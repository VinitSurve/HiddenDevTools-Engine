import os
import sys
from pathlib import Path

# Ensure repository root is at head of sys.path when executed directly as `python scheduler/scheduler.py`
_repo_root = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] == str(Path(__file__).resolve().parent):
    sys.path[0] = _repo_root
elif _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import argparse
import logging
import json
import uuid
import time
import datetime
from scheduler.orchestrator import SchedulerOrchestrator
from scheduler.instagram_publisher import InstagramGraphPublisher, PublishResult
from services.completion_service import CompletionService
from services.observability import setup_logging, PipelineContext
from config.app_config import config
from scheduler.startup_validator import validate_startup, StartupValidationError

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    # --- Startup Banner ---
    print("=======================================")
    print("HiddenDevTools Engine 1.0.0")
    print("Pipeline Version: 6.0.0")
    print(f"Environment: {config.runtime.scheduler.app_env.capitalize()}")
    print(f"Persistence backend: {config.runtime.persistence_backend}")
    print(f"Rendering: {'ENABLED' if config.features.enable_rendering else 'DISABLED'}")
    print(f"Upload: {'ENABLED' if config.features.enable_upload else 'DISABLED'}")
    print(f"Publishing: {'ENABLED' if config.features.enable_publishing else 'DISABLED'}")
    print(f"Completion: {'ENABLED' if config.features.enable_completion else 'DISABLED'}")
    print(f"Reconciliation: {'ENABLED' if config.features.enable_reconciliation else 'DISABLED'}")
    print(f"Dry Run: {'ENABLED' if config.features.dry_run else 'DISABLED'}")
    print("=======================================")

    parser = argparse.ArgumentParser(description="HiddenDevTools Daily Scheduler")
    parser.add_argument("--validate-only", action="store_true", help="Run startup validations and exit without executing pipeline")
    parser.add_argument("--run-today", action="store_true", help="Run the pipeline for today's niche")
    parser.add_argument("--override-day", type=int, choices=range(7), help="DEPRECATED: Override the day of week (0=Mon, 6=Sun)")
    parser.add_argument("--day", type=str, choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], help="Override the day of week (e.g. monday)")
    parser.add_argument("--date", type=str, help="Override the date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.validate_only:
        try:
            validate_startup(read_only=True)
            print("Startup validation succeeded.")
            return 0
        except StartupValidationError as e:
            logger.error(f"Startup validation failed: {e}")
            return 1
        except Exception as e:
            logger.error(f"Startup validation encountered unexpected error: {e}")
            return 1

    override_day = args.override_day
    override_date = args.date

    if args.day:
        day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
        override_day = day_map[args.day.lower()]

    if override_date:
        try:
            parsed_date = datetime.datetime.strptime(override_date, "%Y-%m-%d")
            override_day = parsed_date.weekday()
        except ValueError:
            print("Error: --date must be in YYYY-MM-DD format")
            return

    if args.run_today or override_day is not None or override_date is not None:
        validate_startup()

        run_id = f"RUN_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        workflow_id = os.environ.get("GITHUB_RUN_ID")

        ctx = PipelineContext(run_id=run_id, workflow_id=workflow_id)
        logger.info("Starting Scheduler Pipeline")

        # 0. Startup Reconciliation
        if config.features.enable_reconciliation:
            try:
                from workers.reconciliation_worker import ReconciliationWorker
                recon_worker = ReconciliationWorker()
                recon_results = recon_worker.run(ctx)
                logger.info(f"Startup reconciliation complete: {recon_results}")
            except Exception as e:
                logger.warning(f"Startup reconciliation encountered non-fatal error: {e}")

        # Determine output base directory and create isolated run folder later when generation_id is known
        base_output_dir = "output"

        orchestrator = SchedulerOrchestrator(output_dir=base_output_dir)
        publisher = InstagramGraphPublisher()
        completion_service = CompletionService()

        # 1. Orchestrate (Rendering & Upload happens inside here based on feature flags,
        # but Orchestrator can also be wrapped if needed. The orchestrator itself does
        # rendering and uploading. Let's let it run if any part is enabled, or we can assume
        # orchestrator internally uses feature flags. For now, Orchestrator runs to produce a job.)
        job = None
        try:
            job = orchestrator.run_today(override_day=override_day, override_date=override_date, pipeline_context=ctx)
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")

        if job:
            generation_dir = os.path.join(base_output_dir, job.generation_id)
            os.makedirs(generation_dir, exist_ok=True)

            # Archive Payload
            payload_path = os.path.join(generation_dir, "payload.json")
            try:
                # Orchestrator uses batch.rows dictionaries directly, we need to extract them if they are objects, but Orchestrator did this internally.
                # Since job.artifacts doesn't hold the payload, maybe we need the Orchestrator to save the payload!
                pass # Payload is now saved by orchestrator during its run.
            except Exception as e:
                logger.error(f"Failed to archive payload: {e}")

            # Manifest Generation
            try:
                import config.version as version

                manifest = {
                    "manifest_version": 2,
                    "generation_id": job.generation_id,
                    "batch_id": job.batch_id,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "engine_version": getattr(version, "ENGINE_VERSION", "unknown"),
                    "pipeline_version": getattr(version, "PIPELINE_VERSION", "unknown"),
                    "schema_version": getattr(version, "SCHEMA_VERSION", "unknown"),
                    "niche": job.niche,
                    "renderer": job.niche,
                    "hashes": job.hashes,
                    "artifacts": [{"path": a.storage_path, "public_url": a.public_url, "sha256": a.sha256} for a in job.artifacts],
                    "caption": job.caption,
                    "dry_run": config.features.dry_run
                }

                manifest_path = os.path.join(generation_dir, "manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
                logger.info(f"Generated manifest: {manifest_path}")
            except Exception as e:
                logger.error(f"Failed to generate manifest for job {job.generation_id}: {e}")
            result = PublishResult(
                success=False,
                provider="instagram",
                error_message="Skipped by feature flag"
            )

            # 2. Publish
            if config.features.enable_publishing:
                ctx.start_stage("instagram")

                if config.features.dry_run:
                    logger.info("DRY RUN: Simulating Instagram publish")
                    result = PublishResult(
                        success=True,
                        provider="instagram",
                        permalink="https://instagram.com/p/simulated",
                        published_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        provider_post_id="SIMULATED_MEDIA_ID"
                    )
                else:
                    result = publisher.publish(job)

                if result.success:
                    ctx.end_stage("success")
                else:
                    ctx.end_stage("failed", result.error_message)

            # 3. Complete (Persist State)
            if config.features.enable_completion:
                ctx.start_stage("completion")

                if config.features.dry_run:
                    logger.info("DRY RUN: Simulating Completion")
                    fully_synced = True
                else:
                    fully_synced = completion_service.complete(job, result)

                if result.success:
                    if fully_synced:
                        ctx.end_stage("success")
                    else:
                        ctx.end_stage("partial_success")
                else:
                    ctx.end_stage("failed")

            final_status = "SUCCESS" if result.success else "FAILED"

            # 4. JSON Audit Log
            audit_log = {
                "run_id": run_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "requested_day": args.day or "today",
                "resolved_day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][job.weekday],
                "niche": job.niche,
                "worksheet": job.sheet_name,
                "batch_id": job.batch_id,
                "generation_id": job.generation_id,
                "manifest_path": os.path.abspath(manifest_path) if 'manifest_path' in locals() else None,
                "instagram_container_ids": result.provider_response.get("container_ids", []) if result.provider_response else [],
                "media_id": getattr(result, "provider_post_id", None),
                "published_timestamp": getattr(result, "published_at", None),
                "status": final_status
            }

            audit_path = os.path.join(generation_dir, "scheduler_audit.json")
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit_log, f, indent=2)

            # Keep a global audit log appended
            global_audit_path = "scheduler_audit.json"
            try:
                with open(global_audit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_log) + "\n")
            except:
                pass

        else:
            from utils.timezone import get_ist_weekday
            current_weekday = override_day if override_day is not None else get_ist_weekday()
            if current_weekday == 6:
                logger.info("Sunday scheduled post is intentionally disabled for this launch. Exiting cleanly without publishing.")
                final_status = "SKIPPED"
            else:
                logger.warning("Pipeline exited without creating a PublishJob.")
                final_status = "FAILED"

        summary = ctx.get_summary(final_status)
        logger.info("Pipeline Summary", extra={"pipeline_summary": summary})
        # Explicit print so it's guaranteed visible at the end of the logs in CI
        print(json.dumps(summary, indent=2))
        return 0 if final_status in ("SUCCESS", "SKIPPED") else 1

    else:
        print("Scheduler service started. (Use --run-today to trigger immediately)")
        return 0

if __name__ == "__main__":
    rc = main()
    if rc is not None:
        sys.exit(rc)

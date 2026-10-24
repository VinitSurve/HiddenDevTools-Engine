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
    parser.add_argument("--schedule-aware", action="store_true", help="Calculate target date based on 7 PM IST publishing slot")
    parser.add_argument("--scheduled-at", type=str, help="ISO timestamp of intended schedule trigger or run creation")

    args = parser.parse_args()

    # Auto-detect schedule-aware mode for scheduled GitHub Actions workflows
    is_gh_schedule = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    is_sched_env = os.environ.get("SCHEDULED_MODE") == "true"
    schedule_aware = args.schedule_aware or is_gh_schedule or is_sched_env
    scheduled_at = args.scheduled_at or os.environ.get("SCHEDULED_AT") or os.environ.get("GITHUB_RUN_CREATED_AT")

    from utils.timezone import get_scheduled_publishing_target, get_ist_now, get_ist_weekday
    target_info = get_scheduled_publishing_target(scheduled_at=scheduled_at)
    now_ist = get_ist_now()

    # --- Schedule & Runtime Observability Banner ---
    print(f"Timezone: Asia/Kolkata (IST)")
    print(f"Current IST Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Intended Scheduled Slot: {target_info['scheduled_slot_ist'].strftime('%Y-%m-%d %H:%M:%S IST')} ({target_info['target_day_name']})")
    print(f"Delay: {target_info['delay_human']} (Delayed: {target_info['is_delayed']}, Rollover: {target_info['is_next_day_rollover']}, Expired: {target_info.get('is_expired')})")
    print(f"Execution Mode: {'SCHEDULED' if schedule_aware else 'MANUAL/OVERRIDE'}")
    print("=======================================")

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

    if args.run_today or override_day is not None or override_date is not None or schedule_aware:
        validate_startup()

        run_id = f"RUN_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        workflow_id = os.environ.get("GITHUB_RUN_ID")

        ctx = PipelineContext(run_id=run_id, workflow_id=workflow_id)
        ctx.set_schedule_context(
            intended_date=target_info["target_date_str"],
            intended_day=target_info["target_day_name"],
            intended_slot_ist=target_info["scheduled_slot_ist"].isoformat(),
            actual_execution_ist=target_info["execution_time_ist"].isoformat(),
            delay_seconds=target_info["delay_seconds"],
            delay_human=target_info["delay_human"],
            is_delayed=target_info["is_delayed"],
            is_next_day_rollover=target_info["is_next_day_rollover"],
            is_expired=target_info.get("is_expired", False),
            execution_mode="SCHEDULED" if schedule_aware else "MANUAL"
        )
        logger.info("Starting Scheduler Pipeline")

        # 0. Startup Reconciliation
        if config.features.enable_reconciliation:
            try:
                from workers.reconciliation_worker import ReconciliationWorker
                recon_worker = ReconciliationWorker()
                recon_results = recon_worker.run(ctx)
                logger.info(f"Startup reconciliation complete: {recon_results}")
            except Exception as e:
                logger.error(f"Startup reconciliation encountered error: {e}", exc_info=True)
                ctx.stages["reconciliation_error"] = {"error": str(e), "status": "failed"}

        # Determine output base directory and create isolated run folder later when generation_id is known
        base_output_dir = "output"

        orchestrator = SchedulerOrchestrator(output_dir=base_output_dir)
        publisher = InstagramGraphPublisher()
        completion_service = CompletionService()

        # 1. Orchestrate
        job = None
        try:
            job = orchestrator.run_today(
                override_day=override_day,
                override_date=override_date,
                pipeline_context=ctx,
                schedule_aware=schedule_aware,
                scheduled_at=scheduled_at
            )
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")

        if job and job.status == "EXPIRED":
            logger.warning(
                f"SLOT_EXPIRED: Intended publishing slot for {job.date} ({job.niche}) has expired. "
                f"Delay: {target_info['delay_human']}. Dropping execution to prevent stale publish."
            )
            final_status = "EXPIRED"
            skip_reason = "SLOT_EXPIRED"
            audit_log = {
                "run_id": run_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "intended_date": job.date,
                "intended_slot_ist": target_info["scheduled_slot_ist"].isoformat(),
                "actual_execution_ist": target_info["execution_time_ist"].isoformat(),
                "requested_day": args.day or "today",
                "resolved_day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][job.weekday],
                "niche": job.niche,
                "worksheet": job.sheet_name,
                "batch_id": job.batch_id,
                "generation_id": job.generation_id,
                "manifest_path": None,
                "instagram_container_ids": [],
                "media_id": None,
                "permalink": None,
                "published_timestamp": None,
                "status": "EXPIRED",
                "skip_reason": "SLOT_EXPIRED",
                "already_published": False,
                "delay_seconds": target_info["delay_seconds"],
                "delay_human": target_info["delay_human"],
                "is_expired": True,
                "execution_mode": "SCHEDULED" if schedule_aware else "MANUAL"
            }
            global_audit_path = "scheduler_audit.json"
            try:
                with open(global_audit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_log) + "\n")
            except Exception:
                pass

        elif job and job.status == "ALREADY_PUBLISHED":

            info = job.already_published_info
            logger.info(
                f"IDEMPOTENCY: Content for {job.date} ({job.niche}) is ALREADY PUBLISHED. "
                f"Media ID: {info.get('media_id')}, Permalink: {info.get('permalink')}. "
                "Skipping duplicate rendering, upload, and publishing."
            )
            result = PublishResult(
                success=True,
                provider="instagram",
                permalink=info.get("permalink"),
                published_at=info.get("published_at"),
                provider_post_id=info.get("media_id")
            )
            final_status = "SUCCESS"
            skip_reason = "ALREADY_PUBLISHED"

            audit_log = {
                "run_id": run_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "intended_date": job.date,
                "intended_slot_ist": target_info["scheduled_slot_ist"].isoformat(),
                "actual_execution_ist": target_info["execution_time_ist"].isoformat(),
                "requested_day": args.day or "today",
                "resolved_day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][job.weekday],
                "niche": job.niche,
                "worksheet": job.sheet_name,
                "batch_id": job.batch_id,
                "generation_id": job.generation_id,
                "manifest_path": None,
                "instagram_container_ids": [],
                "media_id": info.get("media_id"),
                "permalink": info.get("permalink"),
                "published_timestamp": info.get("published_at"),
                "status": "SUCCESS",
                "skip_reason": "ALREADY_PUBLISHED",
                "already_published": True,
                "delay_seconds": target_info["delay_seconds"],
                "delay_human": target_info["delay_human"],
                "execution_mode": "SCHEDULED" if schedule_aware else "MANUAL"
            }

            global_audit_path = "scheduler_audit.json"
            try:
                with open(global_audit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_log) + "\n")
            except Exception:
                pass

        elif job:
            generation_dir = os.path.join(base_output_dir, job.generation_id)
            os.makedirs(generation_dir, exist_ok=True)

            # Manifest Generation
            manifest_path = None
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
                "intended_date": job.date,
                "intended_slot_ist": target_info["scheduled_slot_ist"].isoformat(),
                "actual_execution_ist": target_info["execution_time_ist"].isoformat(),
                "requested_day": args.day or "today",
                "resolved_day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][job.weekday],
                "niche": job.niche,
                "worksheet": job.sheet_name,
                "batch_id": job.batch_id,
                "generation_id": job.generation_id,
                "manifest_path": os.path.abspath(manifest_path) if manifest_path else None,
                "instagram_container_ids": result.provider_response.get("container_ids", []) if result.provider_response else [],
                "media_id": getattr(result, "provider_post_id", None),
                "permalink": getattr(result, "permalink", None),
                "published_timestamp": getattr(result, "published_at", None),
                "status": final_status,
                "delay_seconds": target_info["delay_seconds"],
                "delay_human": target_info["delay_human"],
                "is_delayed": target_info["is_delayed"],
                "is_next_day_rollover": target_info["is_next_day_rollover"],
                "execution_mode": "SCHEDULED" if schedule_aware else "MANUAL"
            }

            audit_path = os.path.join(generation_dir, "scheduler_audit.json")
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit_log, f, indent=2)

            global_audit_path = "scheduler_audit.json"
            try:
                with open(global_audit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_log) + "\n")
            except Exception:
                pass

        else:
            resolved_weekday = override_day if override_day is not None else (target_info["target_weekday"] if schedule_aware else get_ist_weekday())
            if resolved_weekday == 6:
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

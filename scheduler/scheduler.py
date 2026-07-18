import os
import argparse
import logging
import json
import uuid
import time
from scheduler.orchestrator import SchedulerOrchestrator
from scheduler.instagram_publisher import InstagramGraphPublisher, PublishResult
from services.completion_service import CompletionService
from services.observability import setup_logging, PipelineContext
from config.app_config import config
from scheduler.startup_validator import validate_startup

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # --- Startup Banner ---
    print("=======================================")
    print("HiddenDevTools Engine 1.0.0")
    print("Pipeline Version: 6.0.0")
    print(f"Environment: {config.runtime.scheduler.app_env.capitalize()}")
    print(f"Rendering: {'ENABLED' if config.features.enable_rendering else 'DISABLED'}")
    print(f"Upload: {'ENABLED' if config.features.enable_upload else 'DISABLED'}")
    print(f"Publishing: {'ENABLED' if config.features.enable_publishing else 'DISABLED'}")
    print(f"Completion: {'ENABLED' if config.features.enable_completion else 'DISABLED'}")
    print(f"Reconciliation: {'ENABLED' if config.features.enable_reconciliation else 'DISABLED'}")
    print(f"Dry Run: {'ENABLED' if config.features.dry_run else 'DISABLED'}")
    print("=======================================")
    
    parser = argparse.ArgumentParser(description="HiddenDevTools Daily Scheduler")
    parser.add_argument("--run-today", action="store_true", help="Run the pipeline for today's niche")
    parser.add_argument("--override-day", type=int, choices=range(7), help="Override the day of week (0=Mon, 6=Sun)")
    
    args = parser.parse_args()
    
    if args.run_today or args.override_day is not None:
        validate_startup()
        
        run_id = f"RUN_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        workflow_id = os.environ.get("GITHUB_RUN_ID")
        
        ctx = PipelineContext(run_id=run_id, workflow_id=workflow_id)
        logger.info("Starting Scheduler Pipeline")
        
        orchestrator = SchedulerOrchestrator()
        publisher = InstagramGraphPublisher()
        completion_service = CompletionService()

        # 1. Orchestrate (Rendering & Upload happens inside here based on feature flags,
        # but Orchestrator can also be wrapped if needed. The orchestrator itself does
        # rendering and uploading. Let's let it run if any part is enabled, or we can assume
        # orchestrator internally uses feature flags. For now, Orchestrator runs to produce a job.)
        job = None
        try:
            job = orchestrator.run_today(override_day=args.override_day, pipeline_context=ctx)
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")

        if job:
            # Manifest Generation
            try:
                import config.version as version
                import os
                import json
                
                manifest_dir = "manifests"
                os.makedirs(manifest_dir, exist_ok=True)
                
                manifest = {
                    "manifest_version": 1,
                    "generation_id": job.generation_id,
                    "batch_id": job.batch_id,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "engine_version": getattr(version, "ENGINE_VERSION", "unknown"),
                    "pipeline_version": getattr(version, "PIPELINE_VERSION", "unknown"),
                    "schema_version": getattr(version, "SCHEMA_VERSION", "unknown"),
                    "niche": job.niche,
                    "renderer": "unknown", # Could be dynamic if exposed on job
                    "template_hash": "unknown",
                    "config_hash": "unknown",
                    "artifacts": [{"path": a.storage_path, "public_url": a.public_url, "sha256": a.sha256} for a in job.artifacts],
                    "caption": job.caption,
                    "dry_run": config.features.dry_run
                }
                
                manifest_path = os.path.join(manifest_dir, f"{job.generation_id}.json")
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
                        published_at=time.strftime("%Y-%m-%dT%H:%M:%S%z")
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
        else:
            logger.warning("Pipeline exited without creating a PublishJob.")
            final_status = "FAILED"
            
        summary = ctx.get_summary(final_status)
        logger.info("Pipeline Summary", extra={"pipeline_summary": summary})
        # Explicit print so it's guaranteed visible at the end of the logs in CI
        print(json.dumps(summary, indent=2))
        
    else:
        print("Scheduler service started. (Use --run-today to trigger immediately)")

if __name__ == "__main__":
    main()

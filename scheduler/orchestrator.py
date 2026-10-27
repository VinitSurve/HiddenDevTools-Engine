import logging
from features.publishing.provider import RepositoryProvider
import datetime
import os
import hashlib
import mimetypes
from typing import Optional, Dict, Any

from models.publish_job import PublishJob
from models.artifact import Artifact
from scheduler.registry import Registry
from scheduler.renderer_factory import RendererFactory
from services.caption_service import CaptionService
from services.publish_batch_service import PublishBatchService, PublishBatch
from services.storage_service import SupabaseStorage
from features.publishing.upload_attempt_repository import UploadAttemptRepository

logger = logging.getLogger(__name__)

class SchedulerOrchestrator:
    def __init__(self, templates_dir: str = "templates", output_dir: str = "output/scheduler_staged"):
        self.caption_service = CaptionService()
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.publish_batch_service = PublishBatchService()

        # Supabase and attempt repos might not be initialized with keys during tests
        try:
            self.storage = SupabaseStorage()
            self.attempt_repo = RepositoryProvider.get_upload_attempt_repository()
            self.ig_attempt_repo = RepositoryProvider.get_instagram_attempt_repository()
        except Exception:
            self.storage = None
            self.attempt_repo = None
            self.ig_attempt_repo = None

    def run_today(
        self,
        override_day: int = None,
        override_date: str = None,
        mock_batch: PublishBatch = None,
        pipeline_context=None,
        schedule_aware: bool = False,
        scheduled_at: Optional[Any] = None
    ) -> Optional[PublishJob]:
        """
        Runs the daily orchestration pipeline Phase 5B.2.
        Fails fast if any step encounters an error.
        """
        logger.info("Scheduler Started")
        target_info = None

        if override_date:
            now = datetime.datetime.strptime(override_date, "%Y-%m-%d")
            date_str = override_date
            weekday = override_day if override_day is not None else now.weekday()
        elif override_day is not None:
            from utils.timezone import get_ist_now
            now = get_ist_now()
            date_str = now.strftime("%Y-%m-%d")
            weekday = override_day
        elif schedule_aware:
            from utils.timezone import get_scheduled_publishing_target
            target_info = get_scheduled_publishing_target(scheduled_at=scheduled_at)
            date_str = target_info["target_date_str"]
            weekday = target_info["target_weekday"]
            logger.info(
                f"Schedule-Aware Target: date={date_str}, day={target_info['target_day_name']}, "
                f"delay={target_info['delay_human']} (delayed={target_info['is_delayed']}, rollover={target_info['is_next_day_rollover']}, expired={target_info.get('is_expired')})"
            )
        else:
            from utils.timezone import get_ist_now
            now = get_ist_now()
            date_str = now.strftime("%Y-%m-%d")
            weekday = now.weekday()

        # 1. Determine niche
        if weekday == 6:
            logger.info("Selected Day 6 (Sunday): Sunday scheduled post is intentionally disabled for this launch. Exiting safely.")
            return None

        config = Registry.get_config_for_day(weekday)
        if not config:
            logger.warning(f"Selected Day {weekday} has no configuration. Exiting.")
            return None

        niche = config["niche"]
        sheet_name = config["sheet_name"]

        logger.info(f"Selected Day {weekday}")
        logger.info(f"Selected Niche {niche}")

        from services.idempotency_service import check_already_published, derive_canonical_generation_id
        canonical_gen_id = derive_canonical_generation_id(date_str, niche)

        # Check for slot expiration (e.g. execution delayed beyond 24h slot deadline)
        if target_info and target_info.get("is_expired"):
            logger.warning(
                f"SLOT_EXPIRED: Intended publishing slot {date_str} ({niche}) has expired "
                f"(delay {target_info['delay_human']} exceeds slot deadline). Dropping execution."
            )
            return PublishJob(
                generation_id=canonical_gen_id,
                batch_id=canonical_gen_id,
                date=date_str,
                weekday=weekday,
                niche=niche,
                sheet_name=sheet_name,
                caption="",
                hashtags=[],
                status="EXPIRED",
                already_published_info={"is_expired": True, "delay_human": target_info["delay_human"]}
            )

        # 1.5 Pre-Publish Idempotency Check
        from config.app_config import config as app_cfg
        is_dry_run = getattr(app_cfg.features, "dry_run", False) if hasattr(app_cfg, "features") else False

        if not mock_batch and not is_dry_run:
            pub_repo = None
            try:
                pub_repo = RepositoryProvider.get_publication_repository()
            except Exception:
                pass
            ig_attempt_repo = getattr(self, "ig_attempt_repo", None)
            if not ig_attempt_repo:
                try:
                    ig_attempt_repo = RepositoryProvider.get_instagram_attempt_repository()
                except Exception:
                    pass
            already_pub = check_already_published(
                target_date_str=date_str,
                niche=niche,
                sheet_name=sheet_name,
                pub_repo=pub_repo,
                attempt_repo=ig_attempt_repo or self.attempt_repo,
                instagram_attempt_repo=ig_attempt_repo,
                upload_attempt_repo=self.attempt_repo
            )
            # Fail closed if repository error occurred and publication state cannot be verified
            if already_pub.get("has_error"):
                logger.error(f"FAIL CLOSED: Pre-publish idempotency check encountered error: {already_pub.get('error')}")
                raise RuntimeError(
                    f"Pre-publish idempotency check failed: {already_pub.get('error')}. "
                    "Failing closed to prevent duplicate publishing."
                )

            if already_pub["is_published"]:
                logger.info(
                    f"IDEMPOTENCY: Content for {date_str} ({niche}) was ALREADY PUBLISHED. "
                    f"Media ID: {already_pub['media_id']}, Permalink: {already_pub['permalink']}"
                )
                if already_pub.get("needs_sheet_sync") and pub_repo:
                    try:
                        from workers.reconciliation_worker import SheetSyncRecovery
                        logger.info(f"Reconciling pending Google Sheets sync for {already_pub['generation_id']}...")
                        SheetSyncRecovery(pub_repo).recover()
                    except Exception as e:
                        logger.warning(f"Failed to reconcile Google Sheets in idempotency check: {e}")

                if pipeline_context:
                    pipeline_context.set_correlation(already_pub["generation_id"], already_pub["generation_id"], niche)

                return PublishJob(
                    generation_id=already_pub["generation_id"],
                    batch_id=already_pub["generation_id"],
                    date=date_str,
                    weekday=weekday,
                    niche=niche,
                    sheet_name=sheet_name,
                    caption="",
                    hashtags=[],
                    status="ALREADY_PUBLISHED",
                    already_published_info=already_pub
                )


        # 2. Get Publish Batch
        if pipeline_context:
            pipeline_context.start_stage("batch_selection")
        logger.info("Requesting PublishBatch")
        batch = mock_batch or self.publish_batch_service.get_next_batch(niche, sheet_name, date_str, generation_id=canonical_gen_id)
        if not batch:
            logger.error("Failed to acquire PublishBatch. Exiting.")
            if pipeline_context: pipeline_context.end_stage("failed", "Failed to acquire PublishBatch")
            return None

        if pipeline_context:
            pipeline_context.set_correlation(batch.batch_id, batch.batch_id, niche)
            pipeline_context.end_stage("success")


        logger.info(f"Acquired Batch {batch.batch_id} with {len(batch.rows)} rows")

        # We need payload dictionaries for rendering
        payloads = [r.__dict__ if hasattr(r, '__dict__') else r for r in batch.rows]

        # 3. Render PNGs
        if pipeline_context: pipeline_context.start_stage("rendering")

        generation_dir = os.path.join(self.output_dir, batch.batch_id)
        os.makedirs(generation_dir, exist_ok=True)

        try:
            renderer = RendererFactory.get_renderer(niche, self.templates_dir)
            # Ensure we send exactly 7 payloads
            if len(payloads) != 7:
                payloads = [payloads[0]] * 7

            # Archive Payload
            payload_path = os.path.join(generation_dir, "payload.json")
            import json
            with open(payload_path, "w", encoding="utf-8") as f:
                json.dump(payloads, f, indent=2)

            logger.info(f"payload.json written to disk (Slide 2): {payloads[0]}")
            logger.info(f"Renderer input dictionary (Slide 2): {payloads[0]}")

            # Render files
            rendered_files = renderer.render(payloads, generation_dir, batch.batch_id)

            # Compute Hashes
            payload_str = json.dumps(payloads, sort_keys=True)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

            layout_path = f"config/renderer_layouts/{niche}.py"
            layout_hash = "unknown"
            if os.path.exists(layout_path):
                with open(layout_path, "rb") as f:
                    layout_hash = hashlib.sha256(f.read()).hexdigest()

            template_name = getattr(renderer, "content_template_name", "")
            template_path = os.path.join(self.templates_dir, template_name) if template_name else ""
            template_hash = "unknown"
            if os.path.exists(template_path):
                with open(template_path, "rb") as f:
                    template_hash = hashlib.sha256(f.read()).hexdigest()

            font_hash = "unknown"
            font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))
            if os.path.exists(font_path):
                with open(font_path, "rb") as f:
                    font_hash = hashlib.sha256(f.read()).hexdigest()

            import inspect
            try:
                renderer_source = inspect.getsource(renderer.__class__)
                renderer_hash = hashlib.sha256(renderer_source.encode()).hexdigest()
            except:
                renderer_hash = "unknown"

            # Save Renderer Metadata
            metadata = {
                "template": template_name,
                "layout": layout_path,
                "payload_hash": payload_hash,
                "layout_hash": layout_hash,
                "template_hash": template_hash,
                "font_hash": font_hash,
                "renderer_hash": renderer_hash
            }
            with open(os.path.join(generation_dir, "render_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            # Expose hashes on the job object for manifest
            batch.hashes = {
                "layout": layout_hash,
                "template": template_hash,
                "fonts": font_hash,
                "renderer": renderer_hash
            }

            logger.info("Rendered Slides")
            if pipeline_context: pipeline_context.end_stage("success")
        except Exception as e:
            logger.error(f"Renderer exception: {e}")
            if pipeline_context: pipeline_context.end_stage("failed", str(e))
            raise

        # 4. Generate caption
        if pipeline_context: pipeline_context.start_stage("caption")
        try:
            caption = self.caption_service.get_caption(row=payloads[0], post_name=niche)
            logger.info("Generated Caption")
            if pipeline_context: pipeline_context.end_stage("success")
        except Exception as e:
            logger.error(f"Caption exception: {e}")
            if pipeline_context: pipeline_context.end_stage("failed", str(e))
            raise

        # 5. Supabase Upload
        if pipeline_context: pipeline_context.start_stage("upload")
        artifacts = []
        from config.app_config import config as app_cfg
        if not app_cfg.features.enable_upload or is_dry_run:
            logger.info("Upload disabled by feature flag or dry run. Creating local mock artifacts.")
            import glob
            png_files = sorted(glob.glob(os.path.join(generation_dir, "*.png")))
            for i, p in enumerate(png_files):
                fname = os.path.basename(p)
                with open(p, "rb") as f:
                    sha = hashlib.sha256(f.read()).hexdigest()
                artifacts.append(Artifact(
                    slide_number=i+1,
                    filename=fname,
                    local_path=p,
                    sha256=sha,
                    mime_type="image/png",
                    storage_path=f"{niche}/{batch.batch_id}/{fname}",
                    public_url=f"https://mock.storage/{niche}/{batch.batch_id}/{fname}"
                ))
            if pipeline_context: pipeline_context.end_stage("success")
        elif self.storage and self.attempt_repo:
            logger.info("Uploading to Supabase Storage")
            upload_result = self.storage.upload_folder(
                generation_id=batch.batch_id,
                local_folder=generation_dir,
                remote_prefix=f"{niche}/{batch.batch_id}",
                attempt_repo=self.attempt_repo
            )
            if not upload_result.get("success"):
                logger.error(f"Upload failed: {upload_result.get('error')}")
                if pipeline_context: pipeline_context.end_stage("failed", upload_result.get("error"))
                raise RuntimeError(f"Storage upload failed: {upload_result.get('error')}")

            # Build Artifacts
            for i, file_res in enumerate(upload_result.get("files", [])):
                local_path = os.path.join(generation_dir, file_res["filename"])
                # We only want to upload PNG artifacts for the Job, but manifest/json etc might also upload.
                # Just include all uploaded files for now.
                if not os.path.exists(local_path):
                    continue
                with open(local_path, "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
                mime_type, _ = mimetypes.guess_type(local_path)

                artifacts.append(Artifact(
                    slide_number=i+1,
                    filename=file_res["filename"],
                    local_path=local_path,
                    sha256=sha256,
                    mime_type=mime_type or "application/octet-stream",
                    storage_path=file_res["remote_path"],
                    public_url=file_res["public_url"]
                ))
            logger.info(f"Enriched {len(artifacts)} Artifacts")
            if pipeline_context: pipeline_context.end_stage("success")
        else:
            logger.info("Mocking Storage Upload (Testing Mode)")
            for i, f in enumerate(rendered_files):
                artifacts.append(Artifact(
                    slide_number=i+1,
                    filename=os.path.basename(f),
                    local_path=f,
                    sha256="mock_sha256",
                    mime_type="image/png",
                    storage_path=f"mock/path/{os.path.basename(f)}",
                    public_url=f"http://mock.url/{os.path.basename(f)}"
                ))
            if pipeline_context: pipeline_context.end_stage("success")

        # 6. Return PublishJob
        job = PublishJob(
            generation_id=batch.batch_id,
            batch_id=batch.batch_id,
            date=date_str,
            weekday=weekday,
            niche=niche,
            sheet_name=sheet_name,
            caption=caption,
            hashtags=[],
            artifacts=artifacts,
            status="READY"
        )
        job.hashes = getattr(batch, "hashes", {})

        logger.info("PublishJob Ready")
        return job

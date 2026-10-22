import os
from features.publishing.provider import RepositoryProvider
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from services.calendar_service import CalendarService, IST
from services.schema_validator import SchemaValidator, SchemaViolationError
from services.active_batch_resolver import ActiveBatchResolver
from services.capability_validator import CapabilityValidator
from services.resource_selector import ResourceSelector, InsufficientResourcesError
from services.batch_claim_service import BatchClaimService
from renderers.template_registry import TemplateRegistry
from adapters.niche_adapter import NicheAdapter
from config.app_config import config

try:
    from sheet_api import open_sheet
except ImportError:
    open_sheet = None

logger = logging.getLogger(__name__)

class ProcessLockError(Exception):
    """Raised when publishing.lock is already held by another process."""
    pass

class DailyCarouselPipeline:
    def __init__(
        self,
        worksheet: Optional[Any] = None,
        pub_repo: Optional[Any] = None,
        artifact_repo: Optional[Any] = None,
        lock_path: Optional[str] = None,
        renderer_cb: Optional[Any] = None,
        uploader_cb: Optional[Any] = None,
        publisher_cb: Optional[Any] = None,
        drive_cb: Optional[Any] = None
    ):
        self.worksheet = worksheet
        self.pub_repo = pub_repo
        self.artifact_repo = artifact_repo
        self.lock_path = lock_path or os.path.join(os.getcwd(), "publishing.lock")
        self.lock_acquired = False
        self.renderer_cb = renderer_cb
        self.uploader_cb = uploader_cb
        self.publisher_cb = publisher_cb
        self.drive_cb = drive_cb

    def _execute_active_batch(
        self,
        sheet_name: str,
        gen_id: str,
        stage: str,
        ws: Any,
        template_key: str
    ) -> Dict[str, Any]:
        """
        Coordinates active batch execution and handles all failure/recovery transitions
        (Scenarios 24-38).
        """
        from PIL import Image
        import shutil

        out_dir = os.path.join(os.getcwd(), "output", gen_id)
        cols = BatchClaimService._get_col_letters(sheet_name, ws)

        def mark_failed(reason: str):
            logger.error(f"ACTIVE_BATCH_FAILED: {reason} under {gen_id}.")
            try:
                records = ws.get_all_records()
                for idx, rec in enumerate(records):
                    if str(rec.get("Generation ID", "")).strip() == gen_id:
                        row_num = rec.get("_row", idx + 2)
                        BatchClaimService._update_row_fields(ws, row_num, cols, "Failed", gen_id, "", "", sheet_name)
            except Exception as e:
                logger.error(f"Could not mark Failed: {e}")
            if os.path.exists(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)

        current_stage = stage
        if current_stage == "Generating":
            try:
                if self.renderer_cb:
                    self.renderer_cb(out_dir)
                else:
                    return {"status": "PHASE_5A1_COMPLETE", "generation_id": gen_id, "stage": current_stage}
            except Exception as e:
                mark_failed(f"Render exception: {e}")
                return {"status": "ABORT_RENDER_FAILED", "generation_id": gen_id}

            if not os.path.exists(out_dir):
                mark_failed("Output directory missing")
                return {"status": "ABORT_RENDER_FAILED", "generation_id": gen_id}

            files = sorted(os.listdir(out_dir))
            if len(files) != 9:
                mark_failed(f"Count != 9 outputs ({len(files)} found)")
                return {"status": "ABORT_RENDER_FAILED", "generation_id": gen_id}

            for f in files:
                try:
                    with Image.open(os.path.join(out_dir, f)) as img:
                        img.verify()
                    with Image.open(os.path.join(out_dir, f)) as img:
                        if img.size != (1173, 1341):
                            mark_failed(f"Image {f} invalid dimensions {img.size}")
                            return {"status": "ABORT_RENDER_FAILED", "generation_id": gen_id}
                except Exception as e:
                    mark_failed(f"Corrupt image {f}: {e}")
                    return {"status": "ABORT_RENDER_FAILED", "generation_id": gen_id}

            current_stage = "Rendered"

        if current_stage == "Rendered":
            try:
                urls = self.uploader_cb(gen_id) if self.uploader_cb else []
                if len(urls) != 9 or any(not str(u).strip() for u in urls):
                    raise RuntimeError("Upload partial or URL verification failure")
                if self.artifact_repo:
                    artifacts = [{"slide_number": idx + 1, "public_url": u} for idx, u in enumerate(urls)]
                    self.artifact_repo.record_artifacts(gen_id, artifacts, datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                mark_failed(f"Supabase upload/verification failure: {e}")
                return {"status": "ABORT_UPLOAD_FAILED", "generation_id": gen_id}

            current_stage = "Uploaded"

        if current_stage == "Uploaded":
            try:
                pub_res = self.publisher_cb(gen_id) if self.publisher_cb else {}

                # Check for controlled fail-closed
                if not pub_res.get("success", True):
                    # Do not mark_failed. Preserve monotonic state (Uploaded).
                    logger.error(f"Instagram publish aborted for {gen_id}: {pub_res.get('error')}")
                    return {"status": "ABORT_PUBLISH_FAILED", "generation_id": gen_id, "error": pub_res.get('error')}

                media_id = pub_res.get("media_id")
                permalink = pub_res.get("permalink")
                pub_timestamp = pub_res.get("timestamp", "")

                if not pub_timestamp:
                    pub_timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

                if not media_id or not permalink:
                    # Defensive. Real failure would be caught above.
                    logger.error("Instagram publish missing media_id or permalink")
                    return {"status": "ABORT_PUBLISH_FAILED", "generation_id": gen_id}

                if self.pub_repo:
                    self.pub_repo.record_publication(gen_id, media_id, permalink, pub_timestamp)
            except Exception as e:
                # Do not call mark_failed for publish failures, preserve monotonic stage.
                logger.error(f"Instagram publish exception: {e}")
                return {"status": "ABORT_PUBLISH_FAILED", "generation_id": gen_id}

            # Sheet final update after verified publish (Scenario 36)
            try:
                records = ws.get_all_records()
                for idx, rec in enumerate(records):
                    if str(rec.get("Generation ID", "")).strip() == gen_id:
                        row_num = rec.get("_row", idx + 2)
                        BatchClaimService._update_row_fields(ws, row_num, cols, "Published", gen_id, permalink, pub_timestamp, sheet_name)
            except Exception as e:
                logger.error(f"SHEET_FINAL_UPDATE_FAILED: {e}. Publication stored in PublicationRepository.")
                return {"status": "SHEET_FINAL_UPDATE_FAILED", "generation_id": gen_id}

            # Google Drive archival non-blocking (Scenario 38)
            try:
                if self.drive_cb:
                    self.drive_cb(gen_id)
            except Exception as e:
                logger.warning(f"DRIVE_ARCHIVAL_FAILED: {e}")

            return {"status": "PUBLISHED", "generation_id": gen_id}

        return {"status": "UNKNOWN_STAGE", "generation_id": gen_id}

    def acquire_lock(self, correlation_id: str) -> bool:
        if os.path.exists(self.lock_path):
            logger.error(f"SCHEDULER_LOCK_HELD: Lock file '{self.lock_path}' exists. Aborting pipeline startup.")
            raise ProcessLockError(f"publishing.lock held at {self.lock_path}")
        lock_data = {
            "pid": os.getpid(),
            "correlation_id": correlation_id,
            "started_at": datetime.now(IST).isoformat()
        }
        try:
            with open(self.lock_path, "w", encoding="utf-8") as f:
                json.dump(lock_data, f)
            self.lock_acquired = True
            return True
        except Exception as e:
            logger.error(f"SCHEDULER_LOCK_FAILED: Could not write lock file '{self.lock_path}': {e}")
            raise ProcessLockError(f"Could not acquire publishing.lock: {e}")

    def release_lock(self) -> None:
        if not self.lock_acquired:
            return
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception as e:
            logger.warning(f"SCHEDULER_LOCK_RELEASE_FAILED: Could not remove lock file '{self.lock_path}': {e}")
        finally:
            self.lock_acquired = False

    def run(
        self,
        calendar_rows: Optional[List[Dict[str, Any]]] = None,
        target_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Execute the Daily Carousel Pipeline following the exact startup order:
        1. Acquire publishing.lock
        2. Resolve today's schedule from Publishing Calendar
        3. Validate target sheet headers in strict ordered equality
        4. Resolve active batches via ActiveBatchResolver across all 7 branches
        5. Gating, resource selection, batch claiming, and rendering coordination
        """
        correlation_id = datetime.now(IST).strftime("PUB_%Y%m%d_%H%M%S")
        try:
            # Step 1: Acquire publishing.lock
            self.acquire_lock(correlation_id)

            # Step 2: Resolve Today's Schedule
            sched_row = CalendarService.get_today_schedule(calendar_rows, target_dt)
            if sched_row is None:
                return {"status": "ABORT_SCHEDULE"}

            sheet_name = str(sched_row.get("Sheet Name", "")).strip()
            template_key = str(sched_row.get("Template", "")).strip()

            try:
                TemplateRegistry.get_template_paths(template_key)
            except KeyError:
                return {"status": "ABORT_INVALID_TEMPLATE"}

            # Step 3: Fetch & Validate Niche Sheet Schema
            ws = self.worksheet
            if ws is None:
                if open_sheet is None:
                    raise RuntimeError("open_sheet not available and no worksheet provided.")
                ws = open_sheet(sheet_name)

            headers = []
            if hasattr(ws, "row_values"):
                try:
                    headers = ws.row_values(1)
                except Exception:
                    headers = []
            if not headers:
                try:
                    recs = ws.get_all_records()
                    if recs:
                        headers = list(recs[0].keys())
                except Exception:
                    headers = []

            if headers:
                try:
                    SchemaValidator.validate_sheet_headers(sheet_name, headers)
                except SchemaViolationError as e:
                    logger.error(f"SHEET_SCHEMA_VALIDATION_FAILED: {e}")
                    raise

            # Get rows
            rows = ws.get_all_records()
            for idx, r in enumerate(rows):
                if "_row" not in r:
                    r["_row"] = idx + 2

            # Ensure pub_repo initialized
            pub_repo = self.pub_repo
            if pub_repo is None:
                from features.publishing.repository import PublicationRepository
                pub_repo = RepositoryProvider.get_publication_repository()

            # Step 4: Active Batch Resolution (Precedence A and B)
            resolution = ActiveBatchResolver.resolve(sheet_name, rows, pub_repo)
            res_type = resolution.get("type")

            # Branch 1: ALREADY_PUBLISHED
            if res_type == "ALREADY_PUBLISHED":
                logger.info(f"PUBLICATION_ALREADY_RECONCILED: {resolution.get('generation_id')}")
                return {"status": "ALREADY_PUBLISHED", "generation_id": resolution.get("generation_id")}

            # Branch 2: INVALID_PUBLISHED_BATCH
            elif res_type == "INVALID_PUBLISHED_BATCH":
                return {"status": "INVALID_PUBLISHED_BATCH", "generation_id": resolution.get("generation_id"), "reason": resolution.get("reason")}

            # Branch 3: CONFLICT
            elif res_type == "CONFLICT":
                return {"status": "CONFLICT", "reason": resolution.get("reason")}

            # Branch 4: INVALID_BATCH
            elif res_type == "INVALID_BATCH":
                return {"status": "INVALID_BATCH", "generation_id": resolution.get("generation_id"), "reason": resolution.get("reason")}

            # Branch 5: UNRECONCILED_PUBLICATION (Precedence A Recovery)
            elif res_type == "UNRECONCILED_PUBLICATION":
                gen_id = resolution.get("generation_id")
                pub_rec = resolution.get("publication", {})
                matched_rows = resolution.get("rows", [])
                canonical_permalink = str(pub_rec.get("permalink", "")).strip()
                canonical_pub_at = str(pub_rec.get("published_at", "")).strip()
                canonical_gen_at = str(pub_rec.get("generated_at", "")).strip()

                cols = BatchClaimService._get_col_letters(sheet_name, ws)
                for r in matched_rows:
                    row_num = r["_row"]
                    BatchClaimService._update_row_fields(
                        ws, row_num, cols, "Published", gen_id, canonical_permalink,
                        canonical_gen_at or datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"), sheet_name
                    )
                    # Also update Published At if column exists/supported
                    if hasattr(ws, "update_cell_by_col_name"):
                        ws.update_cell_by_col_name(row_num, "Published At", canonical_pub_at)
                    elif hasattr(ws, "update_acell") and "Published At" in BatchClaimService._get_col_letters(sheet_name, ws):
                        # If needed
                        pass

                pub_repo.update_sheet_sync_state(gen_id, "SUCCESS")
                logger.info(f"PUBLICATION_RECONCILED_TO_SHEET: Successfully reconciled {gen_id} across 7 rows.")
                return {"status": "RECONCILED", "generation_id": gen_id}

            # Branch 6: RESUME_BATCH (Precedence B Recovery)
            elif res_type == "RESUME_BATCH":
                gen_id = resolution.get("generation_id")
                stage = resolution.get("stage")

                if not config.features.enable_rendering:
                    logger.info(f"ACTIVE_BATCH_FOUND_IN_INSPECTION_MODE: Resumed batch {gen_id} inspected at stage {stage} in Foundation Mode.")
                    return {"status": "PHASE_5A1_COMPLETE", "generation_id": gen_id, "stage": stage}

                if not CapabilityValidator.validate(stage, template_key, gen_id, self.artifact_repo):
                    logger.error(f"CAPABILITY_VALIDATION_FAILED: Cannot resume {gen_id} at stage {stage}.")
                    return {"status": "ABORT_CAPABILITY_FAILED", "generation_id": gen_id, "stage": stage}

                if self.renderer_cb or self.uploader_cb or self.publisher_cb:
                    return self._execute_active_batch(sheet_name, gen_id, stage, ws, template_key)
                return {"status": "PHASE_5A1_COMPLETE", "generation_id": gen_id, "stage": stage}

            # Branch 7: NO_ACTIVE_BATCH (NEW_BATCH flow)
            elif res_type == "NO_ACTIVE_BATCH":
                if not config.features.enable_rendering:
                    adapted = NicheAdapter.adapt_rows(sheet_name, rows)
                    try:
                        selected = ResourceSelector.select_resources(adapted)
                    except InsufficientResourcesError:
                        return {"status": "INSUFFICIENT_RESOURCES"}
                    logger.info(f"PHASE_5A1_FOUNDATION_VALIDATED: Verified 7 eligible drafts for {sheet_name} in Foundation Mode without mutation.")
                    return {"status": "PHASE_5A1_FOUNDATION_VALIDATED", "candidate_count": len(selected)}

                # Pre-claim NEW_BATCH capability gating in Live Mode
                if not CapabilityValidator.validate("NEW_BATCH", template_key, None, self.artifact_repo):
                    logger.error(f"PHASE_5A2_CAPABILITY_VALIDATION_FAILED: Capability check failed for NEW_BATCH ({template_key}).")
                    return {"status": "ABORT_CAPABILITY_FAILED"}

                # Resource Selection
                adapted = NicheAdapter.adapt_rows(sheet_name, rows)
                try:
                    selected = ResourceSelector.select_resources(adapted)
                except InsufficientResourcesError:
                    return {"status": "INSUFFICIENT_RESOURCES"}

                # Durable Verified Batch Claiming
                gen_id = datetime.now(IST).strftime("GEN_%Y%m%d_%H%M%S")
                claimed_id = BatchClaimService.claim_resources(sheet_name, selected, gen_id, ws)
                if not claimed_id:
                    return {"status": "CLAIM_FAILED"}

                if self.renderer_cb or self.uploader_cb or self.publisher_cb:
                    return self._execute_active_batch(sheet_name, claimed_id, "Generating", ws, template_key)
                return {"status": "PHASE_5A1_COMPLETE", "generation_id": claimed_id}

            return {"status": "UNKNOWN_RESOLUTION"}

        finally:
            self.release_lock()

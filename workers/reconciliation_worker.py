import logging
from features.publishing.provider import RepositoryProvider
import datetime
from typing import Dict, Any, List
from services.observability import PipelineContext
from features.publishing.repository import PublicationRepository
from services.batch_claim_service import BatchClaimService
try:
    from sheet_api import open_sheet
except ImportError:
    open_sheet = None

logger = logging.getLogger(__name__)

class RecoveryResult:
    def __init__(self, name: str):
        self.name = name
        self.metrics: Dict[str, int] = {}

    def add_metric(self, key: str, value: int = 1):
        self.metrics[key] = self.metrics.get(key, 0) + value

class SheetSyncRecovery:
    def __init__(self, pub_repo: PublicationRepository):
        self.pub_repo = pub_repo

    def recover(self) -> RecoveryResult:
        result = RecoveryResult("sheet_updates")
        result.metrics = {"pending": 0, "recovered": 0, "failed": 0, "skipped": 0, "permanent_failures": 0}

        pending_records = self.pub_repo.get_pending_sheet_updates()
        result.metrics["pending"] = len(pending_records)

        if not pending_records:
            return result

        if open_sheet is None:
            logger.warning("Google Sheets API not available. Cannot recover sheet updates.")
            result.metrics["permanent_failures"] = len(pending_records)
            return result

        for record in pending_records:
            gen_id = record["generation_id"]
            permalink = record["permalink"]
            pub_timestamp = record["published_at"]
            attempts = record.get("sheet_sync_attempts", 0)

            if attempts >= 5:
                logger.warning(f"Skipping {gen_id} due to max retries.")
                result.metrics["skipped"] += 1
                continue

            logger.info(f"Attempting to recover sheet sync for {gen_id}")
            try:
                niche = gen_id.split("_")[0].lower() if "_" in gen_id else "unknown"
                from scheduler.registry import Registry
                sheet_name = None
                for d in range(7):
                    cfg = Registry.get_config_for_day(d)
                    if cfg and cfg["niche"] == niche:
                        sheet_name = cfg["sheet_name"]
                        break

                if not sheet_name:
                    sheet_name = "Tools/Websites"

                ws = open_sheet(sheet_name)
                if not ws:
                    raise RuntimeError(f"FAILED_AUTH: Could not open sheet {sheet_name}")

                cols = BatchClaimService._get_col_letters(sheet_name, ws)
                records = ws.get_all_records()

                updated = False
                for idx, rec in enumerate(records):
                    if str(rec.get("Generation ID", "")).strip() == gen_id:
                        row_num = rec.get("_row", idx + 2)
                        BatchClaimService._update_row_fields(
                            ws, row_num, cols, "Published", gen_id,
                            permalink, pub_timestamp, sheet_name
                        )
                        updated = True

                if updated:
                    self.pub_repo.update_sheet_sync_state(gen_id, "SUCCESS")
                    result.metrics["recovered"] += 1
                else:
                    raise RuntimeError(f"FAILED_VALIDATION: Row for {gen_id} not found in sheet {sheet_name}")

            except Exception as e:
                error_msg = str(e)
                reason = error_msg.split(":")[0] if "FAILED_" in error_msg else "FAILED_UNKNOWN"
                logger.error(f"Failed to recover sheet sync for {gen_id}: {reason} - {error_msg}")
                self.pub_repo.update_sheet_sync_state(gen_id, "FAILED", error=f"[{reason}] {error_msg}")
                result.metrics["failed"] += 1

        return result

class UploadRecovery:
    def __init__(self, attempt_repo=None, storage_service=None):
        self.attempt_repo = attempt_repo
        self.storage_service = storage_service

    def recover(self, target_generation_id: Optional[str] = None) -> RecoveryResult:
        result = RecoveryResult("uploads")
        result.metrics = {"retried": 0, "recovered": 0, "checked": 0}

        if not self.attempt_repo:
            try:
                self.attempt_repo = RepositoryProvider.get_upload_attempt_repository()
            except Exception:
                return result

        # If target generation is provided, verify its artifacts against local output
        if target_generation_id:
            import os
            local_dir = os.path.join("output", target_generation_id)
            if os.path.isdir(local_dir) and self.storage_service:
                for slide_num in range(1, 10):
                    filename = f"final_{slide_num}.png"
                    local_path = os.path.join(local_dir, filename)
                    if not os.path.isfile(local_path):
                        continue
                    result.add_metric("checked")
                    existing = self.attempt_repo.get_attempt(target_generation_id, slide_num)
                    if not existing:
                        remote_path = f"{target_generation_id}/{filename}"
                        try:
                            upload_res = self.storage_service.upload_file(
                                local_path, remote_path, target_generation_id, slide_num, self.attempt_repo
                            )
                            if upload_res.get("success"):
                                result.add_metric("recovered")
                        except Exception as e:
                            logger.warning(f"Upload recovery failed for {filename}: {e}")
        return result

class PublicationRecovery:
    def __init__(self, attempt_repo=None, pub_repo=None):
        self.attempt_repo = attempt_repo
        self.pub_repo = pub_repo

    def recover(self) -> RecoveryResult:
        result = RecoveryResult("publications")
        result.metrics = {"checked": 0, "recovered": 0, "duplicates_prevented": 0, "unresolved_outcomes": 0}

        if not self.pub_repo:
            try:
                self.pub_repo = RepositoryProvider.get_publication_repository()
            except Exception:
                pass
        if not self.attempt_repo:
            try:
                self.attempt_repo = RepositoryProvider.get_instagram_attempt_repository()
            except Exception:
                pass

        if not self.pub_repo or not self.attempt_repo:
            return result

        pending_records = self.pub_repo.get_pending_sheet_updates()
        for rec in pending_records:
            gen_id = rec.get("generation_id")
            if not gen_id:
                continue
            result.add_metric("checked")
            try:
                attempt = self.attempt_repo.get_attempt(gen_id)
                if not attempt:
                    continue
                state = attempt.get("publish_state")
                if state == "PUBLISH_REQUESTED":
                    logger.warning(f"Ambiguous crash state detected for {gen_id}: PUBLISH_REQUESTED. Failing closed to PUBLISH_OUTCOME_UNKNOWN.")
                    self.attempt_repo.transition_state(gen_id, "PUBLISH_OUTCOME_UNKNOWN")
                    result.add_metric("recovered")
                    result.add_metric("duplicates_prevented")
                    result.add_metric("unresolved_outcomes")
                elif state == "PUBLISH_OUTCOME_UNKNOWN":
                    logger.warning(f"Unresolved publication outcome detected for {gen_id}. Manual reconciliation required.")
                    result.add_metric("duplicates_prevented")
                    result.add_metric("unresolved_outcomes")
            except Exception as e:
                logger.error(f"Publication recovery error for {gen_id}: {e}")

        return result

class ReconciliationWorker:
    def __init__(self, pub_repo=None, attempt_repo=None, upload_repo=None, storage_service=None):
        self.pub_repo = pub_repo or RepositoryProvider.get_publication_repository()
        self.sheet_recovery = SheetSyncRecovery(self.pub_repo)
        self.upload_recovery = UploadRecovery(attempt_repo=upload_repo, storage_service=storage_service)
        self.publication_recovery = PublicationRecovery(attempt_repo=attempt_repo, pub_repo=self.pub_repo)

    def run(self, pipeline_context: PipelineContext) -> Dict[str, Any]:
        pipeline_context.start_stage("reconciliation")

        try:
            sheet_res = self.sheet_recovery.recover()
            upload_res = self.upload_recovery.recover()
            pub_res = self.publication_recovery.recover()

            pipeline_context.end_stage("success")

            return {
                "sheet_updates": sheet_res.metrics,
                "uploads": upload_res.metrics,
                "publications": pub_res.metrics
            }
        except Exception as e:
            logger.error(f"Reconciliation worker failed: {e}")
            pipeline_context.end_stage("failed", error=str(e))
            raise

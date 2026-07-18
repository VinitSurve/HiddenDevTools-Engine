import logging
import datetime
from models.publish_job import PublishJob
from models.publish_result import PublishResult
from features.publishing.repository import PublicationRepository
from services.batch_claim_service import BatchClaimService
try:
    from sheet_api import open_sheet
except ImportError:
    open_sheet = None

logger = logging.getLogger(__name__)

class CompletionService:
    """
    Handles persisting outcomes and updating external state (SQLite, Google Sheets).
    """
    def __init__(self):
        self.pub_repo = PublicationRepository()
        
    def complete(self, job: PublishJob, result: PublishResult) -> bool:
        if not result.success:
            logger.error(f"Publish failed for {job.generation_id}: {result.error_message}")
            return False

        logger.info(f"Completing job {job.generation_id} for provider {result.provider}")

        pub_timestamp = result.published_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update SQLite
        try:
            self.pub_repo.record_publication(
                generation_id=job.generation_id,
                media_id=result.provider_post_id or "UNKNOWN",
                permalink=result.permalink or "",
                published_at=pub_timestamp
            )
            logger.info(f"SQLite updated for {job.generation_id}")
        except Exception as e:
            logger.error(f"Failed to update SQLite for {job.generation_id}: {e}")

        # 2. Update Google Sheets
        sheet_updated = False
        sheet_error = None
        try:
            if open_sheet is None:
                raise RuntimeError("Google Sheets API not available.")
                
            ws = open_sheet(job.sheet_name)
            if not ws:
                raise RuntimeError(f"Could not open sheet {job.sheet_name}")
                
            cols = BatchClaimService._get_col_letters(job.sheet_name, ws)
            records = ws.get_all_records()
            
            for idx, rec in enumerate(records):
                # Using batch_id or generation_id, they are the same in the Orchestrator
                if str(rec.get("Generation ID", "")).strip() == job.generation_id:
                    row_num = rec.get("_row", idx + 2)
                    BatchClaimService._update_row_fields(
                        ws, row_num, cols, "Published", job.generation_id, 
                        result.permalink or "", pub_timestamp, job.sheet_name
                    )
            logger.info(f"Google Sheets updated for {job.generation_id}")
            sheet_updated = True
        except Exception as e:
            sheet_error = str(e)
            logger.error(
                f"PARTIAL FAILURE: Google Sheets update failed for {job.generation_id}: {e}. "
                "Publication is recorded in SQLite. The sheet update remains pending and "
                "will be reconciled by the background retry mechanism."
            )
            
        try:
            if sheet_updated:
                self.pub_repo.update_sheet_sync_state(job.generation_id, "SUCCESS")
                logger.info(f"Job {job.generation_id} successfully completed (fully synchronized).")
            else:
                self.pub_repo.update_sheet_sync_state(job.generation_id, "FAILED", error=sheet_error)
                logger.warning(f"Job {job.generation_id} successfully completed (Google Sheets pending reconciliation).")
        except Exception as e:
            logger.error(f"Failed to record sheet sync state for {job.generation_id}: {e}")
            
        return sheet_updated

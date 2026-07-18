import logging
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
    def recover(self) -> RecoveryResult:
        result = RecoveryResult("uploads")
        result.metrics = {"retried": 0, "recovered": 0}
        # Stub implementation
        return result

class PublicationRecovery:
    def recover(self) -> RecoveryResult:
        result = RecoveryResult("publications")
        result.metrics = {"checked": 0, "recovered": 0, "duplicates_prevented": 0}
        # Stub implementation
        return result

class ReconciliationWorker:
    def __init__(self):
        self.pub_repo = PublicationRepository()
        self.sheet_recovery = SheetSyncRecovery(self.pub_repo)
        self.upload_recovery = UploadRecovery()
        self.publication_recovery = PublicationRecovery()
        
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

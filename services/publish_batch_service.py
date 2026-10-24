import logging
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from models.niche_payloads import BasePayload
from services.batch_claim_service import BatchClaimService
try:
    from sheet_api import open_sheet
except ImportError:
    open_sheet = None

logger = logging.getLogger(__name__)

@dataclass
class PublishBatch:
    batch_id: str
    rows: List[BasePayload]
    sheet_name: str

class PublishBatchService:
    @staticmethod
    def get_next_batch(niche: str, sheet_name: str, date: str, generation_id: Optional[str] = None) -> Optional[PublishBatch]:
        """
        Retrieves the next publishable batch for the given niche.
        Uses BatchClaimService to securely claim 7 Draft rows.
        """
        try:
            from config.app_config import config
            if config.features.dry_run:
                logger.info("DRY RUN: Simulating get_next_batch without fetching real sheet")
                candidate_rows = []
                for i in range(2, 9):
                    payload = BasePayload(id=f"MOCK_{i}", slide_number=i, status="Draft")
                    payload.row_index = i
                    candidate_rows.append(payload)
                
                return PublishBatch(
                    batch_id=generation_id or f"GEN_{uuid.uuid4().hex[:8].upper()}",
                    rows=candidate_rows,
                    sheet_name=sheet_name
                )

                
            ws = None
            if open_sheet is not None:
                ws = open_sheet(sheet_name)
                
            if not ws:
                logger.error(f"Cannot open sheet {sheet_name}")
                return None
                
            try:
                from sheet_api import get_draft_rows
                from adapters.niche_adapter import NicheAdapter
                
                raw_rows = get_draft_rows(limit=7, sheet_name=sheet_name)
                if not raw_rows or len(raw_rows) < 7:
                    logger.error(f"Not enough draft rows for {niche}. Found {len(raw_rows) if raw_rows else 0}.")
                    return None
                    
                candidate_rows = NicheAdapter.adapt_rows(sheet_name, raw_rows)
                
                # Trace for Slide 2 debugging
                logger.info(f"--- TRACE PAYLOAD ---")
                logger.info(f"Requested Day: {date}")
                logger.info(f"Worksheet: {sheet_name}")
                if len(raw_rows) > 0:
                    first_raw = raw_rows[0]
                    first_adapted = candidate_rows[0]
                    logger.info(f"Claimed Row Number (Slide 2): {first_raw.get('_row', 'unknown')}")
                    logger.info(f"Raw Google Sheets Row (Slide 2): {first_raw}")
                    logger.info(f"NicheAdapter Output (Slide 2): {first_adapted}")
                
                # Auto-assign slide numbers sequentially to satisfy validation
                for idx, p in enumerate(candidate_rows):
                    p.slide_number = idx + 2
                
            except Exception as e:
                logger.error(f"Failed to fetch real draft rows from sheet: {e}", exc_info=True)
                return None
                
            if not generation_id:
                from services.idempotency_service import derive_canonical_generation_id
                generation_id = derive_canonical_generation_id(date, niche)

            
            gen_id = BatchClaimService.claim_resources(
                sheet_name=sheet_name,
                candidate_rows=candidate_rows,
                generation_id=generation_id,
                worksheet=ws
            )
            
            if not gen_id:
                logger.error(f"Failed to claim batch for {niche} on {date}")
                return None
                
            return PublishBatch(
                batch_id=gen_id,
                rows=candidate_rows,
                sheet_name=sheet_name
            )
        except Exception as e:
            logger.error(f"Exception in get_next_batch: {e}", exc_info=True)
            return None

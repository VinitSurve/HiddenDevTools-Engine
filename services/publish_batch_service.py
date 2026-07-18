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
    def get_next_batch(niche: str, sheet_name: str, date: str) -> Optional[PublishBatch]:
        """
        Retrieves the next publishable batch for the given niche.
        Uses BatchClaimService to securely claim 7 Draft rows.
        """
        try:
            ws = None
            if open_sheet is not None:
                ws = open_sheet(sheet_name)
                
            if not ws:
                logger.error(f"Cannot open sheet {sheet_name}")
                return None
                
            # For now, we mock row fetching as if we found 7 draft rows.
            # In a full implementation, we'd query `ws` to find 7 rows in Draft status.
            # We construct synthetic candidates to claim since this is still 
            # early integration.
            candidate_rows = []
            for i in range(2, 9):
                payload = BasePayload(id=f"MOCK_{i}", slide_number=i, status="Draft")
                payload.row_index = i
                candidate_rows.append(payload)
                
            generation_id = f"GEN_{uuid.uuid4().hex[:8].upper()}"
            
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
            logger.error(f"Exception in get_next_batch: {e}")
            return None

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from models.niche_payloads import BasePayload
from services.calendar_service import IST
from services.schema_validator import EXPECTED_HEADERS

try:
    from sheet_api import open_sheet, update_cell
except ImportError:
    open_sheet = None
    update_cell = None

logger = logging.getLogger(__name__)

def _col_num_to_letter(col_idx: int) -> str:
    """Convert 1-indexed column number to letter (e.g. 1 -> A, 26 -> Z, 27 -> AA)."""
    result = []
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))

class BatchClaimService:
    @staticmethod
    def _get_col_letters(sheet_name: str, ws: Any) -> Dict[str, str]:
        headers = EXPECTED_HEADERS.get(sheet_name)
        if not headers and hasattr(ws, "row_values"):
            try:
                headers = ws.row_values(1)
            except Exception:
                headers = []
        if not headers:
            # Fallback default columns
            return {"Status": "M", "Post": "N", "Generated At": "O", "Generation ID": "P"}

        cols = {}
        for field in ["Status", "Post", "Generated At", "Generation ID"]:
            if field in headers:
                cols[field] = _col_num_to_letter(headers.index(field) + 1)
            else:
                cols[field] = "M" if field == "Status" else "P"
        return cols

        pass

    @staticmethod
    def claim_resources(
        sheet_name: str,
        candidate_rows: List[BasePayload],
        generation_id: Optional[str] = None,
        worksheet: Optional[Any] = None
    ) -> Optional[str]:
        """
        Durable verified batch claiming of exactly 7 Draft rows.
        Performs ownership-aware rollback on verification failure:
        only rolls back rows where Generation ID == failed_generation_id,
        never modifying rows owned by another process/claim.
        """
        if len(candidate_rows) != 7:
            logger.error(f"BATCH_CLAIM_INVALID_COUNT: Expected exactly 7 candidate rows, got {len(candidate_rows)}.")
            return None

        for p in candidate_rows:
            if str(p.status).strip() != "Draft":
                logger.error(f"BATCH_CLAIM_INVALID_STATUS: Candidate ID={p.id} has status={p.status}, expected Draft.")
                return None

        slide_nums = [p.slide_number for p in candidate_rows]
        if len(set(slide_nums)) != 7:
            logger.error(f"BATCH_CLAIM_DUPLICATE_SLIDES: Candidate rows have duplicate slide numbers {slide_nums}.")
            return None
        if set(slide_nums) != set(range(2, 9)):
            logger.error(f"BATCH_CLAIM_INVALID_SLIDES: Candidate rows have invalid slide numbers {slide_nums}, expected {{2..8}}.")
            return None
        if slide_nums != sorted(slide_nums):
            logger.error(f"BATCH_CLAIM_INVALID_ORDERING: Candidate rows not sorted by slide number.")
            return None

        gen_id = generation_id or datetime.now(IST).strftime("GEN_%Y%m%d_%H%M%S")
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        ws = worksheet
        if ws is None:
            if open_sheet is None:
                raise RuntimeError("open_sheet not available and no worksheet provided.")
            ws = open_sheet(sheet_name)

        cols = BatchClaimService._get_col_letters(sheet_name, ws)

        # 1. Fetch current rows to resolve exact row numbers
        try:
            all_vals = ws.get_all_values()
            headers = all_vals[0] if all_vals else []
            current_records = [dict(zip(headers, row)) for row in all_vals[1:]]
        except Exception as e:
            logger.error(f"BATCH_CLAIM_READ_FAILED: Could not read rows for claim: {e}")
            return None

        id_to_row_num = {}
        for idx, rec in enumerate(current_records):
            rec_id = str(rec.get("ID", "")).strip()
            if rec_id:
                id_to_row_num[rec_id] = rec.get("_row", idx + 2)

        # 2. Perform Batch Write
        try:
            for p in candidate_rows:
                row_num = p.row_index if (p.row_index and p.row_index >= 2) else id_to_row_num.get(p.id)
                if not row_num:
                    logger.error(f"BATCH_CLAIM_ROW_NOT_FOUND: Could not find row number for ID={p.id}")
                    return None
                BatchClaimService._update_row_fields(ws, row_num, cols, "Generating", gen_id, gen_id, timestamp, sheet_name)
        except Exception as e:
            logger.error(f"BATCH_CLAIM_WRITE_ERROR: Exception during write: {e}. Attempting rollback.")
            BatchClaimService._rollback_claim(ws, candidate_rows, gen_id, cols, sheet_name)
            return None

        # 3. Durable Verification
        try:
            verify_vals = ws.get_all_values()
            verify_headers = verify_vals[0] if verify_vals else []
            verify_records = [dict(zip(verify_headers, row)) for row in verify_vals[1:]]
        except Exception as e:
            logger.error(f"BATCH_CLAIM_VERIFY_READ_FAILED: Could not read records for verification: {e}")
            BatchClaimService._rollback_claim(ws, candidate_rows, gen_id, cols, sheet_name)
            return None

        id_to_record = {str(rec.get("ID", "")).strip(): rec for rec in verify_records}

        verification_passed = True
        for p in candidate_rows:
            rec = id_to_record.get(p.id)
            if not rec:
                logger.warning(f"Verification failed: ID {p.id} not found in id_to_record.")
                verification_passed = False
                break
            actual_status = str(rec.get("Status", "")).strip()
            actual_gen_id = str(rec.get("Generation ID", "")).strip()
            if actual_status != "Generating" or actual_gen_id != gen_id:
                logger.warning(f"Verification failed for ID {p.id}: Expected 'Generating'/{gen_id}, got '{actual_status}'/'{actual_gen_id}'.")
                verification_passed = False
                break

        if verification_passed:
            logger.info(f"BATCH_CLAIM_SUCCESS: Successfully claimed 7 rows under {gen_id}.")
            return gen_id

        # 4. Ownership-Aware Rollback
        logger.warning(f"BATCH_CLAIM_VERIFICATION_FAILED: Verification failed for {gen_id}. Executing ownership-aware rollback.")
        BatchClaimService._rollback_claim(ws, candidate_rows, gen_id, cols, sheet_name)
        return None

    @staticmethod
    def _rollback_claim(ws: Any, candidate_rows: List[BasePayload], failed_gen_id: str, cols: Dict[str, str], sheet_name: str) -> None:
        try:
            rollback_vals = ws.get_all_values()
            rollback_headers = rollback_vals[0] if rollback_vals else []
            records = [dict(zip(rollback_headers, row)) for row in rollback_vals[1:]]
        except Exception as e:
            logger.error(f"BATCH_CLAIM_ROLLBACK_READ_FAILED: {e}")
            return

        for idx, rec in enumerate(records):
            rec_id = str(rec.get("ID", "")).strip()
            if any(p.id == rec_id for p in candidate_rows):
                row_num = rec.get("_row", idx + 2)
                current_gen_id = str(rec.get("Generation ID", "")).strip()
                if current_gen_id == failed_gen_id:
                    logger.info(f"BATCH_CLAIM_ROLLBACK: Rolling back ID={rec_id} (row {row_num}) to Draft.")
                    BatchClaimService._update_row_fields(ws, row_num, cols, "Draft", "", "", "", sheet_name)
                else:
                    logger.warning(
                        f"BATCH_CLAIM_OWNERSHIP_CHANGED: Skipping rollback for ID={rec_id} (row {row_num}). "
                        f"Expected {failed_gen_id}, found '{current_gen_id}'."
                    )

    @staticmethod
    def _update_row_fields(ws: Any, row_num: int, cols: Dict[str, str], status: str, gen_id: str, post: str, timestamp: str, sheet_name: str) -> None:
        if hasattr(ws, "update_cell_by_col_name"):
            ws.update_cell_by_col_name(row_num, "Status", status)
            ws.update_cell_by_col_name(row_num, "Generation ID", gen_id)
            ws.update_cell_by_col_name(row_num, "Post", post)
            ws.update_cell_by_col_name(row_num, "Generated At", timestamp)
            return

        updates = [
            {'range': f"{cols['Status']}{row_num}", 'values': [[status]]},
            {'range': f"{cols['Generation ID']}{row_num}", 'values': [[gen_id]]},
            {'range': f"{cols['Post']}{row_num}", 'values': [[post]]},
            {'range': f"{cols['Generated At']}{row_num}", 'values': [[timestamp]]},
        ]
        if hasattr(ws, "batch_update"):
            ws.batch_update(updates)
        else:
            for u in updates:
                ws.update_acell(u['range'], u['values'][0][0])

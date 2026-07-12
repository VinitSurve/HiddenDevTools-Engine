import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ActiveBatchResolver:
    @staticmethod
    def resolve(sheet_name: str, rows: List[Dict[str, Any]], pub_repo: Any) -> Dict[str, Any]:
        """
        ActiveBatchResolver with 7 distinct result types:
        1. UNRECONCILED_PUBLICATION (Precedence A recovery needed)
        2. ALREADY_PUBLISHED (terminal state, zero mutation)
        3. INVALID_PUBLISHED_BATCH (corrupt slide numbers or count for published gen_id)
        4. RESUME_BATCH (Precedence B recovery needed)
        5. INVALID_BATCH (corrupt slide numbers or count for active gen_id)
        6. CONFLICT (multiple active generation IDs)
        7. NO_ACTIVE_BATCH (proceed to claim new resources)
        """
        # Collect distinct non-empty Generation IDs across all rows
        gen_ids_seen = []
        for row in rows:
            gid = str(row.get("Generation ID", "")).strip()
            if gid and gid not in gen_ids_seen:
                gen_ids_seen.append(gid)

        # Precedence A: Check against PublicationRepository
        for gen_id in gen_ids_seen:
            try:
                record = pub_repo.get_by_generation_id(gen_id)
            except Exception as e:
                logger.error(f"Error querying pub_repo for {gen_id}: {e}")
                record = None

            if record is None:
                # Not a published generation, continue checking
                continue

            # Verified publication record exists!
            matched_rows = [r for r in rows if str(r.get("Generation ID", "")).strip() == gen_id]

            # Step 1: Unconditional Structural Validation
            if len(matched_rows) != 7:
                logger.warning(
                    f"INVALID_PUBLISHED_BATCH: Published gen_id='{gen_id}' has {len(matched_rows)} rows, expected 7."
                )
                return {
                    "type": "INVALID_PUBLISHED_BATCH",
                    "generation_id": gen_id,
                    "reason": "INVALID_PUBLISHED_BATCH_COUNT"
                }

            try:
                slide_nums = set(int(r.get("Slide Number", 0)) for r in matched_rows)
            except (ValueError, TypeError):
                slide_nums = set()

            if slide_nums != {2, 3, 4, 5, 6, 7, 8} or len(matched_rows) != 7:
                logger.warning(
                    f"INVALID_PUBLISHED_BATCH: Published gen_id='{gen_id}' has slide numbers {sorted(slide_nums)}, expected 2..8."
                )
                return {
                    "type": "INVALID_PUBLISHED_BATCH",
                    "generation_id": gen_id,
                    "reason": "INVALID_PUBLISHED_BATCH_SLIDES"
                }

            # Step 2: Canonical Field Drift Check
            canonical_permalink = str(record.get("permalink", "")).strip()
            canonical_pub_at = str(record.get("published_at", "")).strip()

            has_drift = False
            for r in matched_rows:
                status_val = str(r.get("Status", "")).strip()
                post_val = str(r.get("Post", "")).strip()
                pub_at_val = str(r.get("Published At", "")).strip()

                if status_val != "Published" or post_val != canonical_permalink or pub_at_val != canonical_pub_at:
                    has_drift = True
                    break

            if has_drift:
                logger.info(f"UNRECONCILED_PUBLICATION: Field drift detected for published gen_id='{gen_id}'.")
                return {
                    "type": "UNRECONCILED_PUBLICATION",
                    "generation_id": gen_id,
                    "publication": record,
                    "rows": matched_rows
                }

            # Step 3: Fully Reconciled -> ALREADY_PUBLISHED
            logger.info(f"ALREADY_PUBLISHED: Fully canonical verified publication for '{gen_id}'.")
            return {
                "type": "ALREADY_PUBLISHED",
                "generation_id": gen_id,
                "publication": record
            }

        # Precedence B: Active (Non-Published) Batches
        active_statuses = {"GENERATING", "RENDERED", "UPLOADED"}
        active_rows = []
        active_gen_ids = []

        for row in rows:
            st = str(row.get("Status", "")).strip().upper()
            if st in active_statuses:
                active_rows.append(row)
                gid = str(row.get("Generation ID", "")).strip()
                if gid and gid not in active_gen_ids:
                    active_gen_ids.append(gid)
                elif not gid:
                    # Active status without a generation ID -> INVALID_BATCH
                    return {
                        "type": "INVALID_BATCH",
                        "reason": "MISSING_GENERATION_ID"
                    }

        if len(active_gen_ids) > 1:
            logger.error(f"CONFLICT: Multiple active generation IDs discovered: {active_gen_ids}.")
            return {
                "type": "CONFLICT",
                "reason": "MULTIPLE_ACTIVE_GENERATION_IDS",
                "generation_ids": active_gen_ids
            }

        if len(active_gen_ids) == 1:
            gen_id = active_gen_ids[0]
            batch_rows = [r for r in rows if str(r.get("Generation ID", "")).strip() == gen_id]

            if len(batch_rows) != 7:
                logger.warning(f"INVALID_BATCH: Active gen_id='{gen_id}' has {len(batch_rows)} rows, expected 7.")
                return {
                    "type": "INVALID_BATCH",
                    "generation_id": gen_id,
                    "reason": "INVALID_ACTIVE_BATCH_COUNT"
                }

            try:
                slide_nums = sorted([int(r.get("Slide Number", 0)) for r in batch_rows])
            except (ValueError, TypeError):
                slide_nums = []

            if slide_nums != list(range(2, 9)):
                logger.warning(f"INVALID_BATCH: Active gen_id='{gen_id}' has slide numbers {slide_nums}, expected 2..8.")
                return {
                    "type": "INVALID_BATCH",
                    "generation_id": gen_id,
                    "reason": "INVALID_ACTIVE_BATCH_SLIDES"
                }

            # Determine recovery stage from minimum status rank
            rank_map = {"GENERATING": 1, "RENDERED": 2, "UPLOADED": 3}
            min_rank = min(rank_map.get(str(r.get("Status", "")).strip().upper(), 1) for r in batch_rows)
            stage_map = {1: "Generating", 2: "Rendered", 3: "Uploaded"}
            stage = stage_map[min_rank]

            logger.info(f"RESUME_BATCH: Discovered valid active batch '{gen_id}' at stage '{stage}'.")
            return {
                "type": "RESUME_BATCH",
                "generation_id": gen_id,
                "stage": stage,
                "rows": batch_rows
            }

        return {"type": "NO_ACTIVE_BATCH"}

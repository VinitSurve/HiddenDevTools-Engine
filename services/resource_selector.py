import logging
from typing import List
from models.niche_payloads import BasePayload

logger = logging.getLogger(__name__)

class InsufficientResourcesError(Exception):
    """Raised when there are not enough eligible Draft candidates to fill slides 2 through 8."""
    pass

class ResourceSelector:
    @staticmethod
    def select_resources(adapted_rows: List[BasePayload]) -> List[BasePayload]:
        """
        Select exactly 7 eligible Draft candidates for slides 2 through 8.
        Enforces strict deterministic ordering: primarily by slide_number (ascending),
        secondarily by ID (ascending) as tie-breaker when multiple candidates exist for the exact same slide number.
        """
        drafts = [p for p in adapted_rows if str(p.status).strip() == "Draft"]

        # Deterministic sort: slide_number asc, then id asc
        drafts.sort(key=lambda x: (x.slide_number, str(x.id).strip()))

        selected = []
        missing_slides = []

        for req_slide in range(2, 9):
            candidate = next((p for p in drafts if p.slide_number == req_slide), None)
            if candidate is not None:
                selected.append(candidate)
            else:
                missing_slides.append(req_slide)

        if missing_slides:
            logger.error(f"INSUFFICIENT_RESOURCES: Missing eligible Draft candidates for slide numbers {missing_slides}.")
            raise InsufficientResourcesError(f"Insufficient Draft resources for slides: {missing_slides}")

        return selected

import logging
import requests
from typing import List, Dict, Optional

from config.app_config import config
from features.publishing.contracts import UploadedArtifactRepository
from features.publishing.repository import UploadedArtifactValidationError, UploadArtifactConflictError

logger = logging.getLogger(__name__)

class SupabaseUploadedArtifactRepository(UploadedArtifactRepository):
    def __init__(self):
        self.url = f"{config.services.supabase.url.rstrip('/')}/rest/v1/uploaded_artifacts"
        self.headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def get_by_generation_id(self, generation_id: str) -> List[Dict]:
        if not generation_id or not isinstance(generation_id, str):
            return []
            
        resp = requests.get(f"{self.url}?generation_id=eq.{generation_id}&order=slide_number", headers=self.headers)
        resp.raise_for_status()
        return resp.json() if resp.json() else []

    def record_artifacts(self, generation_id: str, artifacts: List[Dict], uploaded_at: str) -> None:
        if not isinstance(generation_id, str) or not generation_id.strip():
            raise UploadedArtifactValidationError("generation_id must be a non-empty string.")
        if not isinstance(uploaded_at, str) or not uploaded_at.strip():
            raise UploadedArtifactValidationError("uploaded_at must be a non-empty string.")
        if not isinstance(artifacts, list) or len(artifacts) != 9:
            raise UploadedArtifactValidationError("artifacts must be a list of exactly 9 items.")

        slide_numbers = set()
        for item in artifacts:
            if not isinstance(item, dict):
                raise UploadedArtifactValidationError("Each artifact item must be a dictionary.")
            slide_num = item.get("slide_number")
            if not isinstance(slide_num, int) or isinstance(slide_num, bool):
                raise UploadedArtifactValidationError("slide_number must be an integer between 1 and 9.")
            slide_numbers.add(slide_num)
            
            url = item.get("public_url")
            if not isinstance(url, str) or not url.strip():
                raise UploadedArtifactValidationError("public_url must be a non-empty string.")

        if slide_numbers != {1, 2, 3, 4, 5, 6, 7, 8, 9}:
            raise UploadedArtifactValidationError("slide_number set must be exactly {1, 2, 3, 4, 5, 6, 7, 8, 9} without duplicates.")

        sorted_input = sorted(artifacts, key=lambda x: x["slide_number"])
        
        insert_data = [
            {
                "generation_id": generation_id,
                "slide_number": item["slide_number"],
                "public_url": item["public_url"],
                "uploaded_at": uploaded_at
            }
            for item in sorted_input
        ]

        resp = requests.post(self.url, headers=self.headers, json=insert_data)
        if resp.status_code == 409:
            existing_rows = self.get_by_generation_id(generation_id)
            
            if len(existing_rows) != 9:
                logger.error(f"UPLOAD_ARTIFACT_IDEMPOTENCY_CONFLICT: generation_id={generation_id} has {len(existing_rows)} rows instead of 9.")
                raise UploadArtifactConflictError(f"Conflict: {len(existing_rows)} rows already exist for generation_id={generation_id}.")

            for existing_row, item in zip(existing_rows, sorted_input):
                ex_slide = existing_row["slide_number"]
                ex_url = existing_row["public_url"]
                if ex_slide != item["slide_number"] or ex_url != item["public_url"]:
                    logger.error(f"UPLOAD_ARTIFACT_IDEMPOTENCY_CONFLICT: generation_id={generation_id} slide={item['slide_number']} mismatch (existing: {ex_url}, new: {item['public_url']})")
                    raise UploadArtifactConflictError(f"Conflict on slide {item['slide_number']} for generation_id={generation_id}.")
            
            # Idempotent success
            return
        resp.raise_for_status()

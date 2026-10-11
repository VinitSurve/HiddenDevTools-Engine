import logging
import requests
from typing import List, Dict, Optional

from config.app_config import config
from features.publishing.contracts import UploadAttemptRepository
from features.publishing.upload_attempt_repository import UploadAttemptConflictError

logger = logging.getLogger(__name__)

class SupabaseUploadAttemptRepository(UploadAttemptRepository):
    def __init__(self):
        self.url = f"{config.services.supabase.url.rstrip('/')}/rest/v1/upload_attempts"
        self.headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def record_attempt(self, generation_id: str, slide_number: int, remote_path: str, sha256_hash: str, public_url: str, uploaded_at: str) -> None:
        if not generation_id:
            raise ValueError("generation_id must not be empty")
        if slide_number < 1 or slide_number > 9:
            raise ValueError("slide_number must be between 1 and 9")
        if not remote_path:
            raise ValueError("remote_path must not be empty")
        if len(sha256_hash) != 64 or not sha256_hash.islower() or not all(c in '0123456789abcdef' for c in sha256_hash):
            raise ValueError("sha256_hash must be exactly 64 lowercase hexadecimal characters")
        if not public_url:
            raise ValueError("public_url must not be empty")
        if not uploaded_at:
            raise ValueError("uploaded_at must not be empty")

        data = {
            "generation_id": generation_id,
            "slide_number": slide_number,
            "remote_path": remote_path,
            "sha256_hash": sha256_hash,
            "public_url": public_url,
            "uploaded_at": uploaded_at
        }

        resp = requests.post(self.url, headers=self.headers, json=data)
        if resp.status_code == 409:
            existing = self.get_attempt(generation_id, slide_number)
            if existing:
                if (existing["remote_path"] == remote_path and 
                    existing["sha256_hash"] == sha256_hash and 
                    existing["public_url"] == public_url):
                    logger.info(f"Idempotent upload attempt reuse for {generation_id} slide {slide_number}")
                    return
                else:
                    raise UploadAttemptConflictError(
                        f"Conflict for {generation_id} slide {slide_number}. "
                        f"Existing: {existing['remote_path']}, {existing['sha256_hash']}, {existing['public_url']}. "
                        f"New: {remote_path}, {sha256_hash}, {public_url}."
                    )
        resp.raise_for_status()

    def get_attempt(self, generation_id: str, slide_number: int) -> Optional[Dict]:
        resp = requests.get(f"{self.url}?generation_id=eq.{generation_id}&slide_number=eq.{slide_number}", headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[0]
        return None

    def get_all_attempts(self, generation_id: str) -> List[Dict]:
        resp = requests.get(f"{self.url}?generation_id=eq.{generation_id}&order=slide_number", headers=self.headers)
        resp.raise_for_status()
        return resp.json() if resp.json() else []

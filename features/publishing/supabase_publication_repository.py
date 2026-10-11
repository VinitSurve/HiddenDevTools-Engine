from typing import Optional, Dict, List
import logging
import requests
from datetime import datetime, timezone

from config.app_config import config
from features.publishing.contracts import PublicationRepository
from features.publishing.repository import PublicationConflictError

logger = logging.getLogger(__name__)

class SupabasePublicationRepository(PublicationRepository):
    def __init__(self):
        self.url = f"{config.services.supabase.url.rstrip('/')}/rest/v1/published_generations"
        self.headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def get_by_generation_id(self, generation_id: str) -> Optional[Dict]:
        try:
            resp = requests.get(f"{self.url}?generation_id=eq.{generation_id}", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching from supabase: {e}")
            raise

    def record_publication(self, generation_id: str, media_id: str, permalink: str, published_at: str) -> None:
        if not generation_id or not media_id or not permalink or not published_at:
            raise ValueError("All arguments must be non-empty strings")
            
        data = {
            "generation_id": generation_id,
            "media_id": media_id,
            "permalink": permalink,
            "published_at": published_at,
            "sheet_sync_state": "PENDING",
            "sheet_sync_attempts": 0
        }
        
        resp = requests.post(self.url, headers=self.headers, json=data)
        if resp.status_code == 409: # Conflict
            existing = self.get_by_generation_id(generation_id)
            if existing:
                if existing.get('media_id') == media_id and existing.get('permalink') == permalink:
                    logger.info(f"Idempotent publication recording for {generation_id}")
                    return
                else:
                    raise PublicationConflictError(
                        f"Conflict for {generation_id}. "
                        f"Existing: {existing.get('media_id')} / {existing.get('permalink')}. "
                        f"New: {media_id} / {permalink}."
                    )
        resp.raise_for_status()

    def update_sheet_sync_state(self, generation_id: str, state: str, error: Optional[str] = None) -> None:
        if state not in ('PENDING', 'SUCCESS', 'FAILED'):
            raise ValueError("Invalid sync state")
            
        existing = self.get_by_generation_id(generation_id)
        if not existing:
            return
            
        attempts = existing.get('sheet_sync_attempts', 0) + 1
        now_ts = datetime.now(timezone.utc).isoformat()
        
        update_data = {
            "sheet_sync_state": state,
            "sheet_sync_attempts": attempts,
            "last_sheet_sync_at": now_ts,
            "last_sheet_sync_error": error
        }
        
        resp = requests.patch(f"{self.url}?generation_id=eq.{generation_id}", headers=self.headers, json=update_data)
        resp.raise_for_status()

    def get_pending_sheet_updates(self) -> List[Dict]:
        resp = requests.get(f"{self.url}?sheet_sync_state=in.(PENDING,FAILED)", headers=self.headers)
        resp.raise_for_status()
        return resp.json() if resp.json() else []

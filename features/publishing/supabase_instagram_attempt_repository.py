import json
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone

from config.app_config import config
from features.publishing.contracts import InstagramPublicationAttemptRepository
from features.publishing.instagram_attempt_repository import (
    InstagramAttemptConflictError,
    InvalidStateTransitionError,
    SQLiteInstagramPublicationAttemptRepository as SQLiteRepo,
)

logger = logging.getLogger(__name__)

class SupabaseInstagramPublicationAttemptRepository(InstagramPublicationAttemptRepository):
    VALID_STATES = SQLiteRepo.VALID_STATES

    def __init__(self):
        self.url = f"{config.services.supabase.url.rstrip('/')}/rest/v1/instagram_publication_attempts"
        self.headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def get_attempt(self, generation_id: str) -> Optional[Dict]:
        resp = requests.get(f"{self.url}?generation_id=eq.{generation_id}", headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        
        if data:
            row = data[0]
            # Match SQLite behavior
            return {
                "generation_id": row.get("generation_id"),
                "child_creation_ids": row.get("child_creation_ids"),
                "carousel_creation_id": row.get("carousel_creation_id"),
                "publish_state": row.get("publish_state"),
                "media_id": row.get("media_id"),
                "permalink": row.get("permalink"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at")
            }
        return None

    def create_attempt(self, generation_id: str, child_creation_ids: List[str]) -> None:
        if not generation_id:
            raise ValueError("generation_id must not be empty")
        if not child_creation_ids or len(child_creation_ids) != 9:
            raise ValueError("Must provide exactly 9 child_creation_ids")
            
        data = {
            "generation_id": generation_id,
            "child_creation_ids": child_creation_ids,
            "publish_state": "CHILDREN_CREATED",
            "created_at": self._now(),
            "updated_at": self._now()
        }
        
        resp = requests.post(self.url, headers=self.headers, json=data)
        if resp.status_code == 409:
            pass # SQLite raised IntegrityError, requests raises HTTPError which is basically equivalent. We can let it raise_for_status
        resp.raise_for_status()

    def transition_state(self, generation_id: str, new_state: str, **kwargs) -> None:
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {new_state}")

        existing = self.get_attempt(generation_id)
        if not existing:
            raise InstagramAttemptConflictError(f"Attempt not found for {generation_id}")
            
        current_state = existing["publish_state"]
        existing_media_id = existing["media_id"]
        
        updates = {
            "publish_state": new_state,
            "updated_at": self._now()
        }

        # Validation matrix (matching SQLite behavior exactly)
        if new_state == 'CAROUSEL_CREATED':
            if current_state != 'CHILDREN_CREATED':
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
            if 'carousel_creation_id' not in kwargs or not kwargs['carousel_creation_id']:
                raise ValueError("carousel_creation_id required for CAROUSEL_CREATED")
            updates['carousel_creation_id'] = kwargs['carousel_creation_id']

        elif new_state == 'PUBLISH_REQUESTED':
            if current_state not in ('CAROUSEL_CREATED', 'PUBLISH_RETRY_AUTHORIZED'):
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")

        elif new_state == 'PUBLISHED_MEDIA_KNOWN':
            if current_state != 'PUBLISH_REQUESTED':
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
            media_id = kwargs.get('media_id')
            if not media_id or not str(media_id).strip():
                raise ValueError("media_id must not be empty for PUBLISHED_MEDIA_KNOWN")
            updates['media_id'] = media_id

        elif new_state == 'PUBLISH_OUTCOME_UNKNOWN':
            if current_state not in ('PUBLISH_REQUESTED', 'PUBLISHED_MEDIA_KNOWN'):
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")

        elif new_state == 'PUBLISH_RETRY_AUTHORIZED':
            if current_state != 'PUBLISH_OUTCOME_UNKNOWN':
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")

        elif new_state == 'PUBLISHED_VERIFIED':
            if current_state not in ('PUBLISHED_MEDIA_KNOWN', 'PUBLISH_OUTCOME_UNKNOWN'):
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
            
            permalink = kwargs.get('permalink')
            if existing_media_id and 'media_id' in kwargs and kwargs['media_id'] and kwargs['media_id'] != existing_media_id:
                raise InstagramAttemptConflictError("Cannot overwrite immutable media_id")

            if permalink:
                updates['permalink'] = permalink
            if not existing_media_id and kwargs.get('media_id'):
                updates['media_id'] = kwargs['media_id']

        else:
            raise InvalidStateTransitionError(f"Unknown transition target: {new_state}")

        resp = requests.patch(f"{self.url}?generation_id=eq.{generation_id}", headers=self.headers, json=updates)
        resp.raise_for_status()

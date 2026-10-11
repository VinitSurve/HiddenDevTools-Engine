import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from settings import PUBLISHING_DB_PATH

logger = logging.getLogger(__name__)

class InstagramAttemptConflictError(Exception):
    pass

class InvalidStateTransitionError(Exception):
    pass

from features.publishing.contracts import InstagramPublicationAttemptRepository

class SQLiteInstagramPublicationAttemptRepository(InstagramPublicationAttemptRepository):
    VALID_STATES = {
        'CHILDREN_CREATED',
        'CAROUSEL_CREATED',
        'PUBLISH_REQUESTED',
        'PUBLISHED_MEDIA_KNOWN',
        'PUBLISH_OUTCOME_UNKNOWN',
        'PUBLISH_RETRY_AUTHORIZED',
        'PUBLISHED_VERIFIED'
    }

    def __init__(self, db_path: str = PUBLISHING_DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def get_attempt(self, generation_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT child_creation_ids, carousel_creation_id, publish_state, media_id, permalink, created_at, updated_at
                FROM instagram_publication_attempts
                WHERE generation_id = ?
            """, (generation_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "generation_id": generation_id,
                    "child_creation_ids": json.loads(row[0]) if row[0] else None,
                    "carousel_creation_id": row[1],
                    "publish_state": row[2],
                    "media_id": row[3],
                    "permalink": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                }
            return None

    def create_attempt(self, generation_id: str, child_creation_ids: List[str]) -> None:
        if not generation_id:
            raise ValueError("generation_id must not be empty")
        if not child_creation_ids or len(child_creation_ids) != 9:
            raise ValueError("Must provide exactly 9 child_creation_ids")
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO instagram_publication_attempts 
                (generation_id, child_creation_ids, publish_state, created_at, updated_at) 
                VALUES (?, ?, 'CHILDREN_CREATED', ?, ?)
            """, (generation_id, json.dumps(child_creation_ids), self._now(), self._now()))
            conn.commit()

    def transition_state(self, generation_id: str, new_state: str, **kwargs) -> None:
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {new_state}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT publish_state, media_id FROM instagram_publication_attempts WHERE generation_id = ?", (generation_id,))
            row = cursor.fetchone()
            if not row:
                raise InstagramAttemptConflictError(f"Attempt not found for {generation_id}")
            
            current_state = row[0]
            existing_media_id = row[1]
            
            # Validation matrix
            if new_state == 'CAROUSEL_CREATED':
                if current_state != 'CHILDREN_CREATED':
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                if 'carousel_creation_id' not in kwargs or not kwargs['carousel_creation_id']:
                    raise ValueError("carousel_creation_id required for CAROUSEL_CREATED")
                
                cursor.execute("""
                    UPDATE instagram_publication_attempts 
                    SET publish_state = ?, carousel_creation_id = ?, updated_at = ? 
                    WHERE generation_id = ?
                """, (new_state, kwargs['carousel_creation_id'], self._now(), generation_id))

            elif new_state == 'PUBLISH_REQUESTED':
                if current_state not in ('CAROUSEL_CREATED', 'PUBLISH_RETRY_AUTHORIZED'):
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                
                cursor.execute("""
                    UPDATE instagram_publication_attempts 
                    SET publish_state = ?, updated_at = ? 
                    WHERE generation_id = ?
                """, (new_state, self._now(), generation_id))

            elif new_state == 'PUBLISHED_MEDIA_KNOWN':
                if current_state != 'PUBLISH_REQUESTED':
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                media_id = kwargs.get('media_id')
                if not media_id or not str(media_id).strip():
                    raise ValueError("media_id must not be empty for PUBLISHED_MEDIA_KNOWN")
                
                cursor.execute("""
                    UPDATE instagram_publication_attempts 
                    SET publish_state = ?, media_id = ?, updated_at = ? 
                    WHERE generation_id = ?
                """, (new_state, media_id, self._now(), generation_id))

            elif new_state == 'PUBLISH_OUTCOME_UNKNOWN':
                if current_state not in ('PUBLISH_REQUESTED', 'PUBLISHED_MEDIA_KNOWN'):
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                
                cursor.execute("""
                    UPDATE instagram_publication_attempts 
                    SET publish_state = ?, updated_at = ? 
                    WHERE generation_id = ?
                """, (new_state, self._now(), generation_id))

            elif new_state == 'PUBLISH_RETRY_AUTHORIZED':
                if current_state != 'PUBLISH_OUTCOME_UNKNOWN':
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                
                cursor.execute("""
                    UPDATE instagram_publication_attempts 
                    SET publish_state = ?, updated_at = ? 
                    WHERE generation_id = ?
                """, (new_state, self._now(), generation_id))

            elif new_state == 'PUBLISHED_VERIFIED':
                if current_state not in ('PUBLISHED_MEDIA_KNOWN', 'PUBLISH_OUTCOME_UNKNOWN'):
                    raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {new_state}")
                
                permalink = kwargs.get('permalink')
                # Optional media_id update if needed, but it shouldn't overwrite an existing immutable one
                # Usually VERIFIED_PUBLISHED just sets the final state and permalink
                
                if existing_media_id and 'media_id' in kwargs and kwargs['media_id'] and kwargs['media_id'] != existing_media_id:
                     raise InstagramAttemptConflictError("Cannot overwrite immutable media_id")

                updates = ["publish_state = ?", "updated_at = ?"]
                params = [new_state, self._now()]
                
                if permalink:
                    updates.append("permalink = ?")
                    params.append(permalink)
                if not existing_media_id and kwargs.get('media_id'):
                    updates.append("media_id = ?")
                    params.append(kwargs['media_id'])
                
                params.append(generation_id)
                query = f"UPDATE instagram_publication_attempts SET {', '.join(updates)} WHERE generation_id = ?"
                cursor.execute(query, tuple(params))
            else:
                raise InvalidStateTransitionError(f"Unknown transition target: {new_state}")

            conn.commit()

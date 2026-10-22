import sqlite3
import os
import logging
from typing import Optional, Dict

from settings import PUBLISHING_DB_PATH
from features.publishing.exceptions import (
    PublicationConflictError,
    UploadArtifactConflictError,
    UploadedArtifactValidationError,
)
from features.publishing.migrations_runner import run_publishing_migrations
from features.publishing.uploaded_artifact_repository import UploadedArtifactRepository

logger = logging.getLogger(__name__)

from features.publishing.contracts import PublicationRepository

class SQLitePublicationRepository(PublicationRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "..", PUBLISHING_DB_PATH)
        run_publishing_migrations(self.db_path)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_by_generation_id(self, generation_id: str) -> Optional[Dict]:
        """Get publication record by generation_id."""
        if not generation_id or not isinstance(generation_id, str):
            return None
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT generation_id, media_id, permalink, published_at,
                       sheet_sync_state, sheet_sync_attempts, last_sheet_sync_at, last_sheet_sync_error
                FROM published_generations
                WHERE generation_id = ?
            """, (generation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "generation_id": row[0],
                "media_id": row[1],
                "permalink": row[2],
                "published_at": row[3],
                "sheet_sync_state": row[4],
                "sheet_sync_attempts": row[5],
                "last_sheet_sync_at": row[6],
                "last_sheet_sync_error": row[7]
            }
        finally:
            conn.close()

    def record_publication(self, generation_id: str, media_id: str, permalink: str, published_at: str) -> None:
        """
        Record an Instagram publication for a generation_id.
        Enforces strict idempotency and conflict check.
        """
        if not generation_id or not media_id or not permalink or not published_at:
            raise ValueError("All parameters must be non-empty strings.")

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("""
                    SELECT media_id, permalink, published_at
                    FROM published_generations
                    WHERE generation_id = ?
                """, (generation_id,))
                existing = cursor.fetchone()

                if not existing:
                    # Case A: Not found. INSERT.
                    cursor.execute("""
                        INSERT INTO published_generations (generation_id, media_id, permalink, published_at)
                        VALUES (?, ?, ?, ?)
                    """, (generation_id, media_id, permalink, published_at))
                    conn.commit()
                    return

                ex_media, ex_perm, _ = existing
                if ex_media == media_id and ex_perm == permalink:
                    # Case B: Exact match on media_id and permalink. Idempotent success. No mutation.
                    conn.commit()
                    return

                # Case C: Differs on media_id or permalink. Conflict.
                logger.error(f"PUBLICATION_IDEMPOTENCY_CONFLICT: generation_id={generation_id} existing=(media_id={ex_media}, permalink={ex_perm}) vs new=(media_id={media_id}, permalink={permalink})")
                raise PublicationConflictError(
                    f"Conflict for generation_id={generation_id}: existing media_id={ex_media}, permalink={ex_perm} vs new media_id={media_id}, permalink={permalink}"
                )
            except Exception:
                conn.rollback()
                raise
        finally:
            conn.close()

    def update_sheet_sync_state(self, generation_id: str, state: str, error: Optional[str] = None) -> None:
        """Update the sheet sync state for a publication."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE published_generations
                SET sheet_sync_state = ?,
                    sheet_sync_attempts = sheet_sync_attempts + 1,
                    last_sheet_sync_at = CURRENT_TIMESTAMP,
                    last_sheet_sync_error = ?
                WHERE generation_id = ?
            """, (state, error, generation_id))
            conn.commit()
        finally:
            conn.close()

    def get_pending_sheet_updates(self):
        """Get all publications that have pending or failed sheet updates."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT generation_id, media_id, permalink, published_at, sheet_sync_attempts
                FROM published_generations
                WHERE sheet_sync_state IN ('PENDING', 'FAILED')
            """)
            return [{"generation_id": row[0], "media_id": row[1], "permalink": row[2], "published_at": row[3], "sheet_sync_attempts": row[4]} for row in cursor.fetchall()]
        finally:
            conn.close()

__all__ = [
    "SQLitePublicationRepository",
    "SQLiteUploadedArtifactRepository",
    "PublicationConflictError",
    "UploadArtifactConflictError",
    "UploadedArtifactValidationError",
    "run_publishing_migrations",
]

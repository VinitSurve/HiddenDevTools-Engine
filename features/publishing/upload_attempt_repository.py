import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from settings import PUBLISHING_DB_PATH

logger = logging.getLogger(__name__)

class UploadAttemptConflictError(Exception):
    pass

class RemoteArtifactConflictError(Exception):
    pass

class UntrackedRemoteArtifactError(Exception):
    pass

from features.publishing.contracts import UploadAttemptRepository

class SQLiteUploadAttemptRepository(UploadAttemptRepository):
    def __init__(self, db_path: str = PUBLISHING_DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

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

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT remote_path, sha256_hash, public_url, uploaded_at
                FROM upload_attempts
                WHERE generation_id = ? AND slide_number = ?
            """, (generation_id, slide_number))
            row = cursor.fetchone()

            if row:
                existing_remote_path, existing_hash, existing_url, existing_time = row
                if (existing_remote_path == remote_path and
                    existing_hash == sha256_hash and
                    existing_url == public_url):
                    # Idempotent success
                    logger.info(f"Idempotent upload attempt reuse for {generation_id} slide {slide_number}")
                    return
                else:
                    raise UploadAttemptConflictError(
                        f"Conflict for {generation_id} slide {slide_number}. "
                        f"Existing: {existing_remote_path}, {existing_hash}, {existing_url}. "
                        f"New: {remote_path}, {sha256_hash}, {public_url}."
                    )

            cursor.execute("""
                INSERT INTO upload_attempts
                (generation_id, slide_number, remote_path, sha256_hash, public_url, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (generation_id, slide_number, remote_path, sha256_hash, public_url, uploaded_at))
            conn.commit()

    def get_attempt(self, generation_id: str, slide_number: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT remote_path, sha256_hash, public_url, uploaded_at
                FROM upload_attempts
                WHERE generation_id = ? AND slide_number = ?
            """, (generation_id, slide_number))
            row = cursor.fetchone()
            if row:
                return {
                    "remote_path": row[0],
                    "sha256_hash": row[1],
                    "public_url": row[2],
                    "uploaded_at": row[3]
                }
            return None

    def get_all_attempts(self, generation_id: str) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT slide_number, remote_path, sha256_hash, public_url, uploaded_at
                FROM upload_attempts
                WHERE generation_id = ?
                ORDER BY slide_number ASC
            """, (generation_id,))
            return [
                {
                    "slide_number": row[0],
                    "remote_path": row[1],
                    "sha256_hash": row[2],
                    "public_url": row[3],
                    "uploaded_at": row[4]
                }
                for row in cursor.fetchall()
            ]

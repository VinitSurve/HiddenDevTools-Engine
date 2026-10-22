import sqlite3
import os
import logging
from typing import List, Dict, Optional

from settings import PUBLISHING_DB_PATH
from features.publishing.exceptions import (
    UploadedArtifactValidationError,
    UploadArtifactConflictError,
)
from features.publishing.migrations_runner import run_publishing_migrations

logger = logging.getLogger(__name__)

from features.publishing.contracts import UploadedArtifactRepository

class SQLiteUploadedArtifactRepository(UploadedArtifactRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "..", PUBLISHING_DB_PATH)
        run_publishing_migrations(self.db_path)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_by_generation_id(self, generation_id: str) -> List[Dict]:
        """Return list of uploaded artifacts [{slide_number, public_url, uploaded_at}] sorted by slide_number."""
        if not generation_id or not isinstance(generation_id, str):
            return []
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT slide_number, public_url, uploaded_at
                FROM uploaded_artifacts
                WHERE generation_id = ?
                ORDER BY slide_number ASC
            """, (generation_id,))
            rows = cursor.fetchall()
            return [
                {
                    "slide_number": row[0],
                    "public_url": row[1],
                    "uploaded_at": row[2]
                }
                for row in rows
            ]
        finally:
            conn.close()

    def record_artifacts(self, generation_id: str, artifacts: List[Dict], uploaded_at: str) -> None:
        """
        Record 9 uploaded artifacts for a generation_id.
        Enforces write-time input validation before any SQL transaction, and strict idempotency/conflict rules.
        """
        # Write-Time Input Validation (BEFORE transaction)
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

        # Sorted input for deterministic comparisons
        sorted_input = sorted(artifacts, key=lambda x: x["slide_number"])

        # Enter SQL transaction
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("""
                    SELECT slide_number, public_url, uploaded_at
                    FROM uploaded_artifacts
                    WHERE generation_id = ?
                    ORDER BY slide_number ASC
                """, (generation_id,))
                existing_rows = cursor.fetchall()

                if not existing_rows:
                    # Case A: No records exist. INSERT atomically.
                    cursor.executemany("""
                        INSERT INTO uploaded_artifacts (generation_id, slide_number, public_url, uploaded_at)
                        VALUES (?, ?, ?, ?)
                    """, [
                        (generation_id, item["slide_number"], item["public_url"], uploaded_at)
                        for item in sorted_input
                    ])
                    conn.commit()
                    return

                # Check exact match with existing rows
                if len(existing_rows) != 9:
                    logger.error(f"UPLOAD_ARTIFACT_IDEMPOTENCY_CONFLICT: generation_id={generation_id} has {len(existing_rows)} rows instead of 9.")
                    raise UploadArtifactConflictError(f"Conflict: {len(existing_rows)} rows already exist for generation_id={generation_id}.")

                for existing_row, item in zip(existing_rows, sorted_input):
                    ex_slide, ex_url, _ = existing_row
                    if ex_slide != item["slide_number"] or ex_url != item["public_url"]:
                        logger.error(f"UPLOAD_ARTIFACT_IDEMPOTENCY_CONFLICT: generation_id={generation_id} slide={item['slide_number']} mismatch (existing: {ex_url}, new: {item['public_url']})")
                        raise UploadArtifactConflictError(f"Conflict on slide {item['slide_number']} for generation_id={generation_id}.")

                # Case B: All 9 slides exactly match (slide_number and public_url). Idempotent success. No mutation.
                conn.commit()
                return

            except Exception:
                conn.rollback()
                raise
        finally:
            conn.close()

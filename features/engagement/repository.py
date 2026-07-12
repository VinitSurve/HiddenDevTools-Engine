import sqlite3
import os
from typing import Optional, List
from datetime import datetime

from config import SQLITE_DB_PATH, PROCESSING_TIMEOUT_SECONDS
from features.engagement.models import ProcessedComment, DMStatus
from features.engagement.migrations_runner import MigrationsRunner

class DeduplicationRepository:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "..", SQLITE_DB_PATH)
        # Run migrations on init
        MigrationsRunner(self.db_path).run()

    def has_processed_comment(self, comment_id: str) -> bool:
        """Check if we have already seen this exact webhook event (webhook deduplication)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_comments WHERE comment_id = ?", (comment_id,))
            return cursor.fetchone() is not None

    def has_user_received_dm(self, user_id: str, media_id: str) -> bool:
        """Check if this user has already been queued for a DM on this specific post"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM processed_comments 
                WHERE instagram_user_id = ? AND media_id = ?
            """, (user_id, media_id))
            return cursor.fetchone() is not None

    def save_processed_comment(self, comment: ProcessedComment):
        """Save a new comment to the repository"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_comments (
                    comment_id, media_id, instagram_user_id, username, 
                    original_text, normalized_text, matched_keyword, status, created_at,
                    attempt_count, last_attempt_at, last_error, next_retry_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment.comment_id,
                comment.media_id,
                comment.instagram_user_id,
                comment.username,
                comment.original_text,
                comment.normalized_text,
                comment.matched_keyword,
                comment.status.value,
                comment.created_at.isoformat(),
                comment.attempt_count,
                comment.last_attempt_at.isoformat() if comment.last_attempt_at else None,
                comment.last_error,
                comment.next_retry_at.isoformat() if comment.next_retry_at else None
            ))
            conn.commit()

    def claim_pending_comments(self, limit: int) -> List[ProcessedComment]:
        """
        Concurrency-safe claim mechanism using BEGIN IMMEDIATE.
        Selects PENDING rows, overdue PROCESSING rows, or ripe RETRYING rows.
        """
        claimed = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # BEGIN IMMEDIATE acquires a write lock early to prevent deadlocks and race conditions.
            cursor.execute("BEGIN IMMEDIATE")
            
            cursor.execute(f"""
                SELECT comment_id, media_id, instagram_user_id, username, 
                       original_text, normalized_text, matched_keyword, status, created_at,
                       attempt_count, last_attempt_at, last_error, next_retry_at
                FROM processed_comments
                WHERE status = 'PENDING'
                   OR (status = 'RETRYING' AND next_retry_at <= datetime('now'))
                   OR (status = 'PROCESSING' AND last_attempt_at <= datetime('now', '-{PROCESSING_TIMEOUT_SECONDS} seconds'))
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            if not rows:
                conn.commit()
                return []
                
            comment_ids = [row[0] for row in rows]
            now_str = datetime.now().isoformat()
            
            # Mark as processing
            placeholders = ",".join("?" * len(comment_ids))
            cursor.execute(f"""
                UPDATE processed_comments
                SET status = 'PROCESSING', last_attempt_at = ?
                WHERE comment_id IN ({placeholders})
            """, [now_str] + comment_ids)
            
            conn.commit()
            
            for row in rows:
                claimed.append(ProcessedComment(
                    comment_id=row[0],
                    media_id=row[1],
                    instagram_user_id=row[2],
                    username=row[3],
                    original_text=row[4],
                    normalized_text=row[5],
                    matched_keyword=row[6],
                    status=DMStatus.PROCESSING,
                    created_at=datetime.fromisoformat(row[8]),
                    attempt_count=row[9],
                    last_attempt_at=datetime.now(),
                    last_error=row[11],
                    next_retry_at=datetime.fromisoformat(row[12]) if row[12] else None
                ))
                
        return claimed

    def mark_sent(self, comment_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE processed_comments SET status = 'SENT' WHERE comment_id = ?", (comment_id,))
            conn.commit()
            
    def mark_failed(self, comment_id: str, reason: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processed_comments 
                SET status = 'FAILED', last_error = ? 
                WHERE comment_id = ?
            """, (reason, comment_id))
            conn.commit()

    def mark_retry(self, comment_id: str, reason: str, attempt_count: int, next_retry_at: datetime):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processed_comments 
                SET status = 'RETRYING', last_error = ?, attempt_count = ?, next_retry_at = ?
                WHERE comment_id = ?
            """, (reason, attempt_count, next_retry_at.isoformat(), comment_id))
            conn.commit()

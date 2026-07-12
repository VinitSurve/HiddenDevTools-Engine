# Enterprise Transition Runbook: Migration to PostgreSQL 16+ (`Migration_to_PostgreSQL.md`)

**Document ID:** HDT-FUT-003  
**Category:** Future & Evolution Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [ADR-010](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-010_Migration_Strategy.md), [Database Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/08_Database/Database.md), [Future Roadmap](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Future_Roadmap.md)

---

## 1. Architectural Justification (`ADR-010`)

When `HiddenDevTools-Engine` surpasses `200+ webhook events/second` or expands to multi-account management (`Phase 6`), SQLite's single-file write lock (`BEGIN IMMEDIATE`) becomes a physical throughput ceiling (`SQLITE_BUSY`). Transitioning to managed **PostgreSQL 16+** unlocks true multi-version concurrency control (MVCC) and non-blocking worker row claiming via `SELECT ... FOR UPDATE SKIP LOCKED`.

---

## 2. PostgreSQL DDL Schema Specification

```sql
-- Phase 6 Production PostgreSQL Schema (`003_pg_transition.sql`)
CREATE TABLE IF NOT EXISTS processed_comments (
    comment_id VARCHAR(128) PRIMARY KEY,
    media_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    username VARCHAR(256) NOT NULL,
    original_text TEXT NOT NULL,
    normalized_text VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'SENT', 'FAILED', 'RETRYING')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ NULL,
    last_error TEXT NULL,
    next_retry_at TIMESTAMPTZ NULL
);

-- High-concurrency composite indices
CREATE INDEX IF NOT EXISTS idx_pg_status_retry ON processed_comments (status, next_retry_at)
    WHERE status IN ('PENDING', 'PROCESSING', 'RETRYING');
CREATE INDEX IF NOT EXISTS idx_pg_user_media ON processed_comments (user_id, media_id);
```

---

## 3. Row-Level Worker Claiming Protocol (`SKIP LOCKED`)

In `repository.py`, replace SQLite `BEGIN IMMEDIATE` with PostgreSQL's non-blocking row lock:

```python
# PostgreSQL Concurrency-Safe Claiming Implementation
def claim_pending_comments_pg(self, limit: int = 10) -> List[ProcessedComment]:
    with self.db_pool.connection() as conn:
        with conn.cursor() as cursor:
            # SKIP LOCKED ensures multiple concurrent workers claim distinct batches
            # without waiting or raising database contention errors
            cursor.execute("""
                SELECT comment_id, media_id, user_id, username, original_text, normalized_text,
                       status, created_at, processed_at, attempt_count, last_attempt_at, last_error, next_retry_at
                FROM processed_comments
                WHERE status = 'PENDING'
                   OR (status = 'PROCESSING' AND last_attempt_at <= NOW() - INTERVAL '60 seconds')
                   OR (status = 'RETRYING' AND next_retry_at <= NOW())
                ORDER BY created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            """, (limit,))
            rows = cursor.fetchall()

            claimed_ids = [r[0] for r in rows]
            if claimed_ids:
                cursor.execute("""
                    UPDATE processed_comments
                    SET status = 'PROCESSING', last_attempt_at = NOW(), attempt_count = attempt_count + 1
                    WHERE comment_id = ANY(%s)
                """, (claimed_ids,))
            conn.commit()
            return [self._map_row_to_dto(r) for r in rows]
```

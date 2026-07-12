# ADR-002: Repository Pattern for Deduplication & State Tracking

**Document ID:** HDT-ADR-002  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-003 SQLite First](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-003_SQLite_First.md), [Database Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/08_Database/Database.md), [Engagement Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/07_Engagement/Engagement.md)

---

## 1. Context & Problem Statement

The interactive community engagement loop (`Comment -> DM`) relies heavily on persistent state tracking to:
1. Deduplicate incoming Meta webhook payloads (`comment_id`).
2. Prevent sending duplicate direct messages to users who comment `DEV` multiple times (`user_id + media_id`).
3. Track retry schedules and backoff counts for failed direct messages (`status='RETRYING'`, `attempt_count`, `next_retry_at`).

If `CommentProcessor` and `DMWorker` execute raw SQL statements (`sqlite3.connect().execute("SELECT ...")`) directly throughout their domain methods, the application becomes tightly coupled to SQLite. Any future decision to scale horizontally across multi-instance worker pods would require rewriting the entire domain processing logic to support PostgreSQL (`asyncpg` / `SQLAlchemy`).

---

## 2. Decision

We adopt the **Repository Architectural Pattern** by encapsulating all database access inside `DeduplicationRepository` (`features/engagement/repository.py`).

### Design Rules:
1. **Domain Isolation:** `CommentProcessor` and `DMWorker` must never import `sqlite3` or execute raw SQL queries. They must interact exclusively via typed, high-level repository methods:
   * `has_processed_comment(comment_id: str) -> bool`
   * `has_user_received_dm(user_id: str, media_id: str) -> bool`
   * `save_processed_comment(comment: ProcessedComment)`
   * `claim_pending_comments(limit: int) -> List[ProcessedComment]`
   * `mark_sent(comment_id: str)` / `mark_failed(comment_id: str, reason: str)` / `mark_retry(...)`
2. **Transactional Concurrency Enclosure:** The repository is strictly responsible for managing database transaction locks (`BEGIN IMMEDIATE`), ensuring that concurrency logic is encapsulated away from business workers.

---

## 3. Consequences

### Positive Consequences:
* **Seamless Database Portability:** To migrate from SQLite to PostgreSQL in Phase 6 (`ADR-010`), developers only need to create a `PostgreSQLDeduplicationRepository` class implementing the same signature methods. Zero lines of code change inside `CommentProcessor` or `DMWorker`.
* **Centralized Race-Condition Defense:** Concurrency lock mechanics (`BEGIN IMMEDIATE`) exist in exactly one location (`claim_pending_comments`), preventing deadlocks across the codebase.
* **Easy Mocking & Unit Testing:** In `tests/test_engagement.py`, `DeduplicationRepository` is easily instantiated against ephemeral in-memory or temporary SQLite databases (`test_engagement_uuid.db`) without requiring complex database fixtures.

### Negative Consequences / Trade-Offs:
* **Boilerplate Overhead:** Adding a new query or state column requires updating both `ProcessedComment` (`models.py`) and explicit SQL strings inside `repository.py`.

---

## 4. Codebase Reference

* **Repository Implementation:** [features/engagement/repository.py:L10-L144](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L10-L144)
* **Domain Consumption (Processor):** [features/engagement/comment_processor.py:L24-L38](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L24-L38)
* **Domain Consumption (Worker):** [features/engagement/worker.py:L22-L24](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L22-L24)

# ADR-009: Hybrid Background Task Queue Architecture

**Document ID:** HDT-ADR-009  
**Status:** Accepted (With Planned BullMQ Migration)  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-003 SQLite First](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-003_SQLite_First.md), [Engagement Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/07_Engagement/Engagement.md), [Migration to BullMQ](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Migration_to_BullMQ.md)

---

## 1. Context & Problem Statement

When Meta fires `POST /webhooks/meta` notifications for incoming Instagram comments, the server must acknowledge the request (`HTTP 200 OK`) in `< 200 milliseconds`. If the server attempts to process the comment, normalize keywords, write to SQLite, and execute `InstagramService.send_message()` synchronously inside the request handler, network latency or Graph API rate limits will cause Meta to time out and repeatedly retry sending the webhook, creating duplicate traffic storms.

To decouple webhook acknowledgment from asynchronous processing, the system requires a queue and background worker architecture. However, deploying a full external Redis + BullMQ / Celery broker stack during single-server MVP operations introduces unnecessary operational overhead and memory consumption.

---

## 2. Decision

We adopt a **Hybrid In-Memory + Persistent SQLite Queue Architecture** for Phase 1 through Phase 5 (`FastAPIDispatcher` + `DeduplicationRepository`).

### Queue Architecture & Mechanics:
1. **Immediate In-Memory Offload (`FastAPIDispatcher`):** Upon verifying `X-Hub-Signature-256`, `routers/meta_webhook.py` passes the payload to `MetaWebhookService`, which schedules processing via FastAPI native thread pools:
   ```python
   background_tasks.add_task(self.process_comment_webhook, payload)
   ```
2. **Persistent Database Queue State (`processed_comments`):** Inside the background task, `CommentProcessor.process_event()` evaluates deduplication checks and immediately inserts qualified comments into SQLite (`processed_comments`) with `status = 'PENDING'` (`save_processed_comment`).
3. **Dispatcher Trigger:** `CommentProcessor` invokes `dispatcher.dispatch(comment_id)` ([features/engagement/dispatcher.py](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/dispatcher.py)), waking up `DMWorker.process_queue()`.
4. **Transactional Claim (`BEGIN IMMEDIATE`):** `DMWorker` claims pending jobs (`claim_pending_comments`) using explicit `BEGIN IMMEDIATE` row locking, updating status to `PROCESSING` (`repository.py:L60-L118`).
5. **Persistent Exponential Backoff:** If `send_message()` fails with a retryable Graph API error, `DMWorker` updates the database row: `status = 'RETRYING'`, `next_retry_at = now + 30 * 2^(attempt-1)` (`worker.py:L38-L53`), ensuring retries are picked up on subsequent worker sweeps.

---

## 3. Consequences

### Positive Consequences:
* **Sub-200ms Webhook Acknowledgment:** The HTTP POST endpoint returns `200 OK` in `< 50ms` because heavy Graph API operations run entirely asynchronously.
* **Zero External Broker Dependency:** No Redis or RabbitMQ container required. State is persisted safely inside ACID-compliant `engagement.db`.
* **Crash Resilience for Retries:** If the process crashes while a comment is in `RETRYING` status, when the server restarts and the next event triggers `claim_pending_comments()`, the query selects rows where `status = 'RETRYING' AND next_retry_at <= datetime('now')`, resuming processing automatically.

### Negative Consequences / Trade-Offs:
* **In-Memory Task Loss Vulnerability:** If the python server process (`server.py`) undergoes `kill -9` or power loss *before* `CommentProcessor._save_comment_record()` commits to SQLite (`status = 'PENDING'`), items residing strictly inside `background_tasks.add_task` are dropped.
* **Scale Limit:** This architecture is bounded to vertical compute limits (~50 events/min). Horizontal scale requires executing [ADR-010](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-010_Migration_Strategy.md) / [Migration to BullMQ](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Migration_to_BullMQ.md).

---

## 4. Codebase Reference

* **Dispatcher Abstraction (`FastAPIDispatcher`):** [features/engagement/dispatcher.py:L9-L26](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/dispatcher.py#L9-L26)
* **Processor State Queue Insertion:** [features/engagement/comment_processor.py:L60-L66](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L60-L66)
* **Claim Engine (`claim_pending_comments`):** [features/engagement/repository.py:L60-L118](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L60-L118)

# ADR-008: End-to-End Correlation ID Tracing across Asynchronous Boundaries

**Document ID:** HDT-ADR-008  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-007 Structured Logging](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-007_Structured_Logging.md), [Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/Architecture.md), [Failures Analysis](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/reports/Failures.md)

---

## 1. Context & Problem Statement

HiddenDevTools operates two highly concurrent, multi-stage asynchronous processing pipelines:
1. **The Publishing Pipeline (`developer_tools_pipeline.py`):** Spans across Google Sheets row fetching, 9-slide image rendering, parallel multi-threaded CDN uploads (`max_workers=3`), and 3-stage Graph API container creation and verification.
2. **The Engagement & Messaging Loop (`Comment -> DM`):** Spans across `server.py` HTTP webhook reception, HMAC signature validation, asynchronous `BackgroundTasks` dispatch, SQLite transaction claiming (`claim_pending_comments`), and Graph API direct messaging.

When multiple posts are publishing concurrently or when dozens of comments arrive within seconds, standard log files interleave log statements from independent requests. Without a unique execution identifier tying log lines together, reconstructing the timeline of a specific failed post or a dropped comment requires manual, error-prone timestamp matching.

---

## 2. Decision

We mandate **End-to-End Correlation ID Tracing** across every asynchronous boundary and execution path.

### Rules of Correlation ID Propagation:
1. **Publishing Pipeline Correlation (`PUB_...`):**
   * At the very start of `run_developer_tools_pipeline()` ([pipelines/developer_tools_pipeline.py:L47-L51](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L47-L51)), the orchestrator generates a unique timestamped correlation token:
     ```python
     correlation_id = f"PUB_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
     ```
   * This ID must be prepended to every log statement emitted during rendering, uploading, publishing, and Google Sheets status writeback (`f"[{correlation_id}] Transitioning rows -> Rendering..."`).
2. **Webhook Request Correlation (`REQ_...`):**
   * When `MetaWebhookService.process_comment_webhook()` ([services/meta_webhook_service.py:L140-L145](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L140-L145)) receives an incoming comment payload, it immediately generates a 12-character UUID token:
     ```python
     correlation_id = f"REQ_{uuid.uuid4().hex[:12]}"
     ```
   * This correlation ID is embedded into the local filesystem replay archive filename (`event_TIMESTAMP_REQ_c1a2b3.json`) (`_save_for_replay:L65-L83`), attached to the `WebhookEvent` DTO, and prepended across all logs inside `CommentProcessor` (`f"[{correlation_id}] COMMENT_RECEIVED..."`).

---

## 3. Consequences

### Positive Consequences:
* **Instant Thread Reconstruction:** Running `grep "PUB_20260710_120000" server.log` immediately isolates every step of a specific carousel publish from initial sheet read to final grid permalink verification, completely filtering out interleaved traffic.
* **Deterministic Replay Auditability:** Because the correlation ID is baked into the replay filename (`fixtures/webhooks/2026/07/event_..._REQ_uuid.json`), engineers can map exact log errors directly to the underlying raw JSON payload that triggered them.

### Negative Consequences / Trade-Offs:
* **Signature Enforcement:** Every domain processor method signature must carry `correlation_id` (or receive it attached to `event.correlation_id`), ensuring it is not dropped when crossing async queue boundaries.

---

## 4. Codebase Reference

* **Publishing Correlation Generation:** [pipelines/developer_tools_pipeline.py:L47-L51](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L47-L51)
* **Webhook Correlation Generation:** [services/meta_webhook_service.py:L140-L145](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L140-L145)
* **Replay Snapshot Naming:** [services/meta_webhook_service.py:L70-L80](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L70-L80)

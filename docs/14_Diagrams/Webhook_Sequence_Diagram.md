# Canonical Webhook Reception & Direct Messaging Sequence (`Webhook_Sequence_Diagram.md`)

**Document ID:** HDT-DIAG-004  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Publishing Sequence Diagram](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Publishing_Sequence_Diagram.md), [Engagement Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/07_Engagement/Engagement.md)

---

## 1. Webhook to Direct Message Chronological Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Instagram User
    participant Meta as Meta Graph API Webhooks
    participant Server as FastAPI (`routers/meta_webhook.py`)
    participant Svc as MetaWebhookService
    participant Proc as CommentProcessor
    participant Repo as DeduplicationRepository (SQLite)
    participant Worker as DMWorker (`worker.py`)
    participant IG as InstagramService

    User->>Meta: Comments "DEV" on @hiddendevtools carousel post
    Meta->>Server: POST /webhooks/meta (X-Hub-Signature-256 header)
    Server->>Svc: validate_signature(raw_body, signature_header)
    Svc-->>Server: Signature valid (sha256 hmac.compare_digest matches)
    Server->>Server: background_tasks.add_task(process_comment_webhook, payload)
    Server-->>Meta: HTTP 200 OK (`{"status": "ok"}`) within < 200ms
    Note over Svc,Proc: Asynchronous Background Processing Phase
    Svc->>Svc: _save_for_replay() -> save raw payload to `fixtures/webhooks/...json`
    Svc->>Proc: process_event(WebhookEvent)
    Proc->>Repo: has_processed_comment(event.comment_id)
    Repo-->>Proc: False
    Proc->>Repo: has_user_received_dm(event.user_id, event.media_id)
    Repo-->>Proc: False
    Proc->>Proc: KeywordMatcher.normalize_text("DEV") -> matches keyword "DEV"
    Proc->>Repo: save_processed_comment(ProcessedComment with Status='PENDING')
    Proc->>Worker: QueueDispatcher.dispatch(comment_id) -> trigger `process_queue()`
    Worker->>Repo: claim_pending_comments(limit=10) (`BEGIN IMMEDIATE`)
    Repo->>Repo: UPDATE processed_comments SET status='PROCESSING', last_attempt_at=now
    Repo-->>Worker: Return claimed List[ProcessedComment]
    Worker->>Worker: TemplateRenderer.render_dm_template(comment.username)
    Worker->>IG: send_message(recipient_id=comment.user_id, text=template)
    IG->>Meta: POST /{page_id}/messages (`recipient={"id": user_id}`)
    alt Graph API returns HTTP 200 OK
        Meta-->>IG: `{"message_id": "mid.12345"}`
        IG-->>Worker: MessageResult(success=True, message_id="mid.12345")
        Worker->>Repo: mark_sent(comment_id) (`UPDATE status='SENT'`)
    else Graph API returns retryable rate limit (`Code 613`)
        Meta-->>IG: `{"error": {"code": 613, ...}}`
        IG-->>Worker: MessageResult(success=False, retryable=True)
        Worker->>Repo: mark_retry(comment_id, next_retry_at = now + 30*2^(attempt-1))
    else Graph API returns non-retryable permission drop (`Code 200 / Subcode 2534048`)
        Meta-->>IG: `{"error": {"code": 200, "error_subcode": 2534048, ...}}`
        IG-->>Worker: MessageResult(success=False, retryable=False)
        Worker->>Repo: mark_failed(comment_id, reason="Permission drop / not tester")
    end
```

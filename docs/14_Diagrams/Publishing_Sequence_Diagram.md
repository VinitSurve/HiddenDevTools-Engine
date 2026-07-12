# Canonical Publishing Sequence Diagram (`Publishing_Sequence_Diagram.md` & `Webhook_Sequence_Diagram.md`)

**Document ID:** HDT-DIAG-003  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Data Flow Diagram](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Data_Flow_Diagram.md), [Complete System Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Complete_System_Architecture.md)

---

## Part 1: Publishing Pipeline Sequence (`Publishing_Sequence_Diagram.md`)

```mermaid
sequenceDiagram
    autonumber
    actor Cron as Windows Task Scheduler / main.py
    participant Pipe as developer_tools_pipeline.py
    participant Sheet as sheet_api.py / SheetService
    participant Rend as DeveloperToolsRenderer / Engine
    participant Supa as SupabaseStorage
    participant IG as InstagramService
    participant Drive as DriveService

    Cron->>Pipe: run_developer_tools_pipeline(limit=7)
    Pipe->>Pipe: Check and acquire `publishing.lock`
    Pipe->>Sheet: get_draft_rows(limit=7)
    Sheet-->>Pipe: Return List[Dict] where Status == 'Draft'
    loop For each candidate draft row
        Pipe->>Pipe: Check if `row["Status"] == "Published"` OR `row["Instagram Media ID"] != ""`
        alt Already Published / Has Media ID
            Pipe->>Pipe: Skip rendering / proceed directly to writeback reconciliation
        else Valid Actionable Draft
            Pipe->>Sheet: mark_generating([row]) (`Status -> Rendering`)
            Pipe->>Rend: render_carousel(row, post_name)
            Rend->>Rend: Engine.paragraph() true-type word wrap & bounding check
            Rend-->>Pipe: Return `output/DeveloperTools_TIMESTAMP/` (9 PNG slides)
            Pipe->>Supa: upload_post_images(folder_path, gen_id) (`ThreadPoolExecutor max_workers=3`)
            Supa->>Supa: _upload_concurrently() via HTTP POST with `image/png` header
            loop For each of the 9 public CDN URLs
                Supa->>Supa: verify_url() via HTTP HEAD / GET
            end
            Supa-->>Pipe: Return verified List[str] CDN image URLs
            Pipe->>IG: publish_carousel(image_urls, caption)
            IG->>IG: Stage 1: create_media_container(image_url) x 9 (`is_carousel_item=true`)
            IG->>IG: Stage 2: wait_for_container() polling loop until all `FINISHED`
            IG->>IG: Stage 3: create_carousel(children=id1..id9, caption) -> wait_for_container()
            IG->>IG: Stage 4: publish(creation_id) -> verify_publication(media_id) -> get_permalink()
            IG-->>Pipe: Return `{"success": True, "media_id": "...", "permalink": "..."}`
            Pipe->>Sheet: mark_ready([row], post_name) (`Status -> Published`, Media ID & Post URL)
            Pipe->>Drive: archive_post_folder(local_folder_path, post_name)
        end
    end
    Pipe->>Pipe: Release and delete `publishing.lock` in `finally` block
    Pipe-->>Cron: Execution finished cleanly
```

---

## Part 2: Webhook Reception & Messaging Sequence (`Webhook_Sequence_Diagram.md`)

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

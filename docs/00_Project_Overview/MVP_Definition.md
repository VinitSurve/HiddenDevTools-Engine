# Minimum Viable Product (MVP) Definition

**Document ID:** HDT-EXEC-005  
**Category:** Project Overview  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Scope](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Scope.md), [Current Completion Percentage](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Current_Completion_Percentage.md), [Feature Matrix](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Feature_Matrix.md)

---

## 1. Canonical MVP Checklist & Success Thresholds

The Minimum Viable Product (MVP) for `HiddenDevTools-Engine` is strictly defined as an end-to-end, zero-human-intervention publishing and engagement loop for Instagram carousels. An engineering delivery is certified as MVP-complete when every item on the following checklist is checked (`[x]`) and verified in production.

```markdown
- [x] **Ingestion Engine (`SheetService`):** Read `Draft` rows from the `Developer Tools` Google Sheet, lock rows by updating status to `Rendering`, and filter out any already-`Published` rows (`developer_tools_pipeline.py`).
- [x] **Renderer Engine (`DeveloperToolsRenderer`):** Render exactly 9 visual slides (`01_Cover.png`, `02..08_Content.png`, `09_CTA.png`) using `Pillow` TrueType typography without visual clipping or word-wrap overlap.
- [x] **Cloud Storage Pipeline (`SupabaseStorage`):** Concurrently upload all 9 rendered slide images to Supabase Storage (`posts/YYYY/MM/DD/GenID/`) with `ThreadPoolExecutor(max_workers=3)` and verify HTTP `GET` access for each URL.
- [x] **Instagram Graph API Publisher (`InstagramService`):** Create 9 individual media containers, wait for processing (`check_container_status`), create the parent `CAROUSEL` container, publish to the grid (`/{ig_user_id}/media_publish`), and retrieve the canonical permalink.
- [x] **Post-Publish Sync & Archival:** Write `Media ID`, `Post URL`, and `Published At` back to Google Sheets, and perform best-effort archival of the generated slide images to Google Drive (`DriveService`).
- [x] **Webhook Signature Verification (`MetaWebhookService`):** Receive incoming POST requests on `/webhooks/meta`, validate HMAC-SHA256 (`X-Hub-Signature-256`), and respond `200 OK` immediately while queuing tasks via `FastAPI.BackgroundTasks`.
- [x] **Transactional Deduplication (`DeduplicationRepository`):** Prevent double-processing of duplicate webhooks using SQLite `INSERT OR IGNORE` and explicit `BEGIN IMMEDIATE` table locks during worker claiming.
- [x] **1-on-1 Direct Messaging (`DMWorker`):** Check commenter text against `ENGAGEMENT_KEYWORDS` (`DEV`, `TOOLS`, `LINK`), check if the user has already received a DM for that specific post, and send the curated resource link (`/{page_id}/messages`).
- [ ] **Meta App Review & Live Advanced Access:** Obtain official Meta App Review approval for `instagram_manage_messages` and `instagram_manage_comments` permissions so DMs can be delivered to general public accounts (currently restricted to App Testers in Development Mode).
```

---

## 2. Technical Acceptance Criteria for MVP Graduation

To graduate from MVP testing to full production deployment, the platform must satisfy three rigorous engineering acceptance criteria:

### 1. Zero Duplicate Publishing Guarantee
* If the pipeline crashes, experiences a network timeout, or encounters a power loss *after* `InstagramService.publish_carousel()` has successfully triggered, subsequent pipeline executions **must not** create a duplicate post on Instagram.
* **Implementation Proof:** `pipelines/developer_tools_pipeline.py` ([pipelines/developer_tools_pipeline.py:L188-L202](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L188-L202)) checks if any draft row already possesses a non-empty `Instagram Media ID` prior to calling Graph API endpoints. If found, it bypasses `publish_carousel()` and transitions directly to metadata reconciliation.

### 2. Zero Duplicate DM Guarantee
* If a single Instagram user comments `DEV` 50 times on the exact same carousel post, or if Meta fires 5 simultaneous duplicate webhook notifications for that single comment, the system **must send exactly one (1) Direct Message** to that user.
* **Implementation Proof:** `CommentProcessor.process_event()` ([features/engagement/comment_processor.py:L33-L38](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L33-L38)) queries `repository.has_user_received_dm(event.user_id, event.media_id)`. If true, the comment is recorded in SQLite with status `FAILED` (`DM_ALREADY_QUEUED`), and no message payload is dispatched to Meta.

### 3. Automatic Exponential Backoff & Self-Healing
* If the Meta Graph API returns transient errors (such as rate limit code `613` or server error code `17`), neither the publishing pipeline nor the DM worker may crash or drop records.
* **Implementation Proof:** `InstagramService._make_request()` ([services/instagram_service.py:L140-L154](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L140-L154)) sleeps for `2^attempt` seconds on transient error codes (`4, 17, 32, 613`). Similarly, `DMWorker.process_queue()` ([features/engagement/worker.py:L38-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L38-L53)) computes `next_retry_at = now + 30 * 2^(attempt-1)` for retryable DM errors and writes them back to SQLite.

# Canonical Acceptance Criteria & Verification Matrix

**Document ID:** HDT-PROD-005  
**Category:** Product Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [PRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/PRD.md), [User Stories](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/User_Stories.md), [Testing Strategy](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/11_Testing/Testing.md)

---

## 1. Subsystem Acceptance Criteria Verification Matrix

Every feature across all epics defined in [User Stories](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/User_Stories.md) must satisfy explicit, verifiable Gherkin acceptance criteria (`Given / When / Then`).

---

### AC-101: Draft Row Discovery
* **Scenario:** Discovery of actionable draft rows from Google Sheets.
* **Given** the `Developer Tools` worksheet contains 5 rows where `Status = 'Draft'` and 2 rows where `Status = 'Published'`,
* **When** `developer_tools_pipeline.py` executes `get_draft_rows(limit=7)` (`sheet_api.py`),
* **Then** the service returns exactly the 5 `Draft` dictionary records,
* **And** the 2 `Published` rows are excluded from the returned payload.

### AC-102: Idempotent Row Locking & Duplicate Publish Protection
* **Scenario:** Locking candidate rows before rendering and preventing duplicate publication.
* **Given** a draft row has just been selected by `developer_tools_pipeline.py`,
* **When** the pipeline initiates processing (`mark_generating`),
* **Then** the `Status` cell in Google Sheets is immediately updated to `Rendering`,
* **And** if a subsequent or concurrent process inspects the same row and discovers `Status == 'Published'` or a non-empty `Instagram Media ID` (`pipelines/developer_tools_pipeline.py:L188-L202`),
* **Then** the pipeline aborts `publish_carousel()` immediately and transitions directly to metadata reconciliation without triggering Graph API media creation.

### AC-103: Metadata Reconciliation upon Publication
* **Scenario:** Writing back generation and publication details to Google Sheets.
* **Given** `InstagramService.publish_carousel()` has completed successfully and verified the post permalink,
* **When** `mark_ready(draft_rows, post_name)` (`sheet_api.py`) is invoked,
* **Then** the row's `Status` cell is updated to `Published`,
* **And** `Generation ID`, `Generated At` (UTC ISO string), `Instagram Media ID`, and `Instagram Post URL` are written to their respective columns.

---

### AC-201: Dynamic Typography Word Wrapping & Bounding Box Enforcement
* **Scenario:** Rendering multi-line descriptions with automatic font-size decrement.
* **Given** a developer tool description containing 450 characters of technical text,
* **When** `Engine.paragraph()` (`engine.py`) draws the text within a designated canvas bounding box (`max_width=900, max_height=400`),
* **Then** the text wraps cleanly across line breaks without clipping outside the horizontal boundaries (`draw.textbbox`),
* **And** if the text exceeds vertical bounds (`max_height`), the font size decrements iteratively down to `min_size=16` until the entire block fits cleanly.

### AC-202: Multi-Slide Carousel Asset Generation
* **Scenario:** Programmatic output of 9 sequential slide PNGs.
* **Given** a valid `Draft` dictionary containing Name, Tagline, Category, Pricing, Description, and URL,
* **When** `DeveloperToolsRenderer.render_carousel(row, post_name)` (`renderers/developer_tools_renderer.py`) is invoked,
* **Then** exactly nine (9) high-resolution (`1080x1350`) RGBA image files (`01_Cover.png` to `09_CTA.png`) are written to `output/DeveloperTools_TIMESTAMP/`,
* **And** each slide correctly maps its corresponding text variables and background template tokens from `config.py`.

---

### AC-301: Concurrent Cloud Storage Upload (`ThreadPoolExecutor`)
* **Scenario:** Multi-threaded ingestion of slide PNGs into Supabase Storage.
* **Given** 9 rendered slide images exist inside `output/DeveloperTools_TIMESTAMP/`,
* **When** `SupabaseStorage.upload_post_images(folder_path, gen_id)` (`services/storage_service.py`) executes,
* **Then** a `ThreadPoolExecutor(max_workers=3)` initiates parallel HTTP POST requests to `https://<SUPABASE_URL>/storage/v1/object/posts/YYYY/MM/DD/GenID/`,
* **And** all 9 requests include explicit `Content-Type: image/png` headers and return HTTP `200 OK`.

### AC-302: CDN URL Accessibility Verification
* **Scenario:** Verifying public readability of CDN images prior to Graph API submission.
* **Given** `SupabaseStorage` has uploaded all 9 slide files,
* **When** `verify_url(url)` (`services/storage_service.py`) checks each CDN URL,
* **Then** an HTTP `HEAD` request (or `GET` fallback) is executed against each image URL,
* **And** if any URL returns HTTP `404` or `500`, an exception is raised before `InstagramService.publish_carousel()` is called.

---

### AC-401: Graph API Carousel Container Orchestration & Verification
* **Scenario:** End-to-end multi-stage carousel container creation and publishing.
* **Given** a list of 9 verified public CDN image URLs,
* **When** `InstagramService.publish_carousel(image_urls, caption)` (`services/instagram_service.py`) executes,
* **Then** 9 item containers (`is_carousel_item=true`) are created via `POST /{ig_user_id}/media`,
* **And** `wait_for_container()` polls each container until `check_container_status()` returns `FINISHED`,
* **And** a parent carousel container (`media_type=CAROUSEL`, `children=id1..id9`) is created and polled until `FINISHED`,
* **And** `POST /{ig_user_id}/media_publish` is invoked and returns `HTTP 200 OK` with a valid `id`,
* **And** `verify_publication(media_id)` confirms the object exists via `GET /{media_id}` and returns the canonical `permalink`.

---

### AC-501: Webhook HMAC-SHA256 Signature Security
* **Scenario:** Cryptographic validation of incoming Meta webhooks.
* **Given** an incoming HTTP `POST /webhooks/meta` request arrives at `server.py`,
* **When** `validate_signature()` (`services/meta_webhook_service.py`) evaluates the `X-Hub-Signature-256` header against the raw HTTP body using `HMAC-SHA256(META_APP_SECRET)`,
* **Then** if the computed hex digest matches the header, the endpoint returns `HTTP 200 OK` immediately (`< 200ms`),
* **And** if the signature is missing or mismatched (while `is_development() == False`), the endpoint raises `HTTPException(status_code=403, detail="Invalid signature")` and drops the payload.

### AC-502: Transactional Webhook & User DM Deduplication
* **Scenario:** Concurrency-immune claim locking and deduplication in SQLite.
* **Given** `CommentProcessor.process_event(event)` (`features/engagement/comment_processor.py`) receives a valid comment (`text='DEV'`),
* **When** `DeduplicationRepository` evaluates the event against `engagement.db`,
* **Then** if `has_processed_comment(event.comment_id)` is true, the event is skipped (`DUPLICATE_WEBHOOK_SKIPPED`),
* **And** if `has_user_received_dm(event.user_id, event.media_id)` is true, the record is saved with status `FAILED` (`DM_ALREADY_QUEUED`) and no DM is queued,
* **And** during worker claiming, `claim_pending_comments(limit=10)` executes `BEGIN IMMEDIATE` to acquire an exclusive write lock, ensuring two concurrent worker threads can never claim the exact same comment ID.

### AC-503: Exponential Backoff for Direct Message Retries
* **Scenario:** Automated self-healing during Graph API messaging rate limits.
* **Given** `DMWorker.process_queue()` (`features/engagement/worker.py`) attempts to send a DM via `InstagramService.send_message(recipient_id, text)`,
* **When** the Graph API returns a retryable transient error (`Code 613 Rate Limit Exceeded`),
* **Then** `worker.py` catches the error and invokes `repository.mark_retry()`,
* **And** the record is updated in SQLite with `status='RETRYING'`, `attempt_count = attempt_count + 1`, and `next_retry_at = now + 30 * 2^(attempt - 1)` seconds,
* **And** if `attempt_count` reaches `MAX_DM_RETRIES (3)`, the record is permanently marked `FAILED`.

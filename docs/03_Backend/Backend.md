# Complete Backend Architecture & Module Reference (`Backend.md`)

**Document ID:** HDT-BACK-001  
**Category:** Backend Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [TRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/TRD.md), [Configuration](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/03_Backend/Configuration.md), [API Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/09_APIs/API.md)

---

## 1. Complete Package & Module Catalog

The `HiddenDevTools-Engine` backend (`e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine`) consists of 22 Python source files organized across root orchestration scripts, HTTP routers, external API service adapters, visual layout renderers, and feature-encapsulated domain workers. Every file is documented below with its primary responsibilities, public interfaces, exact dependencies, and interaction patterns.

---

### 1.1 Root Orchestration & Server Modules

#### `main.py` ([main.py:L1-L73](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/main.py#L1-L73))
* **Primary Responsibilities:** Command-line entry point for scheduled carousel generation (`run_developer_tools_pipeline`). Configures UTF-8 console output encoding (`sys.stdout.reconfigure(encoding='utf-8')`), inspects today's schedule (`get_today_schedule`), retrieves actionable draft rows from Google Sheets (`get_draft_rows`), triggers visual slide rendering (`generate_post`), and writes back generation status (`mark_ready`).
* **Dependencies:** `config`, `sheet_api`, `generator`, `utils`, `schedule`.
* **Key Methods:** `main() -> None`: Orchestrates the single-post draft processing loop.

#### `server.py` ([server.py:L1-L33](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/server.py#L1-L33))
* **Primary Responsibilities:** Uvicorn FastAPI application factory (`create_app`) and HTTP server entry point (`__main__`). Configures root structured logging format (`[asctime] [levelname] [name] message`) and registers API routers (`health_router`, `meta_webhook_router`).
* **Dependencies:** `uvicorn`, `fastapi.FastAPI`, `config.PORT`, `routers.health`, `routers.meta_webhook`.
* **Key Methods:** `create_app() -> FastAPI`: Assembles and returns the configured FastAPI application instance.

#### `schedule.py` ([schedule.py:L1-L20](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/schedule.py#L1-L20))
* **Primary Responsibilities:** Inspects the `Publishing Calendar` worksheet via `sheet_api.open_sheet("Publishing Calendar")` to determine if today (`datetime.now().strftime("%A")`) has a scheduled content slot.
* **Dependencies:** `datetime.datetime`, `sheet_api.open_sheet`.
* **Key Methods:** `get_today_schedule() -> Optional[Dict[str, Any]]`: Returns the schedule dictionary row matching today's weekday name, or `None` if no schedule exists.

#### `utils.py` ([utils.py:L1-L35](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/utils.py#L1-L35))
* **Primary Responsibilities:** Filesystem directory naming and sequence tracking. Inspects `output/` to determine the next sequential post number (`Post_001`, `Post_002`) or generates timestamped folder names (`DeveloperTools_20260710_120000`).
* **Dependencies:** `os`, `re`, `datetime.datetime`.
* **Key Methods:** `get_next_post_name(output_dir: str) -> str`: Scans `output_dir` for existing directories and returns the next incremented post folder string.

---

### 1.2 Pipeline & Orchestration Modules (`pipelines/`)

#### `pipelines/developer_tools_pipeline.py` ([pipelines/developer_tools_pipeline.py:L1-L245](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L1-L245))
* **Primary Responsibilities:** The canonical, end-to-end production publishing pipeline for `@hiddendevtools`. Enforces single-instance file locking (`publishing.lock`), fetches draft rows (`sheet_api.get_draft_rows`), locks rows in Google Sheets (`mark_generating`), invokes 9-slide visual rendering (`DeveloperToolsRenderer.render_carousel`), executes multi-threaded Supabase Storage upload (`SupabaseStorage.upload_post_images`), performs HTTP `HEAD/GET` URL verification (`verify_url`), triggers Graph API 3-stage carousel publication (`InstagramService.publish_carousel`), archives slides to Google Drive (`DriveService`), and reconciles final metadata (`mark_ready`).
* **Dependencies:** `sheet_api`, `renderers.developer_tools_renderer`, `services.storage_service`, `services.instagram_service`, `services.drive_service`, `utils`.
* **Key Methods:** `run_developer_tools_pipeline(limit: int = 7) -> None`: Executes the multi-row publishing workflow inside a `try / finally` file-lock enclosure.

---

### 1.3 Service Layer & External API Adapters (`services/`)

#### `services/caption_service.py` ([services/caption_service.py:L1-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/caption_service.py#L1-L53))
* **Primary Responsibilities:** Resolves the Instagram carousel post caption based on strict order of precedence: (1) `Caption` column on the specific draft row, (2) `Caption` configuration from `Publishing Calendar` (`get_today_schedule()`), or (3) `DEFAULT_CAPTION_TEMPLATE` from `config.py`.
* **Dependencies:** `config.DEFAULT_CAPTION_TEMPLATE`, `schedule.get_today_schedule`.
* **Key Methods:** `get_caption(row: Optional[Dict], post_name: str) -> str`: Evaluates precedence rules and returns the sanitized caption string.

#### `services/drive_service.py` ([services/drive_service.py:L1-L180](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/drive_service.py#L1-L180))
* **Primary Responsibilities:** Best-effort Google Drive archival adapter using `google-api-python-client` (`build("drive", "v3", credentials=...)`). Creates parent archive directories and uploads generated PNG slides for permanent internal backup.
* **Dependencies:** `google.oauth2.service_account.Credentials`, `googleapiclient.discovery.build`, `googleapiclient.http.MediaFileUpload`, `config.GOOGLE_SERVICE_ACCOUNT_JSON`, `config.DRIVE_FOLDER_ID`.
* **Key Methods:** `archive_post_folder(local_folder_path: str, post_name: str) -> Optional[Dict[str, str]]`: Uploads local slides to Google Drive and returns folder ID/URL dictionary.

#### `services/generation_service.py` ([services/generation_service.py:L1-L90](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/generation_service.py#L1-L90))
* **Primary Responsibilities:** Asynchronous / multi-threaded slide rendering service wrapper. Isolates CPU-bound `Pillow` canvas drawing operations from async event loops using `asyncio.to_thread()`.
* **Dependencies:** `asyncio`, `renderers.developer_tools_renderer.DeveloperToolsRenderer`.
* **Key Methods:** `async generate_carousel_async(row: Dict, post_name: str) -> str`: Executes synchronous rendering inside a separate thread and returns output directory path.

#### `services/instagram_service.py` ([services/instagram_service.py:L1-780](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L1-L780))
* **Primary Responsibilities:** Production Meta Graph API v23.0 (`https://graph.facebook.com/v23.0`) adapter for Instagram Business publishing (`publish_carousel`) and direct messaging (`send_message`). Implements exponential backoff (`_make_request`), fbtrace_id logging, container polling (`check_container_status`, `wait_for_container`), carousel assembly (`create_carousel`), publication verification (`verify_publication`), permalink retrieval (`get_permalink`), and JSON direct messaging (`POST /{page_id}/messages`).
* **Dependencies:** `requests`, `config.INSTAGRAM_ACCESS_TOKEN`, `config.INSTAGRAM_BUSINESS_ACCOUNT_ID`, `config.FACEBOOK_PAGE_ID`, `config.GRAPH_API_VERSION`, `features.engagement.models.MessageResult`.
* **Key Methods:**
  * `_make_request(method, endpoint, params, json_data, max_retries, timeout) -> Dict`: Executes HTTP requests with exponential backoff on transient error codes (`4, 17, 32, 613`).
  * `send_message(recipient_id: str, text: str) -> MessageResult`: Sends 1-on-1 direct message via Instagram Messaging API.
  * `create_media_container(image_url: str) -> Dict`: Creates single slide container (`is_carousel_item=true`).
  * `wait_for_container(container_id: str, max_wait_seconds=120) -> bool`: Polls container until `FINISHED`.
  * `create_carousel(container_ids: List[str], caption: str) -> Dict`: Creates parent `CAROUSEL` container linking child IDs.
  * `publish(creation_id: str) -> Dict`: Triggers `media_publish`.
  * `publish_carousel(image_urls: List[str], caption: str) -> Dict`: Full end-to-end 3-stage carousel publication orchestrator.

#### `services/meta_webhook_service.py` ([services/meta_webhook_service.py:L1-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L1-L160))
* **Primary Responsibilities:** Cryptographic webhook signature verification and payload archiving. Validates `X-Hub-Signature-256` using `HMAC-SHA256(META_APP_SECRET, body)` (`validate_signature`), bypasses verification when `config.is_development() == True`, archives raw incoming JSON payloads to `fixtures/webhooks/YYYY/MM/event_TIMESTAMP_REQ.json` (`_save_for_replay`), extracts comment properties into `WebhookEvent` instances, and delegates processing to `CommentProcessor` (`process_comment_webhook`).
* **Dependencies:** `hmac`, `hashlib`, `json`, `uuid`, `config`, `models.webhook_event.WebhookEvent`, `features.engagement.comment_processor.CommentProcessor`.
* **Key Methods:**
  * `validate_signature(raw_body: bytes, signature_header: str) -> bool`: Computes SHA256 HMAC and performs secure comparison against `signature_header`.
  * `process_comment_webhook(payload: Dict) -> None`: Parses raw webhook event, saves disk snapshot, and triggers `CommentProcessor.process_event()`.

#### `services/sheet_service.py` ([services/sheet_service.py:L1-L120](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/sheet_service.py#L1-L120))
* **Primary Responsibilities:** Object-oriented wrapper around `gspread` v4 and `sheet_api.py`. Manages worksheet connections, filters out non-actionable rows, locks rows by transitioning `Status` to `Rendering` (`lock_row_for_rendering`), and updates final status and tracking URLs upon publication completion (`mark_row_published`).
* **Dependencies:** `sheet_api`, `gspread`.
* **Key Methods:** `lock_row_for_rendering(row: Dict) -> bool`: Updates `Status` cell to `Rendering` and returns success status.

#### `services/storage_service.py` ([services/storage_service.py:L1-L195](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/storage_service.py#L1-L195))
* **Primary Responsibilities:** Supabase Storage REST API client (`SupabaseStorage`). Uploads local slide folders (`output/GenID/*.png`) to bucket (`posts`) under `YYYY/MM/DD/GenID/` paths using multi-threaded execution (`concurrent.futures.ThreadPoolExecutor(max_workers=3)`). Enforces `Content-Type: image/png` headers (`_upload_single`) and programmatically validates public CDN URL accessibility via HTTP `HEAD/GET` (`verify_url`) before returning URL lists to the pipeline.
* **Dependencies:** `requests`, `concurrent.futures.ThreadPoolExecutor`, `config.SUPABASE_URL`, `config.SUPABASE_SERVICE_ROLE_KEY`, `config.STORAGE_BUCKET_POSTS`.
* **Key Methods:**
  * `upload_post_images(local_folder: str, gen_id: str) -> List[str]`: Concurrently uploads all slide PNGs and returns verified public CDN URLs.
  * `verify_url(url: str) -> bool`: Checks CDN URL reachability via HTTP `HEAD` / `GET`.

---

### 1.4 HTTP Router Controllers (`routers/`)

#### `routers/health.py` ([routers/health.py:L1-L22](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/routers/health.py#L1-L22))
* **Primary Responsibilities:** Liveness and readiness probe endpoint (`GET /health`). Returns `HTTP 200 OK` (`{"status": "ok", "service": "HiddenDevTools Webhook Server", "timestamp": "..."}`) for load balancers and Cloudflare tunnels.
* **Dependencies:** `fastapi.APIRouter`, `datetime.datetime`.
* **Key Methods:** `health_check() -> Dict`: Simple health status response.

#### `routers/meta_webhook.py` ([routers/meta_webhook.py:L1-L60](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/routers/meta_webhook.py#L1-L60))
* **Primary Responsibilities:** Meta Graph API Webhook endpoint controller (`APIRouter(prefix="/webhooks/meta")`).
  * `GET /webhooks/meta`: Evaluates `hub.mode == "subscribe"` and `hub.verify_token == config.META_VERIFY_TOKEN`, responding with integer `hub.challenge`.
  * `POST /webhooks/meta`: Reads raw body bytes (`await request.body()`), extracts `X-Hub-Signature-256` header, validates signature via `MetaWebhookService.validate_signature()`, queues asynchronous processing (`background_tasks.add_task(...)`), and responds `HTTP 200 OK` immediately.
* **Dependencies:** `fastapi.APIRouter`, `fastapi.Request`, `fastapi.Response`, `fastapi.BackgroundTasks`, `fastapi.HTTPException`, `config.META_VERIFY_TOKEN`, `services.meta_webhook_service.MetaWebhookService`.
* **Key Methods:** `receive_webhook(request: Request, background_tasks: BackgroundTasks) -> Dict`: Main webhook receiver and background delegator.

---

### 1.5 Feature Domain: Engagement Subsystem (`features/engagement/`)

#### `features/engagement/comment_processor.py` ([features/engagement/comment_processor.py:L1-L81](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L1-L81))
* **Primary Responsibilities:** Core domain orchestrator for incoming comment webhooks (`CommentProcessor`). Enforces double-deduplication checks against `DeduplicationRepository` (`has_processed_comment`, `has_user_received_dm`), normalizes comment text using `KeywordMatcher`, evaluates target keywords against `EngagementMode`, saves records to SQLite (`save_processed_comment`), and dispatches qualified `comment_id` tasks to `QueueDispatcher`.
* **Dependencies:** `config.ENGAGEMENT_MODE`, `config.EngagementMode`, `models.webhook_event.WebhookEvent`, `features.engagement.repository.DeduplicationRepository`, `features.engagement.models.ProcessedComment`, `features.engagement.models.DMStatus`, `features.engagement.keyword_matcher.KeywordMatcher`, `features.engagement.dispatcher.QueueDispatcher`.
* **Key Methods:** `process_event(event: WebhookEvent) -> None`: Evaluates single comment and queues DMs.

#### `features/engagement/dispatcher.py` ([features/engagement/dispatcher.py:L1-L26](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/dispatcher.py#L1-L26))
* **Primary Responsibilities:** Abstract task dispatcher (`QueueDispatcher`) and native FastAPI background task adapter (`FastAPIDispatcher`). Bridges synchronous webhook processing with background worker execution by enqueuing `DMWorker.process_queue()` tasks on `BackgroundTasks`.
* **Dependencies:** `fastapi.BackgroundTasks`, `features.engagement.worker.DMWorker`.
* **Key Methods:** `dispatch(comment_id: str) -> None`: Enqueues DM dispatch worker execution.

#### `features/engagement/keyword_matcher.py` ([features/engagement/keyword_matcher.py:L1-L45](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/keyword_matcher.py#L1-L45))
* **Primary Responsibilities:** Comment text normalization and keyword extraction (`KeywordMatcher`). Uses regex (`re.sub`) and `unicodedata.normalize("NFKD")` to strip whitespace, emojis, and punctuation, and compares upper-cased tokens against `config.ENGAGEMENT_KEYWORDS` (`DEV`, `TOOLS`, `LINK`).
* **Dependencies:** `re`, `unicodedata`, `config.ENGAGEMENT_KEYWORDS`.
* **Key Methods:**
  * `normalize_text(text: str) -> str`: Cleans raw comment strings.
  * `match_keyword(normalized_text: str) -> Optional[str]`: Returns matched keyword string or `None`.

#### `features/engagement/migrations_runner.py` ([features/engagement/migrations_runner.py:L1-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/migrations_runner.py#L1-L53))
* **Primary Responsibilities:** Sequential SQLite schema migration executor (`MigrationsRunner`). Creates `schema_migrations` tracking table, reads `.sql` scripts inside `migrations/` (`001_initial.sql`, `002_phase_4c_upgrade.sql`), compares applied versions, and executes pending SQL DDL scripts inside atomic transactions (`conn.execute("BEGIN TRANSACTION")`).
* **Dependencies:** `sqlite3`, `os`, `glob`.
* **Key Methods:** `run() -> None`: Applies all pending database migrations cleanly.

#### `features/engagement/models.py` ([features/engagement/models.py:L1-L45](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/models.py#L1-L45))
* **Primary Responsibilities:** Domain data structures and Enums. Defines `DMStatus(Enum)` (`PENDING`, `PROCESSING`, `SENT`, `FAILED`, `RETRYING`), `ProcessedComment(dataclass)` (representing a database record inside `processed_comments`), and `MessageResult(dataclass)` (representing Graph API messaging responses).
* **Dependencies:** `dataclasses`, `enum.Enum`, `datetime.datetime`.
* **Key Components:** `DMStatus`, `ProcessedComment`, `MessageResult`.

#### `features/engagement/repository.py` ([features/engagement/repository.py:L1-L144](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L1-L144))
* **Primary Responsibilities:** Concurrency-safe SQLite repository (`DeduplicationRepository`). Manages connections to `engagement.db` (`SQLITE_DB_PATH`), runs `MigrationsRunner` on init, checks webhook deduplication (`has_processed_comment`), checks user DM locking (`has_user_received_dm`), saves records (`save_processed_comment`), claims pending/overdue/retryable comments using explicit `BEGIN IMMEDIATE` transaction locking (`claim_pending_comments`), and marks final statuses (`mark_sent`, `mark_failed`, `mark_retry`).
* **Dependencies:** `sqlite3`, `os`, `config.SQLITE_DB_PATH`, `config.PROCESSING_TIMEOUT_SECONDS`, `features.engagement.models.ProcessedComment`, `features.engagement.models.DMStatus`, `features.engagement.migrations_runner.MigrationsRunner`.
* **Key Methods:**
  * `claim_pending_comments(limit: int) -> List[ProcessedComment]`: Concurrency-safe `BEGIN IMMEDIATE` claimer.
  * `mark_retry(comment_id, reason, attempt_count, next_retry_at) -> None`: Updates retry state.

#### `features/engagement/template_renderer.py` ([features/engagement/template_renderer.py:L1-L30](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/template_renderer.py#L1-L30))
* **Primary Responsibilities:** Direct message template formatting (`TemplateRenderer`). Loads `config.DM_TEMPLATE` (`"Hey @{username}! Here is the direct link..."`) and injects the commenter's exact username string.
* **Dependencies:** `config.DM_TEMPLATE`.
* **Key Methods:** `render_dm_template(username: str) -> str`: Formats and returns the DM text payload.

#### `features/engagement/worker.py` ([features/engagement/worker.py:L1-L69](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L1-L69))
* **Primary Responsibilities:** Idempotent Direct Message delivery worker (`DMWorker`). Claims batches of qualified comments from `repository.claim_pending_comments()`, renders message templates (`TemplateRenderer.render_dm_template`), dispatches payloads (`InstagramService.send_message`), and evaluates `MessageResult`:
  * If `success == True`, calls `repository.mark_sent()`.
  * If `retryable == True` and `attempt_count < MAX_DM_RETRIES`, computes exponential backoff `next_retry_at = now + timedelta(seconds = 30 * 2^(attempt-1))` and calls `repository.mark_retry()`.
  * Otherwise, calls `repository.mark_failed()`.
* **Dependencies:** `logging`, `datetime`, `config.MAX_DM_RETRIES`, `config.WORKER_BATCH_SIZE`, `features.engagement.repository.DeduplicationRepository`, `services.instagram_service.InstagramService`, `features.engagement.template_renderer.TemplateRenderer`.
* **Key Methods:** `process_queue() -> None`: Sweeps queue and dispatches DMs with retry backoff.

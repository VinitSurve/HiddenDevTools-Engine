# Technical Requirements Document (TRD)

**Document ID:** HDT-ARCH-001  
**Category:** Architectural Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [PRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/PRD.md), [Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/Architecture.md), [Backend](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/03_Backend/Backend.md), [ADR-001](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-001_Renderer_Isolation.md)

---

## 1. Architectural Philosophy & Core Design Principles

The `HiddenDevTools-Engine` repository (`e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine`) is architected around strict adherence to the **SOLID** principles, **Dependency Inversion (DIP)**, and **Domain-Driven Feature Isolation**. The system operates across three asynchronous domains: Ingestion & Rendering, Cloud Storage & Social Publishing, and Real-Time Webhook Reception & Direct Messaging.

```mermaid
graph TD
    subgraph Domain 1: Ingestion & Rendering
        Sheets[Google Sheets Ingestion] -->|gspread v4| SheetSvc[SheetService / sheet_api.py]
        SheetSvc -->|Generic Dictionary| Renderer[DeveloperToolsRenderer / Engine]
        Renderer -->|Local PNGs| OutDir[output/DeveloperTools_TIMESTAMP/]
    end
    subgraph Domain 2: Cloud Storage & Social Publishing
        OutDir -->|ThreadPoolExecutor max_workers=3| StorageSvc[SupabaseStorage Service]
        StorageSvc -->|Public URL List| PubPipeline[developer_tools_pipeline.py]
        PubPipeline -->|Graph API v23.0| IGSvc[InstagramService]
        IGSvc -->|Status Writeback| SheetSvc
    end
    subgraph Domain 3: Real-Time Webhooks & Direct Messaging
        Meta[Meta Webhooks POST /webhooks/meta] -->|HMAC-SHA256| Router[routers/meta_webhook.py]
        Router -->|FastAPI.BackgroundTasks| WebhookSvc[MetaWebhookService]
        WebhookSvc -->|Parsed WebhookEvent| CommentProc[CommentProcessor]
        CommentProc -->|BEGIN IMMEDIATE Claim| Repo[DeduplicationRepository / SQLite]
        Repo -->|Idempotent Claim| Worker[DMWorker]
        Worker -->|POST /{page_id}/messages| IGSvc
    end
```

---

## 2. Core Architectural Patterns Enforced

### 2.1 Dependency Inversion & Feature Isolation (`ADR-001`, `ADR-006`)
* **Renderer Isolation:** The rendering engine (`Engine` inside `engine.py` and `DeveloperToolsRenderer` inside `renderers/`) operates completely isolated from network interfaces, databases, or third-party storage SDKs. It receives a pure Python dictionary (`row`) and outputs local PNG assets (`output/GenID/`). It has zero knowledge of Supabase, Google Sheets, or Instagram.
* **Service Layer Decoupling:** Business domain logic (`CommentProcessor`, `DMWorker`) does not invoke `requests` or `urllib3` directly. All external API communication is abstracted behind service classes (`InstagramService`, `SheetService`, `SupabaseStorage`) whose interface signatures consume domain primitives and return structured result objects (`MessageResult`, `ProcessedComment`).

### 2.2 Repository Pattern (`ADR-002`, `ADR-003`)
* **Deduplication Abstract Layer:** All database queries for webhook deduplication (`has_processed_comment`), user DM locking (`has_user_received_dm`), state recording (`save_processed_comment`), and worker claiming (`claim_pending_comments`) are encapsulated inside `DeduplicationRepository` ([features/engagement/repository.py](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py)).
* **Database Agnosticism:** While the MVP utilizes local SQLite (`engagement.db`), the domain processor (`CommentProcessor`) interacts exclusively with repository method signatures (`repo.claim_pending_comments()`). This enables future migration to PostgreSQL (`003_pg_engagement.sql`) by replacing the internal repository driver without altering one line of domain processing code.

---

## 3. Resilience, Concurrency & Idempotency Strategies

### 3.1 Strict Idempotency Across All Execution Flows
* **Row Status Filtering:** `developer_tools_pipeline.py` ([pipelines/developer_tools_pipeline.py:L79-L87](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L79-L87)) explicitly inspects `row["Status"]`. If `row["Status"] == "Published"`, the row is ignored. If `row["Status"] == "Rendering"`, the row is skipped to avoid double-processing during concurrent cron triggers.
* **Graph API Media Protection:** Prior to calling `InstagramService.publish_carousel()`, the pipeline checks if `row["Instagram Media ID"]` is already populated ([pipelines/developer_tools_pipeline.py:L188-L202](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L188-L202)). If an ID exists, the pipeline assumes publishing previously succeeded and executes only the metadata writeback to Google Sheets.
* **Double-Deduplication DM Gate:** `CommentProcessor.process_event()` ([features/engagement/comment_processor.py:L24-L38](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L24-L38)) enforces two barriers:
  1. `has_processed_comment(comment_id)`: Blocks duplicate webhooks fired by Meta.
  2. `has_user_received_dm(user_id, media_id)`: Blocks sending a second DM to a user who comments `DEV` multiple times on the same post.

### 3.2 Transactional Concurrency Strategy (`BEGIN IMMEDIATE`)
In a concurrent environment where multiple `DMWorker` or background threads poll the database, race conditions can cause two threads to claim the same `PENDING` comment.
* **Technical Requirement:** `claim_pending_comments(limit: int)` ([features/engagement/repository.py:L60-L118](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L60-L118)) must execute `BEGIN IMMEDIATE` before scanning `SELECT ... FROM processed_comments WHERE status = 'PENDING' LIMIT ?`.
* **Mechanism:** `BEGIN IMMEDIATE` acquires a reserved SQLite write lock immediately upon transaction initiation, preventing any concurrent connection from modifying or selecting those rows until the claiming `UPDATE ... SET status = 'PROCESSING'` commits (`conn.commit()`).

### 3.3 Exponential Backoff Retry Strategy
External network calls (`Graph API`, `Supabase`) experience transient failures (`Code 4, 17, 32, 613`).
* **HTTP Level Backoff:** `_make_request()` ([services/instagram_service.py:L101-L154](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L101-L154)) intercepts transient error codes and executes exponential backoff `sleep(2^attempt)` across `max_retries = 3` before surfacing errors to the caller.
* **Worker Level Backoff:** If `DMWorker.process_queue()` encounters a retryable Graph API error (`MessageResult.retryable == True`), it marks the database row `status = 'RETRYING'` with `attempt_count = attempt_count + 1` and schedules `next_retry_at = now + timedelta(seconds = 30 * 2^(attempt - 1))`, up to `MAX_DM_RETRIES = 3` ([features/engagement/worker.py:L38-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L38-L53)).

---

## 4. Structured Logging & Correlation Strategy (`ADR-007`, `ADR-008`)

To trace distributed asynchronous executions across local terminal output, server log files, and offline replay fixtures, all components must enforce **Correlation ID Tracking**:
1. **Publishing Pipeline Correlation (`PUB_...`):** When `developer_tools_pipeline.py` starts processing a draft row, it assigns `correlation_id = f"PUB_{datetime.now().strftime('%Y%m%d_%H%M%S')}"` ([pipelines/developer_tools_pipeline.py:L47-L51](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L47-L51)). Every subsequent log statement (rendering, storage upload, container creation, verification) prefixes this ID.
2. **Webhook & Request Correlation (`REQ_...`):** When `services/meta_webhook_service.py` receives a raw webhook payload, it assigns `correlation_id = f"REQ_{uuid.uuid4().hex[:12]}"` ([services/meta_webhook_service.py:L140-L145](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L140-L145)). This correlation ID is written directly into the saved filesystem replay filename (`event_20260710_120000_REQ_c1a2b3.json`) and passed along to `CommentProcessor` and `DMWorker`.

---

## 5. Technical Migration & Scalability Roadmap

### 5.1 Future Migration to PostgreSQL (`ADR-010`)
* **Trigger Threshold:** When multi-instance container deployments (`server.py` running across 3+ load-balanced pods) are required, local file-based `engagement.db` locking (`SQLITE_BUSY`) will become a bottleneck.
* **Specification:** Create SQL migration `003_pg_engagement.sql` establishing table `processed_comments` with PostgreSQL native ENUM (`DMStatus`), and replace `sqlite3` inside `DeduplicationRepository` with an async connection pool (`SQLAlchemy 2.0` / `asyncpg`) utilizing `SELECT ... FOR UPDATE SKIP LOCKED` inside `claim_pending_comments()`.

### 5.2 Future Migration to BullMQ / Redis (`ADR-009`)
* **Trigger Threshold:** When webhook traffic exceeds 500 events/minute, in-memory `FastAPI.BackgroundTasks` (`FastAPIDispatcher`) risks memory bloat and job loss during unexpected node restarts.
* **Specification:** Replace `QueueDispatcher` with a persistent Redis queue worker (**BullMQ** via `bullmq` Python client or Celery). Webhook ingestion endpoints (`/webhooks/meta`) will push `comment_id` tasks directly to Redis, and isolated worker processes (`worker.py`) will pop jobs independently.

### 5.3 Future Multi-Platform Strategy
* **Specification:** Introduce abstract base classes `RendererInterface` and `PublisherInterface`. To publish to LinkedIn or X, implement `LinkedInCarouselRenderer` (generating PDF document carousels) and `TwitterThreadRenderer` (generating 16:9 summary cards), controlled by a unified orchestration scheduler (`MultiChannelPipeline`).

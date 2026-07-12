# System Architecture Specifications

**Document ID:** HDT-ARCH-002  
**Category:** Architectural Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [TRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/TRD.md), [Backend](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/03_Backend/Backend.md), [Complete System Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/diagrams/Complete_System_Architecture.md)

---

## 1. High-Level Layered Architecture & Service Boundaries

HiddenDevTools is architected as a clean layered monolith with strict domain separation across four distinct layers: Ingestion & Orchestration Layer, Rendering Layer, Cloud Integration Layer, and Real-Time Event & Engagement Layer.

```mermaid
graph TB
    subgraph Layer 1: Ingestion & Orchestration
        Main[main.py / Scheduler Cron] -->|Trigger| Pipeline[pipelines/developer_tools_pipeline.py]
        Pipeline -->|Fetch Draft Rows| SheetAPI[sheet_api.py / SheetService]
    end
    subgraph Layer 2: Visual Canvas Rendering
        Pipeline -->|Dictionary Input| Renderer[renderers/developer_tools_renderer.py]
        Renderer -->|Pillow Canvas Draw| Engine[engine.py / Engine]
        Engine -->|Write Local Assets| OutputDir[output/DeveloperTools_TIMESTAMP/]
    end
    subgraph Layer 3: Cloud Integrations & Publishing
        OutputDir -->|Concurrent Upload| StorageSvc[services/storage_service.py / SupabaseStorage]
        StorageSvc -->|Return CDN URLs| Pipeline
        Pipeline -->|3-Stage Graph API Publish| IGSvc[services/instagram_service.py / InstagramService]
        Pipeline -->|Archive Assets| DriveSvc[services/drive_service.py / DriveService]
        IGSvc -->|Status Writeback| SheetAPI
    end
    subgraph Layer 4: Real-Time Event & Engagement Layer
        Webhook[Meta Webhooks POST /webhooks/meta] -->|HMAC Verify| Router[routers/meta_webhook.py]
        Router -->|Background Dispatch| WebhookSvc[services/meta_webhook_service.py]
        WebhookSvc -->|Replay Save & Parse| CommentProc[features/engagement/comment_processor.py]
        CommentProc -->|Keyword Normalization| KeywordMatch[features/engagement/keyword_matcher.py]
        CommentProc -->|BEGIN IMMEDIATE Claim| Repo[features/engagement/repository.py / SQLite]
        Repo -->|Idempotent Claim| Worker[features/engagement/worker.py / DMWorker]
        Worker -->|POST /{page_id}/messages| IGSvc
    end
```

---

## 2. Complete Execution & Request Lifecycle Sequences

### 2.1 Publishing Pipeline Execution Flow (`developer_tools_pipeline.py`)

```mermaid
sequenceDiagram
    autonumber
    actor Cron as Scheduler / main.py
    participant Pipe as developer_tools_pipeline.py
    participant Sheets as sheet_api.py / SheetService
    participant Rend as DeveloperToolsRenderer / Engine
    participant Supa as SupabaseStorage
    participant IG as InstagramService

    Cron->>Pipe: run_developer_tools_pipeline(limit=7)
    Pipe->>Sheets: get_draft_rows(limit=7)
    Sheets-->>Pipe: Return List[Dict] (`Status = Draft`)
    loop For each draft row
        Pipe->>Pipe: Check row["Status"] == "Published" (Idempotent check)
        Pipe->>Sheets: mark_generating([row]) (`Status -> Rendering`)
        Pipe->>Rend: generate_post(row, post_name)
        Rend->>Rend: Engine.paragraph() dynamic typography
        Rend-->>Pipe: Return `output/DeveloperTools_TIMESTAMP/` (9 PNGs)
        Pipe->>Supa: upload_post_images(folder_path, gen_id) (`max_workers=3`)
        Supa->>Supa: verify_url() (HTTP HEAD / GET on all 9 URLs)
        Supa-->>Pipe: Return List[str] CDN image URLs
        Pipe->>Pipe: Check row["Instagram Media ID"] (Idempotent gate)
        Pipe->>IG: publish_carousel(image_urls, caption)
        IG->>IG: create_media_container() x 9 slides
        IG->>IG: wait_for_container() polling loop
        IG->>IG: create_carousel() parent container -> wait_for_container()
        IG->>IG: publish(creation_id) -> verify_publication(media_id)
        IG-->>Pipe: Return `{"success": True, "media_id": "...", "permalink": "..."}`
        Pipe->>Sheets: mark_ready([row], post_name) (`Status -> Published`, write Media ID & Post URL)
    end
    Pipe-->>Cron: Pipeline complete
```

---

### 2.2 Webhook Reception & Direct Messaging Pipeline Sequence (`Comment -> DM`)

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

    User->>Meta: Comments "DEV" on @hiddendevtools post
    Meta->>Server: POST /webhooks/meta (X-Hub-Signature-256 header)
    Server->>Svc: validate_signature(body, signature)
    Svc-->>Server: Signature valid (HMAC-SHA256 matches)
    Server->>Server: background_tasks.add_task(process_webhook_payload)
    Server-->>Meta: HTTP 200 OK (`{"status": "ok"}`) within < 200ms
    Svc->>Svc: _save_for_replay() -> write `fixtures/webhooks/2026/07/...json`
    Svc->>Proc: process_event(WebhookEvent)
    Proc->>Repo: has_processed_comment(event.comment_id)
    Repo-->>Proc: False
    Proc->>Repo: has_user_received_dm(event.user_id, event.media_id)
    Repo-->>Proc: False
    Proc->>Proc: matcher.normalize_text("DEV") -> matches keyword "DEV"
    Proc->>Repo: save_processed_comment(status='PENDING')
    Proc->>Worker: dispatcher.dispatch(comment_id) -> trigger `process_queue()`
    Worker->>Repo: claim_pending_comments(limit=10) (`BEGIN IMMEDIATE`)
    Repo->>Repo: UPDATE processed_comments SET status='PROCESSING', last_attempt_at=now
    Repo-->>Worker: Return claimed ProcessedComment
    Worker->>Worker: TemplateRenderer.render_dm_template(username)
    Worker->>IG: send_message(recipient_id=user_id, text=template)
    IG->>Meta: POST /{page_id}/messages (`recipient={"id": user_id}`)
    Meta-->>IG: HTTP 200 OK (`{"message_id": "mid.12345"}`)
    IG-->>Worker: MessageResult(success=True, message_id="mid.12345")
    Worker->>Repo: mark_sent(comment_id) (`Status -> SENT`)
```

---

## 3. Folder Philosophy & Code Organization

The repository enforces strict domain separation, isolating configuration, database migrations, rendering assets, domain features, orchestration pipelines, HTTP server endpoints, and external adapters into clean folder hierarchies:

```
HiddenDevTools-Engine/
├── assets/                     # TrueType fonts (Inter_28pt-*.ttf) and static icons
├── templates/developer_tools/  # 1080x1350 PNG slide base templates (Cover to CTA)
├── migrations/                 # SQLite database migration SQL scripts (001_initial.sql, 002...)
├── config.py                   # Singleton global settings with load_dotenv(override=True)
├── engine.py                   # Core Pillow canvas rendering class (`Engine`)
├── generator.py                # Legacy single-post generation adapter
├── main.py                     # CLI entry point for scheduled carousel generation
├── server.py                   # Uvicorn FastAPI application factory (`create_app`)
├── sheet_api.py                # Google Sheets functional abstraction layer
├── schedule.py                 # Weekly publishing schedule inspector
├── utils.py                    # Filesystem output directory naming utilities
│
├── renderers/                  # Domain-specific visual layout renderers
│   ├── base_renderer.py        # Abstract base class for all renderers
│   └── developer_tools_renderer.py # 9-slide Developer Tools carousel renderer
│
├── pipelines/                  # End-to-end orchestration workflows
│   └── developer_tools_pipeline.py # Main production publishing orchestration pipeline
│
├── routers/                    # FastAPI HTTP controllers
│   ├── health.py               # GET /health check endpoint
│   └── meta_webhook.py         # GET/POST /webhooks/meta Meta challenge and event endpoint
│
├── services/                   # External API & storage service adapters
│   ├── caption_service.py      # Caption resolution precedence engine
│   ├── drive_service.py        # Google Drive folder archival adapter
│   ├── generation_service.py   # Multi-thread/async slide rendering service wrapper
│   ├── instagram_service.py    # Meta Graph API v23.0 publishing and messaging client
│   ├── meta_webhook_service.py # Cryptographic signature validation and replay saver
│   ├── sheet_service.py        # Google Sheets row locking and status synchronization
│   └── storage_service.py      # Supabase Storage multi-threaded parallel upload client
│
├── models/                     # Shared domain primitives and DTOs
│   └── webhook_event.py        # WebhookEvent data class
│
├── features/                   # Isolated business feature modules
│   └── engagement/             # Instagram comment-to-DM engagement loop
│       ├── comment_processor.py # Comment processing, deduplication, and status routing
│       ├── dispatcher.py       # In-memory FastAPI.BackgroundTasks queue dispatcher
│       ├── keyword_matcher.py  # Text normalization and keyword matching engine
│       ├── migrations_runner.py# Automatic SQLite schema migration executor
│       ├── models.py           # ProcessedComment and DMStatus domain models
│       ├── repository.py       # SQLite transactional deduplication repository (`BEGIN IMMEDIATE`)
│       ├── template_renderer.py # Dynamic DM message template formatter
│       └── worker.py           # Idempotent DM dispatch worker with exponential backoff
│
├── tests/                      # Automated unit and integration test suite
│   └── test_engagement.py      # Comprehensive tests for engagement loop and race conditions
└── docs/                       # Exhaustive engineering knowledge base (this hierarchy)
```

---

## 4. Component Dependency Graph & Call Graph

```mermaid
graph TD
    subgraph Entry Points
        CLI[main.py / CLI] --> Pipe[pipelines/developer_tools_pipeline.py]
        FastAPI[server.py / Uvicorn] --> Router[routers/meta_webhook.py]
    end
    subgraph Pipeline Orchestrator
        Pipe --> SheetAPI[sheet_api.py / SheetService]
        Pipe --> Rend[renderers/developer_tools_renderer.py]
        Pipe --> Supa[services/storage_service.py / SupabaseStorage]
        Pipe --> IG[services/instagram_service.py / InstagramService]
        Pipe --> Drive[services/drive_service.py / DriveService]
    end
    subgraph Rendering Core
        Rend --> Engine[engine.py / Engine]
        Engine --> Config[config.py]
    end
    subgraph Webhook & Engagement Core
        Router --> WebhookSvc[services/meta_webhook_service.py]
        WebhookSvc --> Proc[features/engagement/comment_processor.py]
        Proc --> Matcher[features/engagement/keyword_matcher.py]
        Proc --> Repo[features/engagement/repository.py / DeduplicationRepository]
        Proc --> Dispatch[features/engagement/dispatcher.py / QueueDispatcher]
        Dispatch --> Worker[features/engagement/worker.py / DMWorker]
        Worker --> Repo
        Worker --> Template[features/engagement/template_renderer.py]
        Worker --> IG
    end
    Repo --> MigRunner[features/engagement/migrations_runner.py]
    MigRunner --> MigSQL[migrations/*.sql]
```

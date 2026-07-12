# Canonical Entity-Relationship & Component Visual Diagrams (`ER_Diagram.md` & `Component_Diagram.md`)

**Document ID:** HDT-DIAG-005  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Database Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/08_Database/Database.md), [Complete System Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Complete_System_Architecture.md)

---

## Part 1: Entity-Relationship Diagram (`ER_Diagram.md`)

```mermaid
erDiagram
    PROCESSED_COMMENTS {
        TEXT comment_id PK "Unique Meta comment ID (e.g. 1834767...)"
        TEXT media_id "Target Instagram Post ID (e.g. 1812608...)"
        TEXT user_id "Instagram Scoped User ID IGSID"
        TEXT username "Public Instagram handle without @"
        TEXT original_text "Raw unformatted comment text"
        TEXT normalized_text "Cleaned uppercase tokens for matching"
        TEXT status "CHECK status IN ('PENDING','PROCESSING','SENT','FAILED','RETRYING')"
        DATETIME created_at "Initial reception UTC timestamp"
        DATETIME processed_at "Timestamp of last status transition"
        INTEGER attempt_count "Number of DM attempts executed"
        DATETIME last_attempt_at "Lock acquisition timestamp during claim"
        TEXT last_error "Sanitized diagnostic Graph API error string"
        DATETIME next_retry_at "Scheduled exponential backoff timestamp"
    }
    SCHEMA_MIGRATIONS {
        TEXT version PK "Script filename (e.g. 001_initial.sql)"
        DATETIME applied_at "UTC timestamp of execution"
    }
    PROCESSED_COMMENTS ||--o{ SCHEMA_MIGRATIONS : "Enforces schema state against"
```

---

## Part 2: Component Architecture Diagram (`Component_Diagram.md`)

```mermaid
graph TB
    subgraph Client Application Layer
        IGApp[Instagram Mobile App / User Account]
        CronCLI[Task Scheduler / python main.py]
    end

    subgraph HTTP Controller & Routing Component (`routers/`)
        Server[server.py Uvicorn Application Factory]
        HealthController[routers/health.py GET /health]
        WebhookController[routers/meta_webhook.py GET/POST /webhooks/meta]
        Server --> HealthController
        Server --> WebhookController
    end

    subgraph Service Adapter Component (`services/`)
        WebhookSvc[services/meta_webhook_service.py]
        SheetSvc[services/sheet_service.py]
        StorageSvc[services/storage_service.py]
        IGSvc[services/instagram_service.py]
        DriveSvc[services/drive_service.py]
        CaptionSvc[services/caption_service.py]
        GenSvc[services/generation_service.py]
    end

    subgraph Domain Feature Component (`features/engagement/`)
        CommentProc[comment_processor.py]
        KeywordMatch[keyword_matcher.py]
        Dispatcher[dispatcher.py / QueueDispatcher]
        Repo[repository.py / DeduplicationRepository]
        Worker[worker.py / DMWorker]
        TemplateRend[template_renderer.py]
        MigRunner[migrations_runner.py]
    end

    subgraph Rendering Component (`engine.py` & `renderers/`)
        EngineCore[engine.py / Engine]
        DevToolsRend[renderers/developer_tools_renderer.py]
        DevToolsRend --> EngineCore
    end

    CronCLI --> SheetSvc
    CronCLI --> DevToolsRend
    CronCLI --> StorageSvc
    CronCLI --> IGSvc
    CronCLI --> DriveSvc
    WebhookController --> WebhookSvc
    WebhookSvc --> CommentProc
    CommentProc --> KeywordMatch
    CommentProc --> Repo
    CommentProc --> Dispatcher
    Dispatcher --> Worker
    Worker --> Repo
    Worker --> TemplateRend
    Worker --> IGSvc
    Repo --> MigRunner
```

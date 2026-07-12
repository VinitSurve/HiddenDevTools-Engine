# Canonical Component & Deployment Visual Diagrams (`Component_Diagram.md` & `Deployment_Diagram.md`)

**Document ID:** HDT-DIAG-006  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Complete System Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Complete_System_Architecture.md), [Deployment Runbook](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/12_Deployment/Deployment.md)

---

## Part 1: Standalone Component Diagram (`Component_Diagram.md`)

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

---

## Part 2: Deployment Topology Diagram (`Deployment_Diagram.md`)

```mermaid
graph LR
    subgraph Cloud Infrastructure Nodes
        SheetsCloud[Google Sheets API Cloud Node]
        DriveCloud[Google Drive API Cloud Node]
        SupabaseCloud[Supabase Cloud Object Storage Bucket `posts`]
        MetaCloud[Meta Graph API v23.0 Infrastructure]
        CloudflareNode[Cloudflare Edge Tunnel Router `trycloudflare.com`]
    end

    subgraph Host Server Node: e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\
        subgraph Process: Python Runtime 3.10+
            UvicornProcess[Uvicorn PID 2384 Port 8000 `server.py`]
            CronProcess[Task Scheduler PID `main.py`]
        end
        subgraph Filesystem Volume
            DotEnvFile[.env Credential Vault]
            LockFile[publishing.lock File Lock]
            SQLiteFile[engagement.db Database File]
            OutVolume[output/GenID/*.png Local Buffer]
            ReplayVolume[fixtures/webhooks/2026/07/*.json]
        end
    end

    MetaCloud -->|HTTPS POST| CloudflareNode
    CloudflareNode -->|cloudflared TCP 8000| UvicornProcess
    UvicornProcess --> DotEnvFile
    UvicornProcess --> SQLiteFile
    UvicornProcess --> ReplayVolume
    CronProcess --> LockFile
    CronProcess --> DotEnvFile
    CronProcess --> OutVolume
    CronProcess --> SheetsCloud
    CronProcess --> SupabaseCloud
    CronProcess --> MetaCloud
    CronProcess --> DriveCloud
```

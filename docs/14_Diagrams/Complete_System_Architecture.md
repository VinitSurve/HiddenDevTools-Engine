# Complete System Architecture & Data Flow Visual Specifications (`Complete_System_Architecture.md` & `Data_Flow_Diagram.md`)

**Document ID:** HDT-DIAG-001  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/Architecture.md), [Publishing Sequence Diagram](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Publishing_Sequence_Diagram.md), [Webhook Sequence Diagram](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Webhook_Sequence_Diagram.md)

---

## Part 1: Complete System Architecture (`Complete_System_Architecture.md`)

The diagram below maps every physical and logical boundary across the entire `HiddenDevTools-Engine` ecosystem, illustrating the complete separation of concerns between Google Workspace, Local Compute / Server Filesystem, Cloud Object Storage, and Meta Graph API v23.0 infrastructure.

```mermaid
graph TB
    subgraph External Cloud Infrastructure
        SheetsAPI[Google Sheets API v4 / SPREADSHEET_ID]
        DriveAPI[Google Drive API v3 / DRIVE_FOLDER_ID]
        SupabaseCDN[Supabase Storage REST API / STORAGE_BUCKET_POSTS]
        GraphAPI[Meta Graph API v23.0 / https://graph.facebook.com/v23.0]
        MetaWebhooks[Meta Webhook Event Dispatcher POST /webhooks/meta]
    end

    subgraph Local Server Environment e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\
        subgraph Orchestration & CLI Layer
            Scheduler[Windows Task Scheduler / cron] --> Main[main.py / CLI Entry]
            Main --> Pipe[pipelines/developer_tools_pipeline.py]
            Pipe -->|Lock check| LockFile[publishing.lock File Exclusivity Gate]
        end

        subgraph Rendering & Graphics Engine
            Pipe -->|Dictionary Input| DevToolsRend[renderers/developer_tools_renderer.py]
            DevToolsRend -->|TrueType Fonts| FontCache[assets/fonts/Inter_28pt-*.ttf]
            DevToolsRend -->|Base PNGs| Templates[templates/developer_tools/*.png]
            DevToolsRend -->|draw.textbbox| Engine[engine.py / Engine Canvas Synthesis]
            Engine -->|Write local PNGs| LocalOut[output/DeveloperTools_TIMESTAMP/01..09.png]
        end

        subgraph Service Layer Adapters
            Pipe --> SheetSvc[services/sheet_service.py / SheetService]
            SheetSvc --> SheetAPI
            Pipe --> StorageSvc[services/storage_service.py / SupabaseStorage]
            StorageSvc -->|ThreadPoolExecutor max_workers=3| SupabaseCDN
            Pipe --> IGSvc[services/instagram_service.py / InstagramService]
            IGSvc -->|Exponential backoff _make_request| GraphAPI
            Pipe --> DriveSvc[services/drive_service.py / DriveService]
            DriveSvc --> DriveAPI
        end

        subgraph Real-Time Webhook & Engagement Server
            Uvicorn[server.py / Uvicorn TCP Port 8000] --> Router[routers/meta_webhook.py]
            MetaWebhooks -->|X-Hub-Signature-256| Router
            Router -->|HMAC-SHA256 verify| WebhookSvc[services/meta_webhook_service.py]
            WebhookSvc -->|Save replay disk archive| ReplayFile[fixtures/webhooks/YYYY/MM/event_TIMESTAMP.json]
            WebhookSvc -->|BackgroundTasks| CommentProc[features/engagement/comment_processor.py]
            CommentProc --> Matcher[features/engagement/keyword_matcher.py]
            CommentProc --> Repo[features/engagement/repository.py / DeduplicationRepository]
            Repo -->|ACID Transactional Store| SQLiteDB[engagement.db SQLite File Storage]
            CommentProc --> Dispatch[features/engagement/dispatcher.py / QueueDispatcher]
            Dispatch --> Worker[features/engagement/worker.py / DMWorker]
            Worker -->|BEGIN IMMEDIATE Claim| Repo
            Worker --> TemplateRend[features/engagement/template_renderer.py]
            Worker -->|send_message POST /{page_id}/messages| IGSvc
        end
    end
```

---

## Part 2: Data Flow Diagram (`Data_Flow_Diagram.md`)

The Data Flow Diagram (DFD) below traces the journey of data primitives (`Raw Dictionary`, `Pillow Canvas Buffer`, `CDN URL`, `Webhook JSON`, `ProcessedComment DTO`) through the system from ingestion to final direct message delivery.

```mermaid
graph LR
    subgraph DFD 1: Publishing Data Flow
        SheetRow[(Google Sheets Draft Row Dict)] -->|Read| SheetSvcDFD[SheetService Ingestion]
        SheetSvcDFD -->|Draft Row Dict + post_name| RendDFD[DeveloperToolsRenderer]
        RendDFD -->|RGBA Pixel Buffer| EngineDFD[Engine.paragraph Word Wrapping]
        EngineDFD -->|Binary Image Stream| OutDirDFD[(output/GenID/*.png Local Filesystem)]
        OutDirDFD -->|Read Binary Bytes| StorageDFD[SupabaseStorage Multi-Threaded Uploader]
        StorageDFD -->|HTTP HEAD/GET Verify| CDNUrls[(List of 9 Public CDN Image URLs)]
        CDNUrls -->|POST /media is_carousel_item=true| IGStage1[Graph API Item Containers]
        IGStage1 -->|Container IDs 1..9| IGStage2[Graph API Carousel Assembly & Publish]
        IGStage2 -->|Media ID + Permalink| SheetWriteback[(Google Sheets Published Status Writeback)]
    end

    subgraph DFD 2: Engagement & Messaging Data Flow
        CommentRaw[(Raw Webhook JSON Bytes)] -->|Verify HMAC| RouterDFD[routers/meta_webhook.py]
        RouterDFD -->|Parse DTO| WebhookEventDTO[models/webhook_event.py / WebhookEvent]
        WebhookEventDTO -->|Normalize Text| MatcherDFD[KeywordMatcher / 'DEV']
        MatcherDFD -->|INSERT OR IGNORE PENDING| SQLiteDFD[(processed_comments Table in engagement.db)]
        SQLiteDFD -->|claim_pending_comments BEGIN IMMEDIATE| ClaimedDTO[ProcessedComment DTO Status=PROCESSING]
        ClaimedDTO -->|Inject username| TemplateDFD[TemplateRenderer / DM_TEMPLATE]
        TemplateDFD -->|JSON Payload {"recipient": ..., "message": ...}| IGMessageDFD[InstagramService.send_message POST /messages]
        IGMessageDFD -->|MessageResult DTO success=True| FinalStatus[(UPDATE processed_comments Status=SENT)]
    end
```

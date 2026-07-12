# Canonical Data Flow Diagram (`Data_Flow_Diagram.md`)

**Document ID:** HDT-DIAG-002  
**Category:** Diagram Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Complete System Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Complete_System_Architecture.md), [Publishing Sequence Diagram](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/14_Diagrams/Publishing_Sequence_Diagram.md)

---

## 1. End-to-End Data Pipeline Flowchart

This standalone document isolates the complete life cycle of data packets moving across the two primary processing pipelines: the **Scheduled Editorial Curation & Publishing Pipeline** and the **Real-Time Webhook Reception & Direct Messaging Pipeline**.

```mermaid
graph TD
    subgraph Pipeline A: Editorial Curation to Grid Publication
        A1[Google Sheets Draft Row Dictionary] -->|sheet_api.get_draft_rows| A2[developer_tools_pipeline.py Orchestrator]
        A2 -->|Check & Lock row.Status = Rendering| A3[Google Sheets Lock Writeback]
        A2 -->|Raw Text Dictionary + post_name| A4[DeveloperToolsRenderer / Engine]
        A4 -->|TrueType Bounding Box Calculation| A5[Pillow ImageDraw RGBA Memory Buffer]
        A5 -->|Save 9 PNGs| A6[output/DeveloperTools_TIMESTAMP/ Filesystem]
        A6 -->|ThreadPoolExecutor max_workers=3| A7[SupabaseStorage.upload_post_images]
        A7 -->|HTTP HEAD / GET Reachability Verification| A8[List of 9 Public CDN Image URLs]
        A8 -->|POST /{ig_user_id}/media is_carousel_item=true| A9[Meta Graph API 9 Slide Containers]
        A9 -->|Polling wait_for_container FINISHED| A10[POST /{ig_user_id}/media CAROUSEL Parent]
        A10 -->|POST /{ig_user_id}/media_publish| A11[Published Instagram Grid Post Object]
        A11 -->|GET /{media_id} permalink| A12[SheetService.mark_ready Writeback Status=Published]
    end

    subgraph Pipeline B: Real-Time Engagement & Direct Messaging
        B1[Incoming Meta HTTP POST /webhooks/meta Raw Bytes] -->|hmac.compare_digest SHA256| B2[routers/meta_webhook.py Security Gate]
        B2 -->|BackgroundTasks Dispatch| B3[services/meta_webhook_service.py Replay Saver]
        B3 -->|Write raw payload| B4[fixtures/webhooks/YYYY/MM/event_TIMESTAMP_REQ.json]
        B3 -->|Parse WebhookEvent DTO| B5[features/engagement/comment_processor.py]
        B5 -->|Check 1: has_processed_comment| B6[DeduplicationRepository SQLite Query]
        B5 -->|Check 2: has_user_received_dm| B6
        B5 -->|Normalize text & match 'DEV'| B7[KeywordMatcher]
        B7 -->|INSERT OR IGNORE PENDING| B8[(processed_comments Table in engagement.db)]
        B8 -->|QueueDispatcher.dispatch| B9[features/engagement/worker.py / DMWorker]
        B9 -->|claim_pending_comments BEGIN IMMEDIATE| B10[ProcessedComment DTO Status=PROCESSING]
        B10 -->|Format username token| B11[TemplateRenderer.render_dm_template]
        B11 -->|POST /{page_id}/messages JSON Payload| B12[InstagramService.send_message]
        B12 -->|MessageResult DTO success=True| B13[repository.mark_sent UPDATE Status=SENT]
        B12 -->|MessageResult DTO retryable=True| B14[repository.mark_retry UPDATE Status=RETRYING next_retry_at]
    end
```

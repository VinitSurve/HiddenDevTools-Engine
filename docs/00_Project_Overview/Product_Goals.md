# Product Goals & Engineering Objectives

**Document ID:** HDT-EXEC-003  
**Category:** Project Overview  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Project Vision](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Project_Vision.md), [Scope](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Scope.md), [MVP Definition](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/MVP_Definition.md)

---

## 1. Primary Engineering & Business Goals

The HiddenDevTools engineering effort is driven by five concrete, measurable product goals designed to maximize developer value while minimizing operational overhead.

| Goal ID | Goal Title | Description | Target Metric / Acceptance Threshold |
| :--- | :--- | :--- | :--- |
| **G-01** | **Zero-Touch Carousel Production** | Completely automate the visual rendering of 9-slide developer tool carousels directly from curated Google Sheets rows without human graphic design intervention. | **< 15 seconds** total rendering time for 9 slides; **0** visual overlap defects across variable-length descriptions. |
| **G-02** | **High-Availability Cloud Ingestion** | Ensure all generated local slide assets (`output/DeveloperTools_TIMESTAMP/`) are safely uploaded to high-speed CDN cloud storage (`Supabase Storage`) with exact MIME verification (`image/png`). | **> 99.9%** successful upload rate; strict verification via HTTP `HEAD`/`GET` fallback before publishing. |
| **G-03** | **Autonomous Instagram Publishing** | Publish multi-image carousels directly to the `@hiddendevtools` Instagram Business feed using the official Meta Graph API v23.0 (`/media` -> `/media_publish`) with full container polling. | **100%** idempotent publishing (no duplicate grid posts); automated recovery from transient rate limits (`429`, `613`). |
| **G-04** | **Instant Real-Time DM Delivery** | Listen for real-time Instagram comment webhooks via HTTPS, normalize commenter text, match target keywords (e.g., `DEV`), and dispatch the curated resource link via Direct Message within seconds. | **< 3 seconds** P95 delivery latency from webhook arrival to DM dispatch; **100%** deduplication accuracy per post. |
| **G-05** | **Zero-Data-Loss Operational State** | Maintain accurate, real-time lifecycle tracking across Google Sheets (`Status`, `Post`, `Generated At`, `Generation ID`, `Instagram Media ID`, `Instagram Post URL`) and local SQLite repositories (`processed_comments`). | **Zero ($0$)** untracked state transitions; full replay capability for raw webhook payloads (`fixtures/webhooks/`). |

---

## 2. Technical Objectives & Architectural Alignment

### Objective 1: Strict Idempotency Across All Execution Paths
Every state-changing operation in the codebase must be safely retriable without causing duplicate external side effects:
* **Google Sheets Status Filtering:** `developer_tools_pipeline.py` ([pipelines/developer_tools_pipeline.py:L79-L87](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L79-L87)) explicitly inspects the `Status` column of each draft row. If any row is already marked `Published`, the entire pipeline aborts immediately.
* **Media ID Protection:** If an unexpected power outage occurs between Instagram Graph API publishing and Google Sheets sync, the pipeline checks if `Instagram Media ID` is already present ([pipelines/developer_tools_pipeline.py:L188-L202](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L188-L202)) and skips `publish_carousel()` to avoid double-posting to the Instagram grid.
* **Webhook Deduplication:** The SQLite repository ([features/engagement/repository.py:L38-L58](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L38-L58)) uses `INSERT OR IGNORE INTO processed_comments` with unique primary keys (`comment_id`) and explicit `instagram_user_id + media_id` checks to guarantee a single user receives at most one DM per Instagram post.

### Objective 2: Concurrency & Race-Condition Immunity
Because Meta often dispatches duplicate webhook notifications almost simultaneously when users comment rapidly or when network retries occur, the database layer must prevent race conditions:
* `claim_pending_comments()` ([features/engagement/repository.py:L60-L118](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L60-L118)) acquires an immediate SQLite write lock (`BEGIN IMMEDIATE`) before scanning `PENDING` or overdue `PROCESSING` records. This ensures that concurrent background threads cannot claim the same comment ID.

### Objective 3: Fault Isolation & Self-Healing Backoff
External cloud services (Meta Graph API, Supabase Storage, Google Drive API) experience transient failures, network hiccups, and rate limits:
* `_make_request` ([services/instagram_service.py:L80-L200](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L80-L200)) automatically detects Meta transient error codes (`4, 17, 32, 613`) and executes exponential backoff (`delay = 2^attempt`).
* `DMWorker.process_queue()` ([features/engagement/worker.py:L38-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L38-L53)) transitions failed DMs to `RETRYING` status with `next_retry_at = now + 30 * 2^(attempt-1)` seconds, up to `MAX_DM_RETRIES = 3`.

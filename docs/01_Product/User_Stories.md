# User Stories & Engineering Epics

**Document ID:** HDT-PROD-004  
**Category:** Product Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [PRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/PRD.md), [Acceptance Criteria](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md), [TRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/TRD.md)

---

## 1. Epic 1: Automated Content Ingestion & Spreadsheet Synchronization

### User Story US-101: Discover Draft Content Rows
* **As a** Content Curator (`@hiddendevtools` Admin),
* **I want** the system to automatically discover rows in the `Developer Tools` Google Sheet where `Status` is marked `Draft`,
* **So that** I do not have to manually trigger individual rendering scripts for every new developer tool.
* **Acceptance Criteria Reference:** [AC-101](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-101-draft-row-discovery)

### User Story US-102: Prevent Duplicate Publishing via Spreadsheet Locking
* **As an** Engineering Manager,
* **I want** the ingestion pipeline to immediately lock candidate rows (`Status = Rendering`) and reject any row that has already been marked `Published` or possesses a valid `Instagram Media ID`,
* **So that** transient network failures or accidental double-executions never cause duplicate carousels to appear on the Instagram grid.
* **Acceptance Criteria Reference:** [AC-102](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-102-idempotent-row-locking)

### User Story US-103: Write Back Execution Metadata upon Completion
* **As a** Content Curator,
* **I want** the system to write back exact operational metadata (`Status = Published`, `Instagram Media ID`, `Instagram Post URL`, `Generated At`) to my Google Sheet row upon publication,
* **So that** I maintain complete auditability over my content pipeline directly from my spreadsheet dashboard.
* **Acceptance Criteria Reference:** [AC-103](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-103-metadata-reconciliation)

---

## 2. Epic 2: Visual Canvas Rendering & Slide Assembly

### User Story US-201: Dynamic Word Wrapping & Typography Scaling
* **As a** Brand Designer,
* **I want** the rendering engine (`Engine`) to dynamically calculate text bounding boxes using TrueType font files (`Inter_28pt-*.ttf`) and automatically wrap or scale down variable-length developer tool descriptions (`min_size=16`),
* **So that** long technical descriptions never overflow canvas boundaries or collide with pricing badges across any of the 9 slides.
* **Acceptance Criteria Reference:** [AC-201](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-201-dynamic-typography)

### User Story US-202: 9-Slide Developer Tool Carousel Generation
* **As a** Content Curator,
* **I want** `DeveloperToolsRenderer` to take my structured row data and generate exactly nine (9) sequentially numbered PNG slides (`01_Cover.png` to `09_CTA.png`) inside a local timestamped directory (`output/DeveloperTools_TIMESTAMP/`),
* **So that** all visual assets adhere strictly to the `@hiddendevtools` visual layout standards without manual graphic design intervention.
* **Acceptance Criteria Reference:** [AC-202](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-202-multi-slide-generation)

---

## 3. Epic 3: Cloud Storage Uploads & CDN Accessibility

### User Story US-301: Parallel Multi-Threaded Cloud Storage Upload
* **As a** DevOps Engineer,
* **I want** `SupabaseStorage` to upload all 9 rendered slide images concurrently (`ThreadPoolExecutor max_workers=3`) to our Supabase Storage bucket (`posts/YYYY/MM/DD/GenID/`) with explicit `image/png` MIME headers,
* **So that** asset upload latency is minimized prior to initiating Graph API container requests.
* **Acceptance Criteria Reference:** [AC-301](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-301-concurrent-storage-upload)

### User Story US-302: Programmatic CDN URL Verification
* **As a** Backend Engineer,
* **I want** the storage service to verify every public CDN image URL via HTTP `HEAD` / `GET` requests (`verify_url`) before passing them to the Instagram publisher,
* **So that** Meta Graph API does not reject item containers due to unreadable or incomplete CDN image paths.
* **Acceptance Criteria Reference:** [AC-302](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-302-cdn-url-verification)

---

## 4. Epic 4: Instagram Graph API Carousel Publishing

### User Story US-401: Asynchronous Carousel Container Orchestration
* **As a** Backend Engineer,
* **I want** `InstagramService` to execute the complete 3-stage Graph API v23.0 carousel flow (`create_media_container` for each slide -> `wait_for_container` polling loop -> `create_carousel` parent -> `publish`),
* **So that** multi-image carousels are published safely even during high Meta server processing queues.
* **Acceptance Criteria Reference:** [AC-401](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-401-carousel-publishing)

---

## 5. Epic 5: Real-Time Webhooks & Direct Messaging Loop

### User Story US-501: Secure Webhook Reception & Cryptographic Signature Validation
* **As a** Security Engineer,
* **I want** our FastAPI webhook server (`server.py`, `routers/meta_webhook.py`) to cryptographically verify the `X-Hub-Signature-256` header against `META_APP_SECRET` (`validate_signature`),
* **So that** malicious actors cannot forge or inject fake comment events into our engagement pipeline.
* **Acceptance Criteria Reference:** [AC-501](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-501-webhook-security)

### User Story US-502: Concurrency-Immune Webhook Deduplication & User DM Locking
* **As a** Software Engineer (`@vinit.surve.pvt`),
* **I want** the engagement system (`DeduplicationRepository` + `CommentProcessor`) to verify if my exact comment ID or my Instagram user ID + post ID combination has already been processed using SQLite `INSERT OR IGNORE` and `BEGIN IMMEDIATE` table locks,
* **So that** commenting `DEV` multiple times or receiving duplicate Meta webhook notifications never causes me to receive duplicate DM spam.
* **Acceptance Criteria Reference:** [AC-502](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-502-transactional-deduplication)

### User Story US-503: Automated Exponential Backoff for Direct Message Delivery
* **As a** DevOps Engineer,
* **I want** `DMWorker` to catch transient Meta Graph API messaging errors (`Code 4, 17, 32, 613`) and transition the comment record to `RETRYING` status with exponential backoff (`30s * 2^(attempt-1)` up to `MAX_DM_RETRIES=3`),
* **So that** temporary rate limits never result in dropped direct messages or lost community engagement.
* **Acceptance Criteria Reference:** [AC-503](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/01_Product/Acceptance_Criteria.md#ac-503-worker-exponential-backoff)

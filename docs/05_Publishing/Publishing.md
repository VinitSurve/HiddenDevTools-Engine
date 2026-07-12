# Publishing Pipeline & Orchestration Architecture (`Publishing.md`)

**Document ID:** HDT-PUB-001  
**Category:** Publishing Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Supabase Integration](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/05_Publishing/Supabase_Integration.md), [Instagram Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/06_Instagram/Instagram.md), [ADR-004](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-004_Supabase_Storage.md), [ADR-005](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-005_Instagram_Graph_API.md)

---

## 1. Subsystem Overview & End-to-End Orchestration

The production publishing engine (`pipelines/developer_tools_pipeline.py`) is the centralized orchestrator that bridges Google Sheets metadata curation (`sheet_api.py`), local canvas rendering (`DeveloperToolsRenderer`), cloud CDN object storage (`SupabaseStorage`), Instagram Graph API v23.0 carousel publishing (`InstagramService`), and Google Drive permanent archival (`DriveService`).

```mermaid
graph TD
    Cron[Schedule Trigger / main.py] -->|limit=7| LockGate{Acquire Lock file publishing.lock}
    LockGate -->|Lock Acquired| Fetch[SheetService.get_draft_rows limit=7]
    LockGate -->|Lock Busy| ExitLocked[Log Warning & Exit Safely]
    Fetch --> Loop[Iterate Discovered Draft Rows]
    subgraph Row Processing Lifecycle
        Loop --> IdempotencyGate{row.Status == 'Published' OR Media ID Exists?}
        IdempotencyGate -->|Yes| Skip[Skip / Reconcile Metadata Only]
        IdempotencyGate -->|No| LockRow[SheetService.mark_generating Status->Rendering]
        LockRow --> Render[DeveloperToolsRenderer.render_carousel]
        Render -->|9 PNGs in output/GenID/| Upload[SupabaseStorage.upload_post_images max_workers=3]
        Upload -->|9 Public CDN URLs| VerifyURL[SupabaseStorage.verify_url HTTP HEAD/GET]
        VerifyURL -->|URLs Accessible| GraphAPI[InstagramService.publish_carousel]
        GraphAPI -->|Verify GET /{media_id}| Writeback[SheetService.mark_ready Status->Published + Post URL]
        Writeback --> Archive[DriveService.archive_post_folder Drive Backup]
    end
    Loop -->|Finally Enclosure| ReleaseLock[Delete publishing.lock]
```

---

## 2. Process Concurrency Locking (`publishing.lock`)

To prevent duplicate publications if a cron scheduler triggers `main.py` twice concurrently while a slow carousel is mid-generation, `run_developer_tools_pipeline()` ([pipelines/developer_tools_pipeline.py:L45-L65](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L45-L65)) enforces filesystem-level process exclusion:

```python
lock_file = os.path.join(os.getcwd(), "publishing.lock")
if os.path.exists(lock_file):
    logger.warning("Lock file publishing.lock exists. Pipeline already running. Exiting.")
    return

try:
    with open(lock_file, "w") as f:
        f.write(f"PID: {os.getpid()} - Started at: {datetime.now().isoformat()}")
    # Execute Pipeline logic...
finally:
    if os.path.exists(lock_file):
        os.remove(lock_file)
```

---

## 3. Detailed Stage-by-Stage Publishing Lifecycle

### Stage 1: Google Sheets Discovery & Idempotent Row Locking ([pipelines/developer_tools_pipeline.py:L70-L100](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L70-L100))
1. The orchestrator calls `sheet_api.get_draft_rows(limit=7)`, inspecting rows in the `Developer Tools` sheet where `Status == "Draft"`.
2. For each discovered row, the pipeline checks two idempotency guards:
   * **Row Status Guard:** If `row.get("Status") == "Published"`, log a skip warning and proceed to the next row.
   * **Media ID Guard:** If `row.get("Instagram Media ID")` is non-empty, the pipeline assumes the post published previously during a network disconnect or partial run. It bypasses rendering/Graph API submission and immediately executes the reconciliation writeback (`mark_ready`).
3. If both guards pass, the pipeline immediately updates the row in Google Sheets via `mark_generating([row])`, setting `Status = "Rendering"`. This locks the row against any concurrent background cron workers.

### Stage 2: Visual Canvas Generation ([pipelines/developer_tools_pipeline.py:L105-L125](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L105-L125))
1. Computes the next sequential directory name (`post_name = utils.get_next_post_name("output")` -> e.g., `Post_012`).
2. Invokes `DeveloperToolsRenderer().render_carousel(row, post_name)`, which executes offline canvas synthesis (`Engine`) and saves exactly 9 sequential PNGs to `output/Post_012/`.

### Stage 3: Multi-Threaded Supabase Storage Ingestion ([pipelines/developer_tools_pipeline.py:L130-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L130-L160))
1. Invokes `storage_service.upload_post_images(local_folder_path, gen_id=post_name)`.
2. `SupabaseStorage` uploads all 9 slides concurrently using a `ThreadPoolExecutor(max_workers=3)`, applying `Content-Type: image/png` headers.
3. Once all uploads complete, `verify_url(url)` executes HTTP `HEAD` checks against each generated public CDN URL (`https://.../storage/v1/object/public/posts/...`). If any URL fails reachability check (`404` or `500`), the pipeline raises an exception and aborts before calling Graph API.

### Stage 4: 3-Stage Meta Graph API Carousel Orchestration ([pipelines/developer_tools_pipeline.py:L165-L215](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L165-L215))
1. Resolves the caption string via `CaptionService.get_caption(row, post_name)`.
2. Invokes `instagram_service.publish_carousel(image_urls, caption)`.
3. `InstagramService` executes the official Meta Graph API v23.0 3-stage flow:
   * **Container Creation:** Creates 9 item containers via `POST /{ig_user_id}/media` (`is_carousel_item=true`).
   * **Container Polling:** Polls each item container (`wait_for_container`) until all report `status_code == "FINISHED"`.
   * **Carousel Assembly:** Creates parent carousel via `POST /{ig_user_id}/media` (`media_type="CAROUSEL"`, `children=id1..id9`) and polls until `FINISHED`.
   * **Grid Publication:** Triggers `POST /{ig_user_id}/media_publish(creation_id)`.
   * **Object Verification:** Verifies post existence via `GET /{media_id}` and retrieves the canonical `permalink` (`https://www.instagram.com/p/C.../`).

### Stage 5: Spreadsheet Reconciliation & Google Drive Archival ([pipelines/developer_tools_pipeline.py:L218-L245](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L218-L245))
1. Calls `sheet_api.mark_ready([row], post_name)`, which updates the Google Sheet row:
   * `Status` -> `"Published"`
   * `Generation ID` -> `post_name`
   * `Generated At` -> Current UTC ISO string
   * `Instagram Media ID` -> `result["media_id"]`
   * `Instagram Post URL` -> `result["permalink"]`
2. Invokes `drive_service.archive_post_folder(local_folder_path, post_name)`, uploading the 9 local PNG slides to a dedicated Google Drive folder for permanent corporate backup.

---

## 4. Error Handling & Rollback Protocol

If an unhandled exception occurs during `render_carousel()`, `upload_post_images()`, or `publish_carousel()` (for example, if Graph API returns `Code 190 Session Expired` or `Code 368 Rate Limit`):
1. The exception is caught inside the `run_developer_tools_pipeline` row loop.
2. The pipeline logs a structured `logger.error(f"[{correlation_id}] Failed to process row {row.get('Name')}: {e}", exc_info=True)`.
3. **Spreadsheet Rollback:** To ensure the row is not permanently stuck in `Rendering` status, the pipeline executes best-effort rollback:
   ```python
   try:
       row["Status"] = "Draft"
       # Write Status back to 'Draft' in Google Sheets...
   except Exception as rollback_err:
       logger.error(f"Rollback failed for row: {rollback_err}")
   ```
4. The pipeline cleanly releases `publishing.lock` in the `finally:` block and continues to the next available draft row without crashing the master process.

# ADR-004: Supabase Storage for High-Speed Image Ingestion

**Document ID:** HDT-ADR-004  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-001 Renderer Isolation](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-001_Renderer_Isolation.md), [Storage Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/05_Publishing/Supabase_Integration.md)

---

## 1. Context & Problem Statement

The Meta Graph API v23.0 carousel publishing endpoints (`POST /{ig_user_id}/media`) strictly require publicly accessible, high-bandwidth HTTPS image URLs (`image_url`). Meta servers do not accept direct `multipart/form-data` binary image uploads when creating carousel items via Graph API.

Therefore, once `DeveloperToolsRenderer` generates 9 local slide PNGs (`output/DeveloperTools_TIMESTAMP/`), the pipeline requires a cloud object store capable of:
1. Fast, reliable file ingestion via simple HTTP REST POST endpoints.
2. Immediate public CDN URL generation (`https://<SUPABASE_URL>/storage/v1/object/public/posts/...`).
3. Low-latency, high-availability `GET` accessibility from Meta's global crawler infrastructure (`facebookexternalhit`).

---

## 2. Decision

We select **Supabase Storage (REST API)** (`services/storage_service.py`) as the canonical cloud storage provider for all pre-published carousel slides.

### Technical Implementation Rules:
1. **Parallel Multi-Threaded Uploading:** `SupabaseStorage` shall execute multi-threaded parallel uploads (`ThreadPoolExecutor(max_workers=3)`) (`_upload_concurrently`) to upload all 9 slides simultaneously, cutting total storage ingestion latency by >65%.
2. **Explicit MIME Verification:** All upload requests must pass explicit headers: `{"Content-Type": "image/png", "cacheControl": "3600"}` (`_upload_single`).
3. **Mandatory Pre-Publish Verification:** Before returning public CDN URLs to `developer_tools_pipeline.py`, the storage service must execute `verify_url()` against every generated URL using HTTP `HEAD` (with `GET` fallback). If Meta external hit crawlers would encounter a `404 Not Found` or `403 Forbidden`, the pipeline aborts before invoking Graph API.

---

## 3. Consequences

### Positive Consequences:
* **Instant Public CDN Access:** Supabase Storage automatically routes requests through global Cloudflare CDN caching layers, ensuring Meta Graph API container creation attempts download images without timeouts.
* **Simple REST Abstraction:** No heavy AWS S3 `boto3` dependency footprint. The upload client uses standard Python `requests.post` directly against Supabase storage buckets.
* **Deterministic Folder Structuring:** Slides are organized cleanly under `posts/YYYY/MM/DD/GenID/01_Cover.png`, making manual inspection or cleanup straightforward.

### Negative Consequences / Trade-Offs:
* **Storage Quota Consumption:** Unused or failed draft generations leave PNG files inside the Supabase bucket indefinitely unless periodic cleanup scripts or bucket lifecycle policies (`expiration=30d`) are enforced.

---

## 4. Codebase Reference

* **Storage Service Class:** [services/storage_service.py:L26-L195](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/storage_service.py#L26-L195)
* **Parallel Upload Engine:** [services/storage_service.py:L130-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/storage_service.py#L130-L160)
* **URL Verification Logic:** [services/storage_service.py:L162-L195](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/storage_service.py#L162-L195)

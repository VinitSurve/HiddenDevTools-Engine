# ADR-001: Strict Renderer Isolation & Canvas Separation

**Document ID:** HDT-ADR-001  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [TRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/TRD.md), [Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/Architecture.md), [Renderer Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/04_Rendering/Renderer.md)

---

## 1. Context & Problem Statement

In automated content publishing platforms, a common architectural antipattern is coupling the visual graphic generation logic (`Pillow`, `Canvas`, `Cairo`) directly with data ingestion drivers (`Google Sheets SDK`, `gspread`), network uploaders (`requests`, `Boto3`, `Supabase`), or social media API clients (`Meta Graph API`).

When rendering classes directly invoke network calls or database queries:
1. **Testing Complexity:** Unit testing typographic alignment or word-wrapping requires mocking external API calls, storage credentials, and HTTP responses.
2. **Reusability Bottleneck:** If the platform expands from Instagram carousels to LinkedIn PDF carousels or offline batch exports, the rendering code cannot be reused because it is entangled with Instagram-specific publishing logic.
3. **Execution Latency:** Network retries or database connection delays block visual rendering threads, causing unpredictable generation latency.

---

## 2. Decision

We mandate **Strict Renderer Isolation**. The visual rendering subsystem (`Engine` inside `engine.py` and all domain renderers inside `renderers/`) must operate purely as a deterministic, local, filesystem-bound image processing pipeline.

### Rules of Renderer Isolation:
1. **No Network SDKs:** Renderers shall never import or execute `requests`, `gspread`, `urllib3`, `supabase`, or `httpx`.
2. **No Database Dependencies:** Renderers shall never import `sqlite3`, `sqlalchemy`, or access `engagement.db`.
3. **Strict Data Ingestion Contract:** Every renderer method (`DeveloperToolsRenderer.render_carousel(row, post_name)`) shall accept a pure Python dictionary (`row: Dict[str, Any]`) containing pre-fetched, validated textual metadata and a string folder name (`post_name`).
4. **Strict Output Contract:** Renderers shall write their generated PNG outputs exclusively to a local filesystem folder (`output/DeveloperTools_TIMESTAMP/`) and return the absolute filesystem path (`str`) to the calling orchestrator.

---

## 3. Consequences

### Positive Consequences:
* **Blazing Fast Unit Testing:** `test_generating.py` and `test_font.py` execute in milliseconds without network access, validating text wrapping, bounding boxes, and font rendering offline.
* **Total Reusability:** The orchestrator (`developer_tools_pipeline.py`) can swap `DeveloperToolsRenderer` with a `LinkedInCarouselRenderer` or `TwitterCardRenderer` without modifying the rendering base class (`BaseRenderer`).
* **Deterministic Output:** Given the exact same dictionary input (`row`), the renderer produces identical pixel-for-pixel PNG slides every time.

### Negative Consequences / Trade-Offs:
* **Intermediate Local Disk I/O:** Because the renderer cannot stream image bytes directly over the network to Supabase Storage, images must first be written to local disk (`output/GenID/*.png`) and then read back by `SupabaseStorage.upload_post_images()`. This requires ensuring local disk space is managed or pruned over time (`DriveService` / cleanup utilities).

---

## 4. Codebase Reference

* **Core Engine Implementation:** [engine.py:L13-L172](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/engine.py#L13-L172)
* **Domain Renderer Implementation:** [renderers/developer_tools_renderer.py:L12-L135](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/renderers/developer_tools_renderer.py#L12-L135)
* **Orchestrator Invocation:** [pipelines/developer_tools_pipeline.py:L106-L121](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/pipelines/developer_tools_pipeline.py#L106-L121)

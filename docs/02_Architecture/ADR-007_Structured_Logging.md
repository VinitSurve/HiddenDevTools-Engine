# ADR-007: Standardized Structured Observability & Logging

**Document ID:** HDT-ADR-007  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-008 Correlation IDs](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-008_Correlation_IDs.md), [Security Audit](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/10_Security/Security.md), [Operations specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/13_Operations/Operations.md)

---

## 1. Context & Problem Statement

In asynchronous pipelines (`developer_tools_pipeline.py`) and background webhook worker loops (`FastAPI.BackgroundTasks` -> `DMWorker`), debugging production failures using ad-hoc `print()` statements or unstructured text strings is ineffective.

When Meta Graph API returns an OAuth exception or when a Supabase upload experiences a network timeout:
1. **No Contextual Tracing:** Without a standardized logging hierarchy, logs cannot be filtered by module, timestamp, or severity (`INFO`, `WARNING`, `ERROR`).
2. **Missing Meta Diagnostic Trace IDs:** Meta API failures output unique `x-fb-trace-id` headers. If these trace IDs are not systematically captured and logged in a structured format, escalating API bugs with Meta Developer Support is nearly impossible.
3. **Secret Leakage Vulnerability:** Uncontrolled raw variable dumps (`print(response.content)`) risk accidentally writing sensitive OAuth access tokens (`INSTAGRAM_ACCESS_TOKEN`) or HMAC secrets (`META_APP_SECRET`) to plaintext log files.

---

## 2. Decision

We mandate **Standardized Structured Logging via Python `logging`** across all application modules. Ad-hoc `print()` statements are strictly forbidden outside of basic CLI startup prompts in `main.py`.

### Rules of Structured Logging:
1. **Logger Instantiation:** Every module must instantiate a named logger matching its module hierarchy:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
2. **Standard Log Formatting:** `server.py` ([server.py:L10-L14](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/server.py#L10-L14)) configures the root handler with exact timestamped formatting:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
   )
   ```
3. **Mandatory Trace ID Capture:** `InstagramService._make_request()` ([services/instagram_service.py:L123-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L123-L160)) must extract `response.headers.get("x-fb-trace-id", "N/A")` (`fbtrace_id`) and include it explicitly in every `logger.warning` and `logger.error` statement alongside Graph API code, subcode, and error type.
4. **Credential Sanitization:** Log messages must never output full raw API keys, tokens, or service account strings. When logging URLs or configurations, strings must be truncated (`image_url[:80]...`).

---

## 3. Consequences

### Positive Consequences:
* **Rapid Fault Diagnosis:** Operators can `grep` log streams for specific error codes (`Code: 190`, `Subcode: 2534048`) or module names (`[services.instagram_service]`) to pinpoint exact failure points in seconds.
* **Meta Support Compliance:** Every Graph API error entry provides an immediate `fbtrace_id` string ready for Meta support escalation ticket submission.
* **Security & Cleanliness:** Production logs remain clean, structured, and free of sensitive OAuth secret leakage.

### Negative Consequences / Trade-Offs:
* **Slight Verbosity:** Developers must write structured `logger.info(f"...")` blocks instead of quick `print()` statements during local feature debugging.

---

## 4. Codebase Reference

* **Server Root Logger Config:** [server.py:L10-L14](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/server.py#L10-L14)
* **Graph API Structured Error Logging:** [services/instagram_service.py:L146-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L146-L160)
* **DM Worker Structured Logging:** [features/engagement/worker.py:L35-L68](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L35-L68)

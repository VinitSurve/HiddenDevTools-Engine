# Canonical Technical Debt Registry (`Technical_Debt.md`)

**Document ID:** HDT-FUT-002  
**Category:** Future & Evolution Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Future Roadmap](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Future_Roadmap.md), [Migration to PostgreSQL](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Migration_to_PostgreSQL.md)

---

## 1. Technical Debt Matrix & Refactor Protocol

This document isolates every structural, architectural, and operational technical debt item currently tracked within `HiddenDevTools-Engine`.

| Debt ID | Subsystem | Debt Description & Current Implementation | Severity | Target Resolution Phase | Concrete Refactor Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEBT-01** | **Task Queuing (`server.py`)** | **In-Memory `BackgroundTasks` Vulnerability:** `routers/meta_webhook.py` pushes comment jobs onto Uvicorn's RAM event loop via `background_tasks.add_task()`. If the server crashes or reboots mid-processing, queued jobs in memory are lost prior to SQLite persistence (`save_processed_comment`). | **Medium** | Phase 6 | Transition webhook reception to write `PENDING` records to PostgreSQL immediately within the synchronous webhook request, or offload processing to a dedicated Redis cluster via `BullMQ` / `Celery` (`ADR-009`). |
| **DEBT-02** | **Database Concurrency (`engagement.db`)** | **Single-File Write Bottleneck:** SQLite `BEGIN IMMEDIATE` locks the entire database file during state transitions (`claim_pending_comments`). While optimal for `< 50 req/sec`, concurrent traffic bursts exceeding `200 req/sec` will experience lock contention and query latency. | **Medium** | Phase 6 | Migrate transactional state from embedded SQLite to managed **PostgreSQL 16+** (`ADR-010`), utilizing row-level `SELECT ... FOR UPDATE SKIP LOCKED` semantics. |
| **DEBT-03** | **Canvas Rendering (`engine.py`)** | **Synchronous CPU-Bound Pillow Synthesis:** Synthesizing 9 high-res PNG slides executes synchronously inside `asyncio.to_thread()`. Under high concurrency, heavy Pillow operations can starve Python thread pools. | **Low** | Phase 5 | Offload `DeveloperToolsRenderer` to an isolated microservice (`Render Worker Cluster`) running compiled Go or Rust (`canvas` / `skia-python`) or serverless AWS Lambda / Cloudflare Workers (`NFR-01`). |
| **DEBT-04** | **Configuration Governance (`config.py`)** | **Flat `.env` Singleton Dictionary:** `config.py` loads variables globally via `load_dotenv(override=True)`. While simple, it lacks schema validation or type-checked defaults at application boot. | **Low** | Phase 5 | Replace raw `os.getenv()` lookups with `pydantic-settings` (`BaseSettings`), enforcing strict boot-time validation of required secrets (`META_APP_SECRET`, `INSTAGRAM_ACCESS_TOKEN`). |

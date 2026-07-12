# ADR-006: Feature-Based Domain Module Encapsulation (`features/engagement`)

**Document ID:** HDT-ADR-006  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [Architecture](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/Architecture.md), [Engagement Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/07_Engagement/Engagement.md), [TRD](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/TRD.md)

---

## 1. Context & Problem Statement

In traditional MVC or monolithic backend structures, codebase files are organized strictly by horizontal technical layer across the entire repository: all models inside a global `models/` directory, all background workers inside `workers/`, all database query methods inside `queries/`, and all business validators inside `validators/`.

As complex domain loops evolve—such as the interactive Meta webhook comment processing, keyword normalization, SQLite deduplication claim locking, and direct messaging worker execution—horizontal technical layering scatters domain code across 8+ disparate directories. This causes severe cognitive overload when debugging an engagement race condition, increases cross-module import tangling, and makes it difficult to extract or refactor a self-contained business capability.

---

## 2. Decision

We mandate **Feature-Based Domain Encapsulation** for complex business subsystems. Specifically, the interactive community engagement loop is encapsulated entirely within `features/engagement/`.

### Structure & Rules of `features/engagement/`:
1. **Self-Contained Subsystem:** All domain-specific processors (`comment_processor.py`), queue dispatchers (`dispatcher.py`), keyword matchers (`keyword_matcher.py`), migration runners (`migrations_runner.py`), domain DTOs (`models.py`), database repositories (`repository.py`), message formatters (`template_renderer.py`), and worker executors (`worker.py`) must reside together inside `features/engagement/`.
2. **Minimal External Dependencies:** The `features/engagement/` module may only import external shared constants from `config.py`, shared primitive events from `models/webhook_event.py`, and the network adapter `services/instagram_service.py`. It must never directly import orchestrators (`pipelines/`) or HTTP routing controllers (`routers/`).
3. **Clean Controller Boundary:** HTTP routing controllers (`routers/meta_webhook.py` and `services/meta_webhook_service.py`) interact with the engagement feature solely by passing `WebhookEvent` instances into `CommentProcessor.process_event()`.

---

## 3. Consequences

### Positive Consequences:
* **High Cohesion & Low Coupling:** All code responsible for turning an Instagram comment into a deduplicated direct message exists in one cohesive folder (`features/engagement/`).
* **Easy Subsystem Refactoring:** To upgrade the worker from `QueueDispatcher` (`FastAPI.BackgroundTasks`) to BullMQ / Redis in Phase 6, engineers only modify `features/engagement/dispatcher.py` and `features/engagement/worker.py` without touching any outer server or publishing logic.
* **Streamlined Testing:** The entire engagement subsystem is tested end-to-end inside `tests/test_engagement.py` using simple mock objects (`MockDispatcher`, `MockInstagramService`).

### Negative Consequences / Trade-Offs:
* **Directory Depth:** New developers must understand the distinction between global services (`services/instagram_service.py`) and feature-scoped domain workers (`features/engagement/worker.py`).

---

## 4. Codebase Reference

* **Feature Module Hierarchy:** [features/engagement/](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement)
* **Processor Entry Point:** [features/engagement/comment_processor.py:L18-L66](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/comment_processor.py#L18-L66)
* **Repository Entry Point:** [features/engagement/repository.py:L10-L144](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L10-L144)
* **Worker Entry Point:** [features/engagement/worker.py:L17-L69](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/worker.py#L17-L69)

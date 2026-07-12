# HiddenDevTools — Master Architecture & North Star Blueprint (ADR-0001)

**Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-09  

This document is the canonical reference, Architecture Decision Record (ADR-0001), and operational North Star for **HiddenDevTools**. All future engineering, AI automation, and product decisions must strictly adhere to the boundaries and principles outlined below.

---

## 1. Product Vision vs. Current Deliverable (MVP)

> **Ultimate Platform Vision:** HiddenDevTools is not intended to remain an Instagram automation tool. The ultimate goal is to build a complete developer knowledge platform where AI continuously discovers, evaluates, organizes, and distributes the highest-quality programming resources across multiple social platforms, search APIs, a dedicated website, and automated newsletters.

### Current Product (MVP)
The immediate focus is strictly bound to a closed-loop, automated Instagram engine:
* **Input:** Developer resources (via Content Source Adapters)
* **Output:** High-fidelity 9-slide Instagram carousel
* **Automation Checklist:**
  1. Carousel generation & publishing via Instagram Graph API
  2. Auto-share carousel to Instagram Story
  3. Comment webhook listener (keyword detection)
  4. Automated Keyword DM delivery (deduplicated 1-on-1 messaging per user/post)
  5. Core analytics & insights gathering

---

## 2. Non-Goals (For MVP Scope)

To maintain strict velocity and prevent feature creep, the following are **explicit non-goals** until the MVP is 100% stable:
* ❌ Reels / AI-generated videos
* ❌ Mobile application (iOS/Android)
* ❌ Multi-account / Multi-brand support
* ❌ Multi-language / Internationalization
* ❌ Public-facing web portal / Marketplace
* ❌ User authentication & membership
* ❌ Paid subscriptions & monetization

---

## 3. Project & Architectural Principles

### Core Engineering Principles
1. **Simplicity over cleverness:** Readable, deterministic code always wins over complex abstractions.
2. **Prefer composition over inheritance:** Keep modules flexible and easy to assemble.
3. **Single Responsibility Principle (SRP):** Every module or service handles exactly one domain concern.
4. **Independently Testable:** Every feature and utility must be unit- and integration-testable in isolation without live external API calls.
5. **Separate Business Logic from Infrastructure:** Domain models must not depend on database or API implementation details.
6. **Favor explicit behavior over hidden magic:** Avoid surprising side-effects or implicit state changes.
7. **Optimize for maintainability before optimization:** Write clean, documented code before micro-optimizing performance.

### Core Architectural Principle (Dependency Inversion)
> **Every external dependency must be replaceable without changing business logic.**

GitHub, Google Sheets, Meta Graph APIs, Cloudinary, AI providers, databases, and schedulers must all be accessed via isolated interfaces or adapters.

---

## 4. Domain Boundaries

To prevent cross-domain coupling, code must be separated into strict functional boundaries:

```
├── Content
│   ├── Resources (Repositories, Libraries, Tools)
│   ├── Categories
│   └── Tags / Keywords
├── Generation
│   ├── Carousel (9-Slide Engine)
│   ├── Caption & Hashtags
│   └── Story Assets
├── Publishing
│   ├── Instagram (Graph API Wrapper)
│   └── Future Platforms (X, LinkedIn, Discord)
├── Automation
│   ├── Scheduler (Cron / Time-based triggers)
│   ├── Queue (BullMQ / Background Workers)
│   └── Retry Controllers
├── Engagement
│   ├── Comments (Webhook Processing)
│   ├── DMs (Messaging API & Deduplication)
│   └── Webhooks
├── Analytics
│   ├── Metrics (Reach, Saves, Shares, Engagement)
│   └── Performance Reports
└── AI
    ├── Ranking & Scoring
    ├── Classification & Tagging
    └── Content & Caption Suggestions
```

---

## 5. Rendering Engine Isolation & API Contract

> **Rule:** The rendering engine (`HiddenDevTools-Engine`) should never know where content came from.

It is a dedicated, production-grade image rendering service (`engine.py`). It must **never** directly call GitHub, databases, AI APIs, or external crawlers. It receives structured JSON payloads and outputs rendered image URLs or file paths.

### Renderer API v1 Contract
```json
// POST /render-carousel
// Input Payloads
{
  "title": "Top 7 Open Source Tools for Developers",
  "theme": "dark-blue-accent",
  "branding": {
    "handle": "@hiddendevtools",
    "logo_url": "assets/logo.png"
  },
  "slides": [
    {
      "slide_number": 1,
      "type": "hook",
      "headline": "Supercharge your dev workflow..."
    },
    {
      "slide_number": 2,
      "type": "content",
      "name": "RepoName",
      "url": "github.com/user/repo",
      "description": "High-performance framework...",
      "best_for_1": "Backend Devs",
      "best_for_2": "API Scaling"
    }
  ]
}

// Output Payload
{
  "status": "success",
  "images": [
    "output/post_001_slide_1.png",
    "output/post_001_slide_2.png"
  ]
}
```

---

## 6. Content Source Adapters

Content sources are decoupled adapters implementing a common `ContentSourceAdapter` interface:
* **Current Implementation:** Google Sheets Adapter (`sheet_api.py`)
* **Future Implementations:** PostgreSQL Database Adapter, CMS Adapter, REST API, CSV Ingestion

---

## 7. AI Philosophy & Strict Restrictions

### AI as a Recommendation Engine
* **AI is a recommendation engine, not an authority.** 
* Every AI output must pass deterministic programmatic validation before reaching production.
* **Multi-Factor Ranking:** Resource ranking combines AI Quality Score, GitHub Stars, Forks, Recency, Maintainer Trust, and Developer Trend Velocity.

### AI Strict Restrictions
AI must **never**:
1. ❌ Publish posts directly to production without programmatic validation checks.
2. ❌ Delete existing posts or comments.
3. ❌ Send DMs directly without deduplication and safety verification.
4. ❌ Modify core production database schemas or state.
5. ❌ Rotate or access raw credentials/secrets.
6. ❌ Bypass safety guards or rate-limiting checks.

---

## 8. Observability & Structured Logging

Every critical step across the lifecycle must produce structured logs with correlation tracing (`post_id`, `job_id`, `user_id`):

* `POST_QUEUED` — Draft row or item added to the processing queue.
* `RENDERING_STARTED` / `RENDERING_FINISHED` — Image generation timings and asset checks.
* `PUBLISHING_STARTED` / `PUBLISHING_SUCCEEDED` — Graph API publishing lifecycle.
* `STORY_PUBLISHED` — Story share confirmation.
* `COMMENT_DETECTED` — Webhook comment receipt and keyword match check.
* `DM_SENT` — Deduplicated DM delivery confirmation.
* `RETRY_TRIGGERED` — Exponential backoff event logging.
* `FAILURE_OCCURRED` — Structured exception and stack trace capture.

---

## 9. Security & Secret Management

* **Never commit** `.env` files, `credentials.json`, `token.json`, or Meta access tokens to git.
* **Encrypt long-lived tokens** at rest when stored in database adapters.
* **Programmatic Token Refresh:** Implement automated workers to refresh Meta Business tokens before 60-day expiration windows.
* **Log Sanitization:** Ensure structured logger middleware strips sensitive authorization headers and tokens.

---

## 10. Coding Conventions

* **Variables & Functions:** `camelCase` (TypeScript/JS), `snake_case` (Python)
* **Classes & Types:** `PascalCase` across all languages
* **Folders & Modules:** `kebab-case` (TypeScript/JS), `snake_case` (Python)
* **Environment Variables:** `UPPER_SNAKE_CASE` (e.g., `INSTAGRAM_ACCESS_TOKEN`, `META_APP_ID`)

---

## 11. Definition of Done (DoD)

A feature, module, or bugfix is considered **complete (`[x]`)** only when:
- [x] Code has been peer-reviewed or self-audited for architectural compliance.
- [x] Unit and/or integration tests are added and passing locally.
- [x] Structured logs and correlation tracking are integrated.
- [x] API errors, rate limits, and retries with exponential backoff are handled.
- [x] All secrets and configuration variables are externalized to environment variables.
- [x] Documentation (`README.md`, docstrings) is updated to reflect changes.
- [x] Operation is 100% **idempotent** (safe to retry multiple times without duplicate side effects).

---

## 12. Long-Term Success & Reliability Metrics

* **Publishing Reliability:** $> 99.5\%$ automated publish success rate across 30 days.
* **Deduplication Accuracy:** Exactly **Zero ($0$)** duplicate DMs delivered to any user on a single post.
* **Pipeline Velocity:** Mean time from `DRAFT_READY` to `PUBLISHED_STORY` $< 2\text{ minutes}$.
* **Transient Recovery:** $100\%$ automated self-healing recovery from transient Instagram Graph API rate-limit (`429`) or server (`5xx`) errors.
* **Zero Human Intervention:** End-to-end execution of the daily 9-slide carousel without manual trigger scripts.

---

## 13. Immediate Execution Roadmap

To maintain strict velocity, no new target backend migrations or crawlers will commence until the MVP pipeline is verified:

1. **Phase 1: Authentication Stability** — Verify and stabilize Instagram Business Login token exchange (`oauth_client.json`, `instagram_service.py`).
2. **Phase 2: Carousel Publishing** — Publish a single 9-slide carousel to the Instagram Business Account via Graph API.
3. **Phase 3: Story Automation** — Automatically publish/share the carousel to the Instagram Story immediately after grid publication.
4. **Phase 4: Webhook Integration** — Configure and test live Instagram Comments API webhooks (`COL_KEYWORD` matching).
5. **Phase 5: Deduplicated DM Delivery** — Implement and verify the 1-on-1 keyword-triggered DM response.

# ADR-005: Meta Graph API v23.0 for Carousel & Messaging Orchestration

**Document ID:** HDT-ADR-005  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [Instagram Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/06_Instagram/Instagram.md), [API Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/09_APIs/API.md), [Failures Analysis](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/reports/Failures.md)

---

## 1. Context & Problem Statement

Publishing multi-image carousels (`2-10 slides`) and sending automated 1-on-1 direct messages on Instagram can theoretically be attempted via third-party scraping libraries (`instagrapi`, Selenium mobile browser automation, or private API wrappers).

However, utilizing unofficial scraping libraries or reverse-engineered private mobile APIs introduces fatal business and operational risks:
1. **Immediate Account Ban / Shadowban:** Meta actively detects non-official API signatures, IP spoofing, and headless browser fingerprints, resulting in permanent brand account termination.
2. **Brittle Execution:** Private APIs change schemas without warning upon every iOS/Android app update, breaking automated cron publishers overnight.
3. **No Webhook Capability:** Unofficial libraries cannot receive real-time server-to-server comment notifications (`webhooks`), forcing heavy, rate-limited polling loops to discover new comments.

---

## 2. Decision

We standardize exclusively on the **Official Meta Graph API v23.0** (`https://graph.facebook.com/v23.0`) (`services/instagram_service.py`) for all publishing and messaging interactions.

### Rules of Graph API Integration:
1. **Carousel Publishing 3-Stage Orchestration:** `publish_carousel()` must execute the exact Meta asynchronous specification:
   * **Stage 1:** `POST /{ig_user_id}/media` (`image_url=URL`, `is_carousel_item=true`) for all 9 slides.
   * **Stage 2:** Poll `wait_for_container(container_id)` (`GET /{container_id}?fields=status_code`) until every slide reports `FINISHED`.
   * **Stage 3:** `POST /{ig_user_id}/media` (`media_type=CAROUSEL`, `children=id1,id2...`), poll until `FINISHED`, then `POST /{ig_user_id}/media_publish`.
2. **Direct Messaging API:** `send_message()` must invoke `POST /{page_id}/messages` (or `/me/messages`) passing JSON payloads (`{"recipient": {"id": "..."}, "message": {"text": "..."}}`).
3. **Defensive Exponential Backoff:** All API calls must pass through `_make_request()`, intercepting transient error codes (`4, 17, 32, 613`) and sleeping `2^attempt` seconds prior to retrying.

---

## 3. Consequences

### Positive Consequences:
* **Total Brand Security & Compliance:** Zero risk of account suspension for using scraping bots. All actions are cryptographically authenticated via official Facebook Page / Instagram Business Access Tokens (`INSTAGRAM_ACCESS_TOKEN`).
* **Real-Time Webhook Reception:** Meta pushes instant `< 200ms` HTTPS POST payloads directly to our `/webhooks/meta` endpoint when comments occur.
* **Traceable Escalation:** Every Graph API response includes an `x-fb-trace-id` header (`fbtrace_id`), which `InstagramService` logs explicitly on errors (`_make_request:L124-L160`), enabling rapid bug escalation with Meta developer support.

### Negative Consequences / Trade-Offs:
* **App Review Barrier (`Code 200 / Subcode 2534048`):** In Standard Access (Development Mode), Meta strictly prevents the bot from sending DMs to public commenters unless the recipient account is manually registered as an App Tester in the Meta Developer Dashboard. Public deployment requires passing official Meta App Review (`instagram_manage_messages`).

---

## 4. Codebase Reference

* **Service Initialization:** [services/instagram_service.py:L50-L75](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L50-L75)
* **Exponential Backoff Helper (`_make_request`):** [services/instagram_service.py:L80-L200](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L80-L200)
* **Direct Message Dispatcher (`send_message`):** [services/instagram_service.py:L205-L267](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L205-L267)
* **Carousel Orchestrator (`publish_carousel`):** [services/instagram_service.py:L604-L779](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L604-L779)

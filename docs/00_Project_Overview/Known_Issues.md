# Known Operational Issues & Workarounds

**Document ID:** HDT-EXEC-012  
**Category:** Project Overview  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Technical Debt Report](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Technical_Debt_Report.md), [Failures Analysis](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/reports/Failures.md)

---

## 1. Active Operational Issues Log

The following table documents active or recently resolved operational quirks, external API gotchas, and specific behaviors requiring developer awareness when operating the HiddenDevTools platform.

| Issue ID | Affected Subsystem | Symptom / Error Message | Root Cause | Workaround / Operational Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **KI-01** | **Meta Webhooks & Messaging API** | `Graph API Error [POST .../messages] Code: 200, Subcode: 2534048: App does not have Advanced Access to instagram_manage_messages permission...` | Meta restricts `Standard Access` apps in Development Mode to sending DMs only to registered App Testers/Developers/Admins. | **Immediate Workaround:** Add target Instagram user accounts to the Meta App Dashboard under **App roles -> Roles -> Instagram Testers** and accept the invitation in Instagram mobile settings (`Settings -> Creator Tools -> App Testers`). **Long-Term Fix:** Submit App Review for `instagram_manage_messages` Advanced Access. | `Active / By Design` |
| **KI-02** | **FastAPI Reloader & `.env` Sync** | `.env` changes are not reflected in running app; Graph API returns `OAuthException Code 190 / Subcode 463 (Session has expired)` even after editing `.env`. | `load_dotenv()` by default does not overwrite environment variables already loaded in `os.environ` by the master `uvicorn` parent process. | **Resolution Implemented:** `config.py` has been updated to `load_dotenv(override=True)`. However, if the master process has been running for hours prior to the fix, perform a **hard terminal restart (`Ctrl+C` -> `python server.py`)**. | `[x] Resolved` |
| **KI-03** | **Instagram Graph API Publication Polling** | `wait_for_container()` reports `ERROR` or times out after 120 seconds during high Meta server load. | Meta Graph API video or multi-image carousel container processing experiences transient backend delays or internal processing queues during peak UTC hours. | **Operational Resolution:** The pipeline exits safely without creating a grid post. The user may re-run the pipeline after 5 minutes; `developer_tools_pipeline.py` ensures idempotency. | `Mitigated via Polling` |
| **KI-04** | **Google Sheets Rate Limiting (Quota Exceeded)** | `gspread.exceptions.APIError: [429] Quota exceeded for quota metric 'Read requests' and limit 'Read requests per minute per user'`. | Executing rapid, continuous end-to-end integration tests that repeatedly open worksheets and fetch all records within a short window. | **Operational Resolution:** Ensure at least 2-second sleep delays between automated test runs. `SheetService` groups row status updates to minimize API round-trips. | `Mitigated` |

---

## 2. Environment Verification Runbook

When setting up a new development station or troubleshooting a `Code 190` OAuth error, execute this quick verification checklist:
1. Verify `INSTAGRAM_ACCESS_TOKEN` is valid using curl:
   ```powershell
   curl -X GET "https://graph.facebook.com/v23.0/me?fields=id,name&access_token=YOUR_TOKEN"
   ```
2. Verify `cloudflared` tunnel is forwarding traffic to local port `8000`:
   ```powershell
   curl -i http://localhost:8000/webhooks/meta?hub.mode=subscribe&hub.verify_token=META_VERIFY_TOKEN&hub.challenge=12345
   ```
   *Expected Response:* HTTP `200 OK` with body `12345`.

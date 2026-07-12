# Production Operations, Monitoring & Incident Response Runbooks (`Operations.md`)

**Document ID:** HDT-OPS-001  
**Category:** Operations Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Deployment](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/12_Deployment/Deployment.md), [Known Issues](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/00_Project_Overview/Known_Issues.md), [Failures Analysis](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/reports/Failures.md), [Security Audit](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/10_Security/Security.md)

---

## 1. Production Monitoring & Observability Dashboard

Operating `HiddenDevTools-Engine` requires continuous monitoring of three critical telemetry signals: **Server Log Output (`server.log`)**, **SQLite Deduplication Queue State (`engagement.db`)**, and **Google Sheets Status Transitions (`Status` column)**.

### 1.1 Real-Time Log Monitoring (PowerShell)
To monitor active webhook reception and Direct Message worker sweeps (`worker.py`) across local terminal logs:
```powershell
Get-Content -Path "e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\server.log" -Wait -Tail 50 | Select-String -Pattern "ERROR|WARNING|COMMENT_RECEIVED|DM_ALREADY_QUEUED"
```

### 1.2 SQLite Queue Inspection Commands
To inspect active pending, processing, or retrying jobs directly from `engagement.db`:
```powershell
# View breakdown of comments across all 5 DMStatus lifecycle states
sqlite3 e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db "SELECT status, COUNT(*) FROM processed_comments GROUP BY status;"

# View comments currently stuck in RETRYING status with their scheduled backoff times
sqlite3 e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db "SELECT comment_id, username, attempt_count, last_error, next_retry_at FROM processed_comments WHERE status = 'RETRYING';"
```

---

## 2. Standardized Incident Response Runbooks

When system monitoring triggers an alert or when automated DMs fail to deliver, operators must execute the following step-by-step resolution runbooks immediately.

---

### Runbook 1: Meta Graph API Access Token Expiration (`OAuthException Code 190 / Subcode 463`)
* **Symptom:** Carousel publishing (`main.py`) or DM dispatch (`worker.py`) throws `Graph API Error Code: 190, Subcode: 463, Type: OAuthException, Message: Error validating access token: Session has expired`.
* **Root Cause:** The 60-day Meta Business Access Token (`INSTAGRAM_ACCESS_TOKEN`) reached its natural TTL.
* **Resolution Step-by-Step:**
  1. Open a web browser and navigate to the [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/).
  2. Select your Meta App (`HiddenDevTools`) and User/Page -> **Get User Token**. Ensure permissions `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, and `instagram_manage_messages` are checked. Click **Generate Access Token**.
  3. Exchange the short-lived token for a 60-day long-lived token using the Meta Access Token Debugger or Graph API exchange endpoint:
     ```powershell
     curl -X GET "https://graph.facebook.com/v23.0/oauth/access_token?grant_type=fb_exchange_token&client_id=META_APP_ID&client_secret=META_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
     ```
  4. Copy the long-lived token string (`EAA...`) and update `e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\.env`:
     ```ini
     INSTAGRAM_ACCESS_TOKEN="EAA_YOUR_NEW_LONG_LIVED_TOKEN_HERE"
     ```
  5. **CRITICAL RESTART STEP:** Stop the running Uvicorn server (`Ctrl+C`) and perform a **hard terminal restart**:
     ```powershell
     python server.py
     ```
     *(Note: `config.py` uses `load_dotenv(override=True)`, ensuring the restarted master process immediately loads the fresh `.env` token).*

---

### Runbook 2: Direct Messages Blocked for Non-Testers (`Code 200 / Subcode 2534048`)
* **Symptom:** Public users comment `DEV` on a post, but logs show `worker.py` throwing `Graph API Error Code: 200, Subcode: 2534048: (#200) App does not have Advanced Access to instagram_manage_messages permission`.
* **Root Cause:** The system is operating in **Standard Access** (Development Mode). Meta strictly prevents bots from sending DMs to public accounts unless they are explicitly registered and verified as App Testers.
* **Immediate Workaround (Adding Testers):**
  1. Go to Meta Developer Dashboard -> **App Roles -> Roles -> Instagram Testers**.
  2. Click **Add Instagram Testers** and enter the target Instagram username (for example, `vinit.surve.pvt`).
  3. Open the Instagram mobile app on the tester's phone -> **Settings -> Creator Tools -> App Testers**.
  4. Tap **Accept Invitation**. Once accepted, `send_message()` will succeed immediately for that user.
* **Permanent Resolution (Submitting App Review):**
  1. Record a 2-minute MP4 screen recording demonstrating the user flow: (a) User (`@vinit.surve.pvt`) comments `DEV` on `@hiddendevtools` post, (b) Webhook arrives at server (`200 OK`), (c) DM is delivered instantly to the user's inbox containing the exact GitHub URL.
  2. Navigate to Meta Developer Dashboard -> **App Review -> Requests -> Request Advanced Access for `instagram_manage_messages`**.
  3. Upload the video screencast and enter the compliance justification: *"HiddenDevTools uses automated direct messaging to deliver requested open-source developer tool documentation and GitHub repository URLs to software engineers who explicitly comment 'DEV' on our educational Instagram carousels."*

---

### Runbook 3: Supabase Storage CDN Reachability Failure (`verify_url` raises Exception)
* **Symptom:** `developer_tools_pipeline.py` aborts during Stage 3 (`verify_url()`), throwing `RuntimeError: CDN verification failed for URL https://.../storage/v1/object/public/posts/... after maximum retries`.
* **Root Cause:** Cloudflare CDN edge propagation delays across Supabase storage nodes, or `SUPABASE_SERVICE_ROLE_KEY` permission revocation.
* **Resolution Step-by-Step:**
  1. Test image URL accessibility manually via curl:
     ```powershell
     curl -i "https://xxxx.supabase.co/storage/v1/object/public/posts/YYYY/MM/DD/GenID/01_Cover.png"
     ```
  2. If curl returns `404 Not Found`, log into the [Supabase Dashboard](https://supabase.com/dashboard) -> **Storage -> `posts` Bucket -> Policies**. Verify the bucket policy **`Public Access`** is enabled (`SELECT` policy for `anon` role).
  3. If policy is valid, re-run `python main.py`. `developer_tools_pipeline.py` guarantees idempotency and will safely re-attempt uploading any missing slide assets without duplicating completed grid posts.

---

## 3. Database Maintenance, Backup & Pruning Runbook

Over months of continuous comment processing, `engagement.db` accumulates thousands of `SENT` and `FAILED` historical records. To maintain sub-millisecond query performance (`claim_pending_comments`), execute the weekly maintenance runbook:

```powershell
# 1. Create timestamped hot backup snapshot of engagement.db
Copy-Item "e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db" -Destination "e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement_backup_$(Get-Date -Format 'yyyyMMdd').db"

# 2. Prune processed records older than 90 days (retaining PENDING and RETRYING rows)
sqlite3 e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db "DELETE FROM processed_comments WHERE status IN ('SENT', 'FAILED') AND created_at <= datetime('now', '-90 days');"

# 3. Rebuild internal B-Trees and reclaim freed disk blocks (`VACUUM`)
sqlite3 e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db "VACUUM;"
```

# Platform Security, Credential Isolation & Cryptographic Verification (`Security.md`)

**Document ID:** HDT-SEC-001  
**Category:** Security Specifications  
**Version:** 1.0  
**Status:** Canonical Engineering Baseline  
**Cross-References:** [Risk Register](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/10_Security/Risk_Register.md), [ADR-007](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-007_Structured_Logging.md), [Configuration](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/03_Backend/Configuration.md)

---

## 1. Executive Security Baseline

HiddenDevTools (`@hiddendevtools`) interacts with sensitive third-party APIs across Google Workspace (`service_account.json`), Supabase Cloud Storage (`SUPABASE_SERVICE_ROLE_KEY`), and Meta Business Manager (`INSTAGRAM_ACCESS_TOKEN`). A breach of any single credential could allow unauthorized publishing to corporate social accounts, data deletion across storage buckets, or unauthorized manipulation of editorial spreadsheets.

To mitigate credential theft and injection attacks, the system enforces four foundational security pillars: **Environment Credential Isolation (`.env`)**, **Cryptographic HMAC-SHA256 Webhook Verification**, **Strict Log Sanitization**, and **Meta App Review Compliance Gateways**.

---

## 2. Credential Isolation & `.env` Governance

### 2.1 Secrets Storage Boundary (`load_dotenv override=True`)
* **Mandate:** Secrets (`META_APP_SECRET`, `INSTAGRAM_ACCESS_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`) shall **NEVER** be hardcoded in Python `.py` source files or committed to git tracking.
* **Mechanism:** All secrets must be loaded dynamically from a local `.env` file via `config.py` ([config.py:L1-L2](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/config.py#L1-L2)) using `load_dotenv(override=True)`.
* **Exclusion Enforcement:** `.gitignore` explicitly lists `.env`, `*.db`, `service_account.json`, `output/`, and `fixtures/webhooks/` to prevent accidental credential upload to GitHub.

### 2.2 Google Service Account Isolation
* **Principle of Least Privilege:** The Google Service Account (`service_account.json`) granted access to `SPREADSHEET_ID` and `DRIVE_FOLDER_ID` must possess **only** Google Sheets and Google Drive API scopes (`https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/drive.file`). It must never be granted domain-wide Google Workspace admin privileges or Gmail access.

---

## 3. Cryptographic Webhook HMAC Signature Verification (`X-Hub-Signature-256`)

When an incoming HTTP POST arrives at `/webhooks/meta`, the server must verify that the request originated from legitimate Meta Graph API servers rather than a malicious actor attempting to inject fake comment payloads or trigger unauthorized Direct Messages (`US-501`).

### Cryptographic Validation Protocol
1. **Signature Header Extraction:** `routers/meta_webhook.py` extracts the `X-Hub-Signature-256` header (`sha256=a1b2c3...`) and reads raw request body bytes (`raw_body = await request.body()`).
2. **HMAC Computation:** `MetaWebhookService.validate_signature(raw_body, signature_header)` ([services/meta_webhook_service.py:L40-L63](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/meta_webhook_service.py#L40-L63)) computes the expected SHA-256 HMAC:
   ```python
   expected_signature = "sha256=" + hmac.new(
       config.META_APP_SECRET.encode("utf-8"),
       raw_body,
       hashlib.sha256
   ).hexdigest()
   ```
3. **Timing-Attack Immune Comparison:** The method executes `hmac.compare_digest(expected_signature, signature_header)`. Utilizing `compare_digest()` rather than standard string equality (`==`) prevents side-channel timing attacks where an attacker infers characters based on string comparison execution duration.
4. **Development Bypass Rule:** If `config.is_development() == True` (`ENV="development"`), signature verification returns `True` to allow local testing with mock payloads (`curl`). **Production environments (`ENV="production"`) must never disable HMAC verification.**

---

## 4. Log Sanitization & Trace Auditing (`ADR-007`)

If raw HTTP responses from Graph API or Supabase Storage are printed unmasked (`print(response.json())`), sensitive access tokens (`INSTAGRAM_ACCESS_TOKEN`) embedded in query parameters could leak into plaintext log files (`server.log`).

### Rules of Log Sanitization:
1. **Never Log Full URLs with Tokens:** When `InstagramService._make_request()` logs errors or retries ([services/instagram_service.py:L123-L160](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/services/instagram_service.py#L123-L160)), it logs only `method`, `endpoint`, and sanitized diagnostic strings (`Code: {code}, Subcode: {subcode}, Type: {error_type}`). It never logs the `params={"access_token": ...}` dictionary.
2. **Mandatory Trace ID (`fbtrace_id`) Capture:** Every Graph API error entry must capture and log `x-fb-trace-id` alongside correlation IDs (`[{correlation_id}] Graph API Error Code {code}... [fbtrace_id={trace_id}]`). This ensures exact auditability when investigating rate limits or permission drops without exposing token strings.

---

## 5. Meta App Review & Access Token Security Gateways

### 5.1 Long-Lived Token Expiration & Rotation (`Code 190`)
Meta Business Access Tokens issued via Graph API Explorer expire after 60 days. When an expired token is encountered:
* `InstagramService` catches `Code 190 / Subcode 463` and logs a critical error indicating exact expiration timestamps.
* **Security Protocol:** To rotate an access token, an authorized administrator must generate a new token via Meta Developer Dashboard, update `.env` (`INSTAGRAM_ACCESS_TOKEN=YOUR_NEW_TOKEN`), and perform a **hard terminal restart (`Ctrl+C` -> `python server.py`)** to force `load_dotenv(override=True)` across Uvicorn parent and child worker processes.

### 5.2 Direct Messaging Permission Boundary (`Code 200 / Subcode 2534048`)
While in **Standard Access** (Development Mode), the app is restricted to sending direct messages solely to verified App Testers.
* **Security Safeguard:** Attempting to send a DM to a public user returns `(#200) App does not have Advanced Access to instagram_manage_messages permission`. The system handles this gracefully by transitioning the comment record directly to `FAILED` without crashing or spamming Meta servers with retries.

# Operations Runbook

## Overview
This runbook covers common failure modes and recovery procedures for the HiddenDevTools Publishing Engine.

## 1. Startup Validation Failures
**Symptom**: Pipeline aborts instantly with `StartupValidationError`.
**Action**:
- Check the error log carefully.
- If missing templates, ensure `assets/` and `assets/fonts/` exist and are accessible.
- If missing directories, ensure the process has write permissions to `./output`.
- If missing configuration, check `.env` or injected CI/CD secrets for Supabase, Instagram, and Sheets.

## 2. Instagram Token Expiration
**Symptom**: `PublishResult` fails with an OAuth Exception.
**Action**:
- The Meta Graph API token might be expired.
- Regenerate a new Long-Lived Access Token via the Meta App Dashboard.
- Update the `INSTAGRAM_ACCESS_TOKEN` secret in the deployment environment.

## 3. Rate Limits & Quotas
**Symptom**: API errors indicating 429 Too Many Requests from Supabase, Meta, or Google.
**Action**:
- The pipeline inherently limits generations to 1 per day per niche.
- Ensure you haven't triggered a large manual replay loop.
- The `ReconciliationWorker` uses exponential backoff and SQLite persistence to survive transient errors without requiring manual intervention. Let it retry on the next execution.

## 4. Unreconciled / Interrupted Publications
**Symptom**: A publication succeeded on Instagram, but Google Sheets was never updated (Status remains "Generating" or "Draft" in the sheet, but the post is live).
**Action**:
- The `ReconciliationWorker` (invoked on the next pipeline startup) will detect the drift.
- It will find the completed record in the local `published_generations` SQLite database and automatically push the state to Google Sheets. No manual intervention required.

## 5. Blank/Corrupt Rendered Outputs
**Symptom**: Pipeline aborts at the `RENDERED` stage.
**Action**:
- Investigate the logs for Pillow exceptions.
- Usually caused by dynamic content text overflowing or containing undisplayable glyphs.
- `CapabilityValidator` rejects corrupt outputs before uploading. Correct the source text in the Google Sheet and allow the scheduler to retry.

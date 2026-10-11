# Production Secret Parity Audit Report (Phase 7.6)

This document contains the findings of the Local ↔ GitHub Actions production secret parity audit. 

**IMPORTANT: Do not enable the automatic publishing workflow (`publish.yml`) or scheduled cron jobs until the hard blockers identified below are resolved.**

## 1. Configuration Contract (`app_config.py`)

The application consumes the following environment variables natively:

| Environment Variable | Required/Optional | Consumed By |
| --- | --- | --- |
| `INSTAGRAM_ACCESS_TOKEN` | Required | `InstagramService` |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Required | `InstagramService` |
| `META_APP_SECRET` | Required | `InstagramService` (API calls) |
| `FACEBOOK_PAGE_ID` | Required | `InstagramService` |
| `META_VERIFY_TOKEN` | Optional | Webhooks |
| `META_APP_ID` | Optional | Webhooks/Config |
| `SUPABASE_URL` | Required | `StorageService` |
| `SUPABASE_SERVICE_ROLE_KEY` | Required | `StorageService` |
| `SERVICE_ACCOUNT_FILE` | Required | Google Sheets / Drive API (defaults to `service_account.json`, populated by GH secret) |
| `SPREADSHEET_ID` | Required | `sheet_api.py` (has default, but needs actual sheet) |

## 2. CI/CD Workflow Audit (Mismatches Identified)

The current `.github/workflows/cd.yml` and `.github/workflows/ci.yml` define older or incorrect environment variable names that **do not match** `config/app_config.py`.

* **`INSTAGRAM_ACCOUNT_ID`** in YAML vs. **`INSTAGRAM_BUSINESS_ACCOUNT_ID`** in code.
* **`SUPABASE_KEY`** in YAML vs. **`SUPABASE_SERVICE_ROLE_KEY`** in code.
* **`META_WEBHOOK_VERIFY_TOKEN`** in YAML vs. **`META_VERIFY_TOKEN`** in code.
* **`FACEBOOK_PAGE_ID`** is missing from the YAML files entirely.
* **`META_APP_SECRET`** is missing from the YAML files entirely.

## 3. Secret Parity Status

We verified the local fingerprints and have prepared a workflow (`.github/workflows/secret_audit.yml`) to verify them inside GitHub Actions securely.

| Configuration | Local | GitHub (`production` env) | Parity Status |
|---|---|---|---|
| Instagram Token | Present | Unverified | UNVERIFIED (Requires manual secret creation) |
| Instagram Account ID | Present | Unverified | UNVERIFIED |
| Facebook Page ID | Present | Unverified | UNVERIFIED |
| Meta App Secret | Present | Unverified | UNVERIFIED |
| Supabase URL | Present | Unverified | UNVERIFIED |
| Supabase Key | Present | Unverified | UNVERIFIED |
| Spreadsheet ID | Present (default) | Unverified | UNVERIFIED |
| Google Service Account | Present | Unverified | UNVERIFIED |

*Note: Parity is currently UNVERIFIED because we must run the `.github/workflows/secret_audit.yml` action manually after injecting the `AUDIT_EXPECTED_*` temporary secrets into the GitHub repository.*

## 4. HARD BLOCKER: SQLite Durability

**Status:** 🚨 **CRITICAL VULNERABILITY DETECTED**

We audited the pipeline's dependency on SQLite (`publishing.db`). 
* `services/completion_service.py` records successful Instagram publications into SQLite.
* `scheduler/state_manager.py` uses SQLite to reconcile state (e.g. knowing if a job was already published).
* `migrations_runner.py` builds the database schema.

**The Problem:** GitHub-hosted runners are ephemeral. A fresh VM is spun up for every workflow run. When `cd.yml` or `publish.yml` runs, it will create a brand new, empty `publishing.db`. Any rows written to `published_generations` or `upload_attempts` will be permanently lost as soon as the workflow finishes. 

**Impact:** On the next run, the SQLite database will be empty again. The pipeline will have no local memory of what it previously published, which destroys the deduplication, reconciliation, and idempotency guarantees built into the engine.

**Resolution Required:** Before enabling scheduled publishing, we must implement a persistence layer for SQLite in GitHub Actions (e.g., using `actions/cache` or storing the `.db` file in an external bucket), or migrate the tracking logic to Supabase PostgreSQL, which is already configured.

## 5. Next Steps

1. Review this report.
2. Decide how to solve the SQLite durability blocker (e.g., migrate to Supabase Postgres).
3. Fix the mismatched environment variables in `cd.yml` and `ci.yml`.
4. Inject the `AUDIT_EXPECTED_*` temporary secrets into GitHub and run the `Secret Parity Audit` workflow to complete identity verification.
5. Do NOT proceed to automatic publishing until the SQLite issue is resolved.

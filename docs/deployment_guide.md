# Deployment Guide

This guide covers deploying the HiddenDevTools Engine, configuring environment variables, and validating the deployment.

## Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

## Environment Variables
The application strictly reads all environment variables via `AppConfig`. You must supply these at runtime or via `.env`:
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_ACCOUNT_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SPREADSHEET_ID`
- `META_WEBHOOK_VERIFY_TOKEN`
- `DRY_RUN` (Optional: "True" or "False")

## Local Execution
1. Install dependencies: `pip install -r requirements.txt`
2. Run validation only: `python scheduler/scheduler.py --validate-only`
3. Run Healthcheck: `python scheduler/healthcheck.py`
4. Dry Run Publish: `python scheduler/scheduler.py --run-today` with `DRY_RUN=True`

## Production Deployment
The CD pipeline (`.github/workflows/cd.yml`) automates deployments upon merging to `main` or pushing a `v*` tag.
1. It validates migrations via `startup_validator.py`.
2. It asserts connectivity via `healthcheck.py`.
3. It validates logical correctness via a Dry Run.
4. It performs a deployment.
5. It runs a post-deployment Health Check.

Ensure that the target environment (e.g. EC2, ECS, Heroku, Render) provides writable access to `./output` and `./manifests` (or configure these paths accordingly via `AppConfig` if changed in the future).

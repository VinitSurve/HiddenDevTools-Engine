# CHANGELOG

## [1.0.0] - 2026-07-18

### Added
- **Core Engine Freeze**: Reached production readiness and architectural stability. Tagging v1.0.0.
- **Manifest Generation**: Canonical JSON record of intended publications.
- **CI/CD Pipelines**: `ci.yml` and `cd.yml` for rigorous testing, mocked health checks, and DRY_RUN validation before deployment.
- **Structured Observability**: Centralized JSON logging with `PipelineContext` tracking `generation_id`, `batch_id`, and `niche`.
- **Reconciliation Worker**: SQLite state machine to recover interrupted sheet updates or unverified publications.
- **Startup Validation**: Prevents execution if storage, rendering assets, or database migrations are unavailable.
- **Health Checks**: CLI endpoint for latency and dependency verification.
- **Immutable Configuration**: `AppConfig` providing distinct Service, Runtime, and Feature flag structures separated from static `settings.py`.

### Changed
- `settings.py` restricted entirely to static layout/rendering constants; all secrets and environment variables migrated to `AppConfig`.
- Engine architecture separated cleanly into Orchestration, Rendering, Storage, Publishing, and Completion layers.

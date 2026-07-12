# ADR-010: Database Schema Evolution & Forward-Compatible Migration Strategy

**Document ID:** HDT-ADR-010  
**Status:** Accepted  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-003 SQLite First](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-003_SQLite_First.md), [Database Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/08_Database/Database.md), [Migration to PostgreSQL](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/15_Future/Migration_to_PostgreSQL.md)

---

## 1. Context & Problem Statement

As feature requirements expand, the underlying schema of `engagement.db` (`processed_comments` table) evolves. For example, migrating from initial Phase 4 state tracking (`001_initial.sql`) to Phase 4C retry backoff mechanics (`002_phase_4c_upgrade.sql`) required adding four columns (`attempt_count`, `last_attempt_at`, `last_error`, `next_retry_at`) and renaming text columns (`normalized_text`, `original_text`).

Because SQLite has restrictive `ALTER TABLE` support (for example, dropping columns, renaming constraints, or modifying ENUM check constraints is unsupported without rebuilding the table), running manual migrations on live production instances risks database corruption or data loss. Furthermore, as the platform prepares for its future transition to PostgreSQL (`ADR-003`), schema migrations must be written sequentially and executed automatically on startup.

---

## 2. Decision

We establish an **Automated, Sequential SQL Script Migration Engine** (`MigrationsRunner` inside `features/engagement/migrations_runner.py`).

### Rules of Schema Evolution & Migrations:
1. **Sequential Script Directory:** All database changes must be authored as immutable SQL files numbered sequentially inside `migrations/` (`001_initial.sql`, `002_phase_4c_upgrade.sql`). Once committed, an existing migration file may never be modified.
2. **Schema Tracking Table:** `MigrationsRunner` shall automatically create a system table `schema_migrations (version TEXT PRIMARY KEY, applied_at DATETIME)` upon initialization ([migrations_runner.py:L26-L32](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/migrations_runner.py#L26-L32)).
3. **Automatic Startup Application:** When `DeduplicationRepository` initializes (`repository.py:L13-L14`), `MigrationsRunner.run()` compares the list of `.sql` files in `migrations/` against rows inside `schema_migrations`. Unapplied scripts are executed inside an atomic transaction (`conn.execute("BEGIN TRANSACTION")`) and recorded immediately.
4. **Table Rebuild Strategy for SQLite:** When SQLite `ALTER TABLE` limitations prevent simple DDL, migrations shall follow the **Table Rebuild Pattern**:
   * Create new table with updated schema (`CREATE TABLE processed_comments_new ...`).
   * Copy data (`INSERT INTO processed_comments_new SELECT ... FROM processed_comments`).
   * Drop old table (`DROP TABLE processed_comments`) and rename (`ALTER TABLE processed_comments_new RENAME TO processed_comments`).

---

## 3. Consequences

### Positive Consequences:
* **Zero-Touch Deployments:** Restarting the `server.py` application automatically upgrades the local SQLite database schema without requiring manual DBA scripts or external CLI tools (`alembic`).
* **Complete Audit Trail:** `schema_migrations` provides an exact history (`version`, `applied_at`) of when every schema change occurred on that specific server instance.
* **Forward Compatibility with PostgreSQL:** When transitioning to PostgreSQL (`003_pg_engagement.sql`), the exact same sequential file structure (`migrations/*.sql`) maps directly into standard PostgreSQL migration runners (`Flyway` / `Alembic` / `pgmigrate`).

### Negative Consequences / Trade-Offs:
* **Table Rebuild Locks:** If `processed_comments` grows to >500,000 rows in SQLite, a table rebuild migration (`DROP / RENAME`) could lock the database (`SQLITE_BUSY`) for several seconds during startup.

---

## 4. Codebase Reference

* **Migrations Runner Class:** [features/engagement/migrations_runner.py:L15-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/migrations_runner.py#L15-L53)
* **Initial Schema Script:** [migrations/001_initial.sql:L1-L11](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/migrations/001_initial.sql#L1-L11)
* **Phase 4C Upgrade Script:** [migrations/002_phase_4c_upgrade.sql:L1-L19](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/migrations/002_phase_4c_upgrade.sql#L1-L19)

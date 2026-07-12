# ADR-003: SQLite-First Embedded Database Architecture

**Document ID:** HDT-ADR-003  
**Status:** Accepted (With Planned PostgreSQL Migration)  
**Date:** 2026-07-09  
**Decision-Makers:** Lead Software Architect, Core Backend Engineering Team  
**Cross-References:** [ADR-002 Repository Pattern](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-002_Repository_Pattern.md), [ADR-010 Migration Strategy](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-010_Migration_Strategy.md), [Database Specifications](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/08_Database/Database.md)

---

## 1. Context & Problem Statement

For Phase 1 through Phase 5 (MVP and single-node production deployment), the platform requires a transactional storage engine to deduplicate incoming webhooks (`processed_comments` table) and manage background retry queues.

Evaluating full-blown relational database servers (such as managed AWS RDS PostgreSQL or Dockerized MySQL) introduced unnecessary operational friction for single-node compute environments (`uvicorn server:app`). Requiring external DB connection strings, VPC configurations, and persistent TCP connection pools would complicate local developer onboarding and increase MVP operational costs.

---

## 2. Decision

We mandate an **SQLite-First Embedded Architecture** for all local and single-server production state tracking (`engagement.db`).

### Architectural Rules:
1. **Embedded File Location:** The database file resides locally at `e:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\engagement.db` (`SQLITE_DB_PATH`).
2. **Automated Schema Migrations:** On initialization, `DeduplicationRepository.__init__()` invokes `MigrationsRunner(self.db_path).run()`, sequentially applying SQL scripts (`migrations/001_initial.sql`, `migrations/002_phase_4c_upgrade.sql`).
3. **Write-Lock Concurrency (`BEGIN IMMEDIATE`):** All multi-step read-then-write claim operations (`claim_pending_comments`) must execute an explicit `BEGIN IMMEDIATE` statement immediately upon opening the cursor to acquire a reserved write lock and eliminate race-condition deadlocks.

---

## 3. Consequences

### Positive Consequences:
* **Zero Operational Overhead:** No database servers to provision, monitor, or pay for. The database is a single disk file (`engagement.db`) backed up easily via filesystem snapshots.
* **ACID Transactional Integrity:** SQLite enforces strict ACID guarantees, atomic rollbacks, and exact primary key uniqueness (`comment_id`).
* **Sub-Millisecond Query Execution:** Because the database resides on the local block device in the exact same memory space as the Python process, query latencies average `< 0.5ms`.

### Negative Consequences / Trade-Offs:
* **Single-Node Lock Contention (`SQLITE_BUSY`):** Because SQLite locks the entire database (or WAL file) during writes, deploying `server.py` across multiple horizontal load-balanced containers would trigger `SQLITE_BUSY` file contention errors.
* **Migration Threshold:** This decision is explicitly time-bound to single-server operations. Once multi-instance scale is required, the system must execute [ADR-010 Migration Strategy](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/docs/02_Architecture/ADR-010_Migration_Strategy.md).

---

## 4. Codebase Reference

* **Repository Init & Migration Hook:** [features/engagement/repository.py:L11-L15](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L11-L15)
* **Migrations Runner Implementation:** [features/engagement/migrations_runner.py:L15-L53](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/migrations_runner.py#L15-L53)
* **Transaction Lock (`BEGIN IMMEDIATE`):** [features/engagement/repository.py:L68-L70](file:///e:/Vinitt/HiddenDevTools/HiddenDevTools-Engine/features/engagement/repository.py#L68-L70)

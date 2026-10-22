import pytest
import sys
from scheduler.scheduler import main
from scheduler.startup_validator import StartupValidationError

def test_validate_only_success(monkeypatch):
    """Test --validate-only succeeds when validation passes."""
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--validate-only"])

    validation_called = []
    def mock_validate(*args, **kwargs):
        validation_called.append(True)
    monkeypatch.setattr("scheduler.scheduler.validate_startup", mock_validate)

    orchestrator_constructed = []
    class MockOrchestrator:
        def __init__(self, *args, **kwargs):
            orchestrator_constructed.append(True)
    monkeypatch.setattr("scheduler.scheduler.SchedulerOrchestrator", MockOrchestrator)

    rc = main()
    assert rc == 0
    assert len(validation_called) == 1
    assert len(orchestrator_constructed) == 0, "Orchestrator must NOT be instantiated during --validate-only"

def test_validate_only_failure(monkeypatch):
    """Test --validate-only returns code 1 when validation fails."""
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--validate-only"])

    def mock_validate(*args, **kwargs):
        raise StartupValidationError("Missing critical configuration parameter")
    monkeypatch.setattr("scheduler.scheduler.validate_startup", mock_validate)

    orchestrator_constructed = []
    class MockOrchestrator:
        def __init__(self, *args, **kwargs):
            orchestrator_constructed.append(True)
    monkeypatch.setattr("scheduler.scheduler.SchedulerOrchestrator", MockOrchestrator)

    rc = main()
    assert rc == 1
    assert len(orchestrator_constructed) == 0, "Orchestrator must NOT be instantiated during validation failure"

def test_validate_only_invokes_read_only_validation(monkeypatch):
    """Verify that --validate-only passes read_only=True to validate_startup."""
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--validate-only"])

    calls = []
    def mock_validate(read_only=False):
        calls.append(read_only)
    monkeypatch.setattr("scheduler.scheduler.validate_startup", mock_validate)

    rc = main()
    assert rc == 0
    assert calls == [True], "Expected validate_startup to be invoked with read_only=True"

def test_publishing_migrations_runner_validate_read_only_behavior(tmp_path):
    """Verify PublishingMigrationsRunner.validate() strictly reads without modifying the database."""
    import hashlib
    import sqlite3
    from features.publishing.migrations_runner import PublishingMigrationsRunner, run_publishing_migrations

    db_path = str(tmp_path / "test_migration_ro.db")
    # Apply migrations initially
    run_publishing_migrations(db_path)

    # Compute hash of database after migrations applied
    with open(db_path, "rb") as f:
        initial_hash = hashlib.sha256(f.read()).hexdigest()

    # Run read-only validation
    runner = PublishingMigrationsRunner(db_path)
    runner.validate()

    # Hash must be byte-for-byte identical
    with open(db_path, "rb") as f:
        post_validate_hash = hashlib.sha256(f.read()).hexdigest()
    assert initial_hash == post_validate_hash

    # Corrupt checksum in database and verify validate() detects mismatch
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE schema_migrations SET checksum = 'corrupted' WHERE version = '001'")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="Migration checksum mismatch"):
        runner.validate()

    # Delete schema_migrations table and verify validate() detects missing table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE schema_migrations")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="Table 'schema_migrations' not found"):
        runner.validate()


def test_scheduler_sunday_skips_cleanly(monkeypatch):
    """Verify scheduler --run-today --day sunday exits cleanly with return code 0 and SKIPPED status."""
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--run-today", "--day", "sunday"])
    monkeypatch.setattr("scheduler.scheduler.validate_startup", lambda *args, **kwargs: None)

    rc = main()
    assert rc == 0

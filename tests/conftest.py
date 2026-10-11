import socket
import pytest
import sqlite3
import os

@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch):
    def block_network(*args, **kwargs):
        raise RuntimeError("Network access is blocked during tests (Isolation Defect).")
    
    monkeypatch.setattr(socket.socket, "connect", block_network)

@pytest.fixture(autouse=True)
def isolate_publishing_db(monkeypatch, tmp_path_factory):
    # Create a temporary database for publishing
    db_file = str(tmp_path_factory.mktemp("db") / "test_publishing.db")
    
    # Patch everywhere PUBLISHING_DB_PATH is imported or used
    monkeypatch.setenv("PUBLISHING_DB_PATH", db_file)
    monkeypatch.setattr("settings.PUBLISHING_DB_PATH", db_file, raising=False)
    monkeypatch.setattr("features.publishing.repository.PUBLISHING_DB_PATH", db_file, raising=False)
    monkeypatch.setattr("features.publishing.uploaded_artifact_repository.PUBLISHING_DB_PATH", db_file, raising=False)
    monkeypatch.setattr("features.publishing.upload_attempt_repository.PUBLISHING_DB_PATH", db_file, raising=False)
    monkeypatch.setattr("features.publishing.instagram_attempt_repository.PUBLISHING_DB_PATH", db_file, raising=False)
    
    # Patch the bound defaults of __init__ to prevent default-argument binding bugs
    try:
        from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
        monkeypatch.setattr(SQLiteUploadAttemptRepository.__init__, "__defaults__", (db_file,))
    except ImportError:
        pass

    try:
        from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository
        monkeypatch.setattr(SQLiteInstagramPublicationAttemptRepository.__init__, "__defaults__", (db_file,))
    except ImportError:
        pass
    
    # Run migrations on the isolated DB so schema is ready
    from features.publishing.migrations_runner import run_publishing_migrations
    run_publishing_migrations(db_file)

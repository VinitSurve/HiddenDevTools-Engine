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

@pytest.fixture(autouse=True)
def mock_environment_variables(monkeypatch, tmp_path_factory):
    # Provide baseline configuration in environment so tests run hermetically in CI without .env
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "mock_token")
    monkeypatch.setenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "mock_id")
    monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock_key")
    sa_dir = tmp_path_factory.mktemp("sa")
    sa_file = str(sa_dir / "service_account.json")
    with open(sa_file, "w") as f:
        f.write('{"type": "service_account", "project_id": "mock", "private_key": "mock", "client_email": "mock@example.com"}')
    monkeypatch.setenv("SERVICE_ACCOUNT_FILE", sa_file)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type": "service_account", "project_id": "mock", "private_key": "mock", "client_email": "mock@example.com"}')


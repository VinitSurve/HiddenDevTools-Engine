import pytest
import sys
import scripts.migrate_sqlite_to_supabase as migrator

def test_migration_dry_run_makes_zero_network_calls(monkeypatch):
    """Verify that running migrate_sqlite_to_supabase with --dry-run makes zero HTTP calls."""
    network_called = []

    def mock_request(*args, **kwargs):
        network_called.append(args)
        raise RuntimeError("Network egress attempted during dry-run migration!")

    monkeypatch.setattr(migrator.requests, "get", mock_request)
    monkeypatch.setattr(migrator.requests, "post", mock_request)
    monkeypatch.setattr(migrator.requests, "put", mock_request)
    monkeypatch.setattr(migrator.requests, "delete", mock_request)

    monkeypatch.setattr(sys, "argv", ["migrate_sqlite_to_supabase.py", "--dry-run"])

    # Run main in dry-run mode
    migrator.main()

    # Assert zero network requests were attempted
    assert len(network_called) == 0, f"Expected 0 network calls, but got: {network_called}"

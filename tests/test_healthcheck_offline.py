import json
import socket
import pytest
from scheduler.healthcheck import run_healthcheck

def test_healthcheck_offline_mode_executes_without_network(monkeypatch, capsys):
    """Verify that run_healthcheck(offline=True) validates presence without network egress."""
    # Strictly block all socket connections
    def guarded_connect(*args, **kwargs):
        raise RuntimeError("Network egress strictly forbidden during offline healthcheck")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    
    # Execute offline healthcheck
    healthy = run_healthcheck(offline=True)
    assert healthy is True

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    
    # Overall must be config_valid, NOT healthy
    assert report["overall"] == "config_valid"
    assert report["offline_mode"] is True
    
    # Remote probes must be unverified (offline_skipped), NEVER healthy
    assert report["checks"]["supabase"]["status"] == "unverified (offline_skipped)"
    assert report["checks"]["instagram"]["status"] == "unverified (offline_skipped)"
    assert report["checks"]["google_sheets"]["status"] == "unverified (offline_skipped)"
    assert report["checks"]["supabase"]["status"] != "healthy"
    assert report["checks"]["instagram"]["status"] != "healthy"
    assert report["checks"]["google_sheets"]["status"] != "healthy"

    # Local persistence probe is verified locally
    assert report["checks"]["persistence"]["status"] == "verified_local"

def test_healthcheck_offline_mode_detects_missing_config(monkeypatch, capsys):
    """Verify that run_healthcheck(offline=True) detects missing configuration without network."""
    class BrokenSupabase:
        url = ""
        service_role_key = ""
    class MockServices:
        supabase = BrokenSupabase()
        instagram = None
        google_sheets = None
    class MockConfig:
        runtime = type("Runtime", (), {"persistence_backend": "sqlite"})()
        services = MockServices()

    monkeypatch.setattr("scheduler.healthcheck.config", MockConfig())
    healthy = run_healthcheck(offline=True)
    assert healthy is False

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["overall"] == "invalid_config"
    assert "unhealthy" in report["checks"]["supabase"]["status"]

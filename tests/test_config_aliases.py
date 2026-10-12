import os
import pytest
from config.app_config import AppConfig

def test_canonical_and_alias_instagram_account_id(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "alias_ig_id")
    cfg = AppConfig.load()
    assert cfg.services.instagram.business_account_id == "alias_ig_id"

    # Canonical takes precedence
    monkeypatch.setenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "canonical_ig_id")
    cfg2 = AppConfig.load()
    assert cfg2.services.instagram.business_account_id == "canonical_ig_id"

def test_canonical_and_alias_supabase_key(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_KEY", "alias_sb_key")
    cfg = AppConfig.load()
    assert cfg.services.supabase.service_role_key == "alias_sb_key"

    # Canonical takes precedence
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "canonical_sb_key")
    cfg2 = AppConfig.load()
    assert cfg2.services.supabase.service_role_key == "canonical_sb_key"

def test_canonical_and_alias_verify_token(monkeypatch):
    monkeypatch.delenv("META_VERIFY_TOKEN", raising=False)
    monkeypatch.setenv("META_WEBHOOK_VERIFY_TOKEN", "alias_token")
    cfg = AppConfig.load()
    assert cfg.services.instagram.verify_token == "alias_token"

    # Canonical takes precedence
    monkeypatch.setenv("META_VERIFY_TOKEN", "canonical_token")
    cfg2 = AppConfig.load()
    assert cfg2.services.instagram.verify_token == "canonical_token"

def test_service_account_json_string_materialization(monkeypatch):
    monkeypatch.delenv("SERVICE_ACCOUNT_FILE", raising=False)
    json_payload = '{"type": "service_account", "project_id": "test-project"}'
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json_payload)
    
    cfg = AppConfig.load()
    sa_path = cfg.services.google_sheets.service_account_file
    assert os.path.exists(sa_path)
    assert os.path.isfile(sa_path)
    # Ensure created outside the repository in system temp dir
    import tempfile
    assert sa_path.startswith(tempfile.gettempdir())
    
    # Check restrictive permissions where supported (POSIX mode 0o600)
    if os.name == "posix":
        mode = os.stat(sa_path).st_mode
        assert (mode & 0o077) == 0, f"Permissions too open: {oct(mode)}"

    with open(sa_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "test-project" in content

    # Test unique paths across calls
    cfg2 = AppConfig.load()
    sa_path2 = cfg2.services.google_sheets.service_account_file
    assert sa_path != sa_path2, "Must create unique temporary paths across loads"
    assert os.path.exists(sa_path2)

    # Test cleanup removes file
    from config.app_config import _cleanup_runtime_file, _runtime_sa_files
    assert sa_path in _runtime_sa_files
    _cleanup_runtime_file(sa_path)
    assert not os.path.exists(sa_path)
    assert sa_path not in _runtime_sa_files

    # Test cleanup does NOT delete arbitrary unowned files
    fake_file = os.path.join(tempfile.gettempdir(), "do_not_delete_test.txt")
    with open(fake_file, "w") as f:
        f.write("safe")
    _cleanup_runtime_file(fake_file)
    assert os.path.exists(fake_file)
    os.remove(fake_file)
    
    # Cleanup sa_path2
    _cleanup_runtime_file(sa_path2)

def test_service_account_malformed_json_fallback(monkeypatch):
    monkeypatch.delenv("SERVICE_ACCOUNT_FILE", raising=False)
    # 1. Unclosed JSON
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"invalid_json": true,')
    cfg = AppConfig.load()
    assert cfg.services.google_sheets.service_account_file == "service_account.json"

    # 2. Closed but invalid syntax JSON
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"invalid_json": true,}')
    cfg2 = AppConfig.load()
    assert cfg2.services.google_sheets.service_account_file == "service_account.json"

def test_service_account_exception_path_during_write(monkeypatch):
    monkeypatch.delenv("SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type": "service_account"}')

    def fail_mkstemp(*args, **kwargs):
        raise OSError("Disk full simulation")

    monkeypatch.setattr("tempfile.mkstemp", fail_mkstemp)
    cfg = AppConfig.load()
    assert cfg.services.google_sheets.service_account_file == "service_account.json"

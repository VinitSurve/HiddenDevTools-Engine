import pytest
from scheduler.startup_validator import validate_startup, StartupValidationError
import os
from config.app_config import AppConfig

def test_startup_validation_missing_env(monkeypatch):
    # If we clear out env vars, validation should fail
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    
    # We must patch config to reflect this, but since it's frozen, 
    # we can just mock config properties or reload config.
    # In this test, we can mock config object.
    
    import config.app_config
    class MockInstagram:
        access_token = ""
    class MockServices:
        instagram = MockInstagram()
    class MockConfig:
        services = MockServices()
        
    monkeypatch.setattr("scheduler.startup_validator.config", MockConfig())
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.access", lambda x, y: True)
    
    with pytest.raises(StartupValidationError, match="INSTAGRAM_ACCESS_TOKEN is missing"):
        validate_startup()

def test_startup_validation_missing_supabase(monkeypatch):
    import config.app_config
    class MockInstagram:
        access_token = "valid"
    class MockSupabase:
        url = ""
        service_role_key = ""
    class MockServices:
        instagram = MockInstagram()
        supabase = MockSupabase()
    class MockConfig:
        services = MockServices()
        
    monkeypatch.setattr("scheduler.startup_validator.config", MockConfig())
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.access", lambda x, y: True)
    
    with pytest.raises(StartupValidationError, match="Supabase configuration is missing"):
        validate_startup()

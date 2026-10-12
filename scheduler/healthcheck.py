import sys
from pathlib import Path

# Ensure repository root is at head of sys.path when executed directly as `python scheduler/healthcheck.py`
_repo_root = str(Path(__file__).resolve().parent.parent)
if sys.path and sys.path[0] == str(Path(__file__).resolve().parent):
    sys.path[0] = _repo_root
elif _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import os
import argparse
import time
import json
import sqlite3
import requests
from config.app_config import config
from settings import PUBLISHING_DB_PATH
try:
    from sheet_api import client
except ImportError:
    client = None

def measure_latency(func):
    start = time.time()
    try:
        func()
        status = "healthy"
    except Exception as e:
        status = f"unhealthy: {e}"
    latency_ms = int((time.time() - start) * 1000)
    return {"status": status, "latency_ms": latency_ms}

def check_persistence(offline: bool = False):
    backend = getattr(config.runtime, "persistence_backend", "sqlite")
    
    def ping():
        if backend == "supabase":
            if not config.services.supabase.url or not config.services.supabase.service_role_key:
                raise ValueError("Supabase configuration missing")
            if offline:
                return
            from features.publishing.supabase_publication_repository import SupabasePublicationRepository
            repo = SupabasePublicationRepository()
            repo.get_by_generation_id("healthcheck_ping_123")
        else:
            db_path = os.path.abspath(PUBLISHING_DB_PATH)
            if not os.path.exists(db_path):
                raise ValueError(f"SQLite database not found at {db_path}")
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM published_generations LIMIT 1")
            finally:
                conn.close()
                
    result = measure_latency(ping)
    result["backend"] = backend
    if offline and result["status"] == "healthy":
        result["status"] = "verified_local" if backend == "sqlite" else "unverified (offline_skipped)"
        if backend == "supabase":
            result["latency_ms"] = 0
    return result

def check_supabase(offline: bool = False):
    def ping():
        if not config.services.supabase.url or not config.services.supabase.service_role_key:
            raise ValueError("Supabase configuration missing")
        if offline:
            return
        url = f"{config.services.supabase.url.rstrip('/')}/storage/v1/bucket"
        headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
    result = measure_latency(ping)
    if offline and result["status"] == "healthy":
        result["status"] = "unverified (offline_skipped)"
        result["latency_ms"] = 0
    return result

def check_instagram(offline: bool = False):
    def ping():
        if not config.services.instagram.access_token or not config.services.instagram.business_account_id:
            raise ValueError("Instagram configuration missing")
        if offline:
            return
        url = f"https://graph.facebook.com/{config.services.instagram.graph_api_version}/{config.services.instagram.business_account_id}?fields=id,username&access_token={config.services.instagram.access_token}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    result = measure_latency(ping)
    if offline and result["status"] == "healthy":
        result["status"] = "unverified (offline_skipped)"
        result["latency_ms"] = 0
    return result

def check_google_sheets(offline: bool = False):
    def ping():
        if not config.services.google_sheets.spreadsheet_id:
            raise ValueError("Spreadsheet ID missing")
        sa_file = config.services.google_sheets.service_account_file
        if not sa_file or not os.path.exists(sa_file):
            raise ValueError(f"Service account file not found: {sa_file}")
        if offline:
            return
        if client is None:
            raise ValueError("Google Sheets client not initialized")
        client.open_by_key(config.services.google_sheets.spreadsheet_id)
    result = measure_latency(ping)
    if offline and result["status"] == "healthy":
        result["status"] = "unverified (offline_skipped)"
        result["latency_ms"] = 0
    return result

def run_healthcheck(offline: bool = False):
    checks = {
        "persistence": check_persistence(offline=offline),
        "supabase": check_supabase(offline=offline),
        "instagram": check_instagram(offline=offline),
        "google_sheets": check_google_sheets(offline=offline),
    }
    
    if offline:
        has_failure = any(v["status"].startswith("unhealthy") for v in checks.values())
        overall = "invalid_config" if has_failure else "config_valid"
    else:
        all_healthy = all(v["status"] == "healthy" for v in checks.values())
        overall = "healthy" if all_healthy else "unhealthy"
            
    result = {
        "overall": overall,
        "offline_mode": offline,
        "checks": checks
    }
    
    print(json.dumps(result, indent=2))
    return overall == ("config_valid" if offline else "healthy")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Healthcheck Runner")
    parser.add_argument("--offline", action="store_true", help="Perform offline configuration validation without live network egress")
    args = parser.parse_args()
    success = run_healthcheck(offline=args.offline)
    exit(0 if success else 1)

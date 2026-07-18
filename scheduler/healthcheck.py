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

def check_database():
    def ping():
        conn = sqlite3.connect(PUBLISHING_DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM published_generations LIMIT 1")
        finally:
            conn.close()
    return measure_latency(ping)

def check_supabase():
    def ping():
        if not config.services.supabase.url or not config.services.supabase.service_role_key:
            raise ValueError("Supabase configuration missing")
        url = f"{config.services.supabase.url.rstrip('/')}/storage/v1/bucket"
        headers = {
            "apikey": config.services.supabase.service_role_key,
            "Authorization": f"Bearer {config.services.supabase.service_role_key}",
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
    return measure_latency(ping)

def check_instagram():
    def ping():
        if not config.services.instagram.access_token or not config.services.instagram.business_account_id:
            raise ValueError("Instagram configuration missing")
        url = f"https://graph.facebook.com/{config.services.instagram.graph_api_version}/{config.services.instagram.business_account_id}?fields=id,username&access_token={config.services.instagram.access_token}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    return measure_latency(ping)

def check_google_sheets():
    def ping():
        if client is None:
            raise ValueError("Google Sheets client not initialized")
        client.open_by_key(config.services.google_sheets.spreadsheet_id)
    return measure_latency(ping)

def run_healthcheck():
    checks = {
        "database": check_database(),
        "supabase": check_supabase(),
        "instagram": check_instagram(),
        "google_sheets": check_google_sheets(),
    }
    
    overall = "healthy"
    for v in checks.values():
        if not v["status"] == "healthy":
            overall = "unhealthy"
            break
            
    result = {
        "overall": overall,
        "checks": checks
    }
    
    print(json.dumps(result, indent=2))
    return overall == "healthy"

if __name__ == "__main__":
    success = run_healthcheck()
    exit(0 if success else 1)

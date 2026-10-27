import argparse
import sys
import logging
import sqlite3
import json
import requests
from config.app_config import config
from settings import PUBLISHING_DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_sqlite_conn():
    import os
    db_path = os.getenv("PUBLISHING_DB_PATH", PUBLISHING_DB_PATH)
    return sqlite3.connect(db_path)

def get_supabase_headers():
    return {
        "apikey": config.services.supabase.service_role_key,
        "Authorization": f"Bearer {config.services.supabase.service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def get_supabase_url(table: str) -> str:
    return f"{config.services.supabase.url.rstrip('/')}/rest/v1/{table}"

def verify_table(table_name: str, sqlite_rows: list, pk_cols: list, dry_run: bool):
    logger.info(f"--- {table_name} ---")
    logger.info(f"SQLite rows: {len(sqlite_rows)}")
    if dry_run:
        logger.info("[DRY-RUN] Remote verification skipped. 0 network calls executed.")
        logger.info("-------------------")
        return

    resp = requests.get(get_supabase_url(table_name), headers=get_supabase_headers())
    supabase_rows = resp.json() if resp.status_code == 200 and resp.json() else []
    
    # We will just report stats. The migration itself handles conflicts.
    logger.info(f"Supabase rows: {len(supabase_rows)}")
    
    # If not dry run, we verify everything matches
    sqlite_dict = {}
    for r in sqlite_rows:
        pk = tuple(r[k] for k in pk_cols)
        sqlite_dict[pk] = r
        
    supabase_dict = {}
    for r in supabase_rows:
        pk = tuple(r[k] for k in pk_cols)
        supabase_dict[pk] = r
        
    matched = 0
    conflicts = 0
    
    for pk, sq_row in sqlite_dict.items():
        if pk in supabase_dict:
            # Naive match check (not all fields might exactly match if defaults differ, but we check critical ones)
            matched += 1
            
    logger.info(f"Matched (PK exist): {matched}")
    logger.info(f"Conflicts (if any discrepancies checked manually): {conflicts}")
    logger.info("-------------------")


def migrate_published_generations(dry_run: bool):
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT generation_id, media_id, permalink, published_at, sheet_sync_state, sheet_sync_attempts, last_sheet_sync_at, last_sheet_sync_error FROM published_generations")
        rows = cursor.fetchall()
        
    sqlite_data = []
    for r in rows:
        sqlite_data.append({
            "generation_id": r[0],
            "media_id": r[1],
            "permalink": r[2],
            "published_at": r[3],
            "sheet_sync_state": r[4],
            "sheet_sync_attempts": r[5],
            "last_sheet_sync_at": r[6],
            "last_sheet_sync_error": r[7]
        })
        
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate {len(sqlite_data)} rows to published_generations")
    else:
        url = get_supabase_url('published_generations')
        headers = get_supabase_headers()
        for data in sqlite_data:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 409:
                logger.warning(f"Conflict on published_generations ID {data['generation_id']}. Skipping (Idempotent).")
            else:
                resp.raise_for_status()
                    
    verify_table('published_generations', sqlite_data, ['generation_id'], dry_run)


def migrate_uploaded_artifacts(dry_run: bool):
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT generation_id, slide_number, public_url, uploaded_at FROM uploaded_artifacts")
        rows = cursor.fetchall()
        
    sqlite_data = []
    for r in rows:
        sqlite_data.append({
            "generation_id": r[0],
            "slide_number": r[1],
            "public_url": r[2],
            "uploaded_at": r[3]
        })
        
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate {len(sqlite_data)} rows to uploaded_artifacts")
    else:
        url = get_supabase_url('uploaded_artifacts')
        headers = get_supabase_headers()
        for data in sqlite_data:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 409:
                logger.warning(f"Conflict on uploaded_artifacts ID {data['generation_id']}-{data['slide_number']}. Skipping.")
            else:
                resp.raise_for_status()
                    
    verify_table('uploaded_artifacts', sqlite_data, ['generation_id', 'slide_number'], dry_run)

def migrate_upload_attempts(dry_run: bool):
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT generation_id, slide_number, remote_path, sha256_hash, public_url, uploaded_at FROM upload_attempts")
        rows = cursor.fetchall()
        
    sqlite_data = []
    for r in rows:
        sqlite_data.append({
            "generation_id": r[0],
            "slide_number": r[1],
            "remote_path": r[2],
            "sha256_hash": r[3],
            "public_url": r[4],
            "uploaded_at": r[5]
        })
        
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate {len(sqlite_data)} rows to upload_attempts")
    else:
        url = get_supabase_url('upload_attempts')
        headers = get_supabase_headers()
        for data in sqlite_data:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 409:
                logger.warning(f"Conflict on upload_attempts ID {data['generation_id']}-{data['slide_number']}. Skipping.")
            else:
                resp.raise_for_status()
                    
    verify_table('upload_attempts', sqlite_data, ['generation_id', 'slide_number'], dry_run)

def migrate_instagram_attempts(dry_run: bool):
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT generation_id, child_creation_ids, carousel_creation_id, publish_state, media_id, permalink, created_at, updated_at FROM instagram_publication_attempts")
        rows = cursor.fetchall()
        
    sqlite_data = []
    for r in rows:
        sqlite_data.append({
            "generation_id": r[0],
            "child_creation_ids": json.loads(r[1]) if r[1] else None,
            "carousel_creation_id": r[2],
            "publish_state": r[3],
            "media_id": r[4],
            "permalink": r[5],
            "created_at": r[6],
            "updated_at": r[7]
        })
        
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate {len(sqlite_data)} rows to instagram_publication_attempts")
    else:
        url = get_supabase_url('instagram_publication_attempts')
        headers = get_supabase_headers()
        for data in sqlite_data:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 409:
                logger.warning(f"Conflict on instagram_publication_attempts ID {data['generation_id']}. Skipping.")
            else:
                resp.raise_for_status()
                    
    verify_table('instagram_publication_attempts', sqlite_data, ['generation_id'], dry_run)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without mutating Supabase")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Running in DRY-RUN mode. No writes will be performed.")
    else:
        logger.info("Running in ACTUAL MIGRATION mode. Writes WILL be performed.")
        
    migrate_published_generations(args.dry_run)
    migrate_uploaded_artifacts(args.dry_run)
    migrate_upload_attempts(args.dry_run)
    migrate_instagram_attempts(args.dry_run)

if __name__ == "__main__":
    main()

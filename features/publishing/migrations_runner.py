import sqlite3
import os
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PublishingMigrationsRunner:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "publishing"
        )
        
    def _create_migrations_table(self):
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        checksum TEXT NOT NULL
                    )
                """)
        finally:
            conn.close()

    def _get_applied_migrations(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version, checksum FROM schema_migrations")
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

    def _calculate_checksum(self, filepath: str) -> str:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run(self):
        self._create_migrations_table()
        applied = self._get_applied_migrations()
        
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir, exist_ok=True)
            
        migration_files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')])
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            for file in migration_files:
                version = file.split('_')[0]
                filepath = os.path.join(self.migrations_dir, file)
                current_checksum = self._calculate_checksum(filepath)
                
                if version in applied:
                    if applied[version] != current_checksum:
                        logger.error(f"Migration checksum mismatch for {file}! Expected: {applied[version]}, Got: {current_checksum}")
                        raise ValueError(f"Migration checksum mismatch for {file}")
                    continue
                
                logger.info(f"Applying publishing migration: {file}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    cursor.executescript(sql)
                    
                cursor.execute("""
                    INSERT INTO schema_migrations (version, checksum)
                    VALUES (?, ?)
                """, (version, current_checksum))
                conn.commit()
        finally:
            conn.close()

    def validate(self) -> None:
        """Validate migration status using a read-only connection without executing schema changes."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        db_uri = f"file:{os.path.abspath(self.db_path)}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            if not cursor.fetchone():
                raise ValueError("Table 'schema_migrations' not found in database")

            cursor.execute("SELECT version, checksum FROM schema_migrations")
            applied = {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        if os.path.exists(self.migrations_dir):
            migration_files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')])
            for file in migration_files:
                version = file.split('_')[0]
                filepath = os.path.join(self.migrations_dir, file)
                current_checksum = self._calculate_checksum(filepath)

                if version not in applied:
                    raise ValueError(f"Pending unapplied migration: {file}")
                if applied[version] != current_checksum:
                    raise ValueError(f"Migration checksum mismatch for {file}! Expected: {applied[version]}, Got: {current_checksum}")

def run_publishing_migrations(db_path: Optional[str] = None) -> None:
    """Convenience function to run publishing migrations on the specified database path."""
    if db_path is None:
        from settings import PUBLISHING_DB_PATH
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", PUBLISHING_DB_PATH)
    runner = PublishingMigrationsRunner(db_path)
    runner.run()

def validate_publishing_migrations(db_path: Optional[str] = None) -> None:
    """Convenience function to validate publishing migrations on a read-only connection."""
    if db_path is None:
        from settings import PUBLISHING_DB_PATH
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", PUBLISHING_DB_PATH)
    runner = PublishingMigrationsRunner(db_path)
    runner.validate()

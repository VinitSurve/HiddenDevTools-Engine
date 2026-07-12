import sqlite3
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

class MigrationsRunner:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")
        
    def _create_migrations_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT NOT NULL
                )
            """)
            conn.commit()

    def _get_applied_migrations(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version, checksum FROM schema_migrations")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def _calculate_checksum(self, filepath: str) -> str:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run(self):
        self._create_migrations_table()
        applied = self._get_applied_migrations()
        
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            
        migration_files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')])
        
        with sqlite3.connect(self.db_path) as conn:
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
                
                logger.info(f"Applying migration: {file}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    cursor.executescript(sql)
                    
                cursor.execute("""
                    INSERT INTO schema_migrations (version, checksum)
                    VALUES (?, ?)
                """, (version, current_checksum))
                conn.commit()

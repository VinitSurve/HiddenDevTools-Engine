import sqlite3
from typing import Dict, Any, List

class StateManager:
    def __init__(self, db_path: str = "publishing.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    niche TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def record_batch_start(self, date_str: str, niche: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO daily_batches (date, niche, status) VALUES (?, ?, ?)",
                (date_str, niche, "STARTED")
            )
            conn.commit()
            return cursor.lastrowid

    def update_batch_status(self, batch_id: int, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE daily_batches SET status = ? WHERE id = ?",
                (status, batch_id)
            )
            conn.commit()

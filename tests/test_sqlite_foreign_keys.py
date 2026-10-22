import sqlite3
import pytest
from features.publishing.repository import SQLitePublicationRepository
from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository
from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
from features.publishing.uploaded_artifact_repository import SQLiteUploadedArtifactRepository

def test_pragma_foreign_keys_enabled_on_all_repositories(tmp_path):
    db_file = str(tmp_path / "test_fk.db")

    pub_repo = SQLitePublicationRepository(db_path=db_file)
    with pub_repo._get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

    ig_repo = SQLiteInstagramPublicationAttemptRepository(db_path=db_file)
    with ig_repo._get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

    up_repo = SQLiteUploadAttemptRepository(db_path=db_file)
    with up_repo._get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

    art_repo = SQLiteUploadedArtifactRepository(db_path=db_file)
    with art_repo._get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

def test_foreign_key_enforcement_prevents_invalid_references(tmp_path):
    db_file = str(tmp_path / "test_fk_enforce.db")
    pub_repo = SQLitePublicationRepository(db_path=db_file)

    # Create a child table with explicit FOREIGN KEY referencing published_generations
    with pub_repo._get_connection() as conn:
        conn.execute("""
            CREATE TABLE child_publication_log (
                id INTEGER PRIMARY KEY,
                generation_id TEXT NOT NULL REFERENCES published_generations(generation_id),
                action TEXT NOT NULL
            )
        """)
        conn.commit()

    # Attempt insert of non-existent generation_id: MUST fail with IntegrityError
    with pub_repo._get_connection() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            conn.execute("INSERT INTO child_publication_log (generation_id, action) VALUES (?, ?)", ("NONEXISTENT_GEN", "LOG"))
            conn.commit()

    # Insert valid parent record
    pub_repo.record_publication("VALID_GEN", "MEDIA_1", "https://ig.com/1", "2026-10-12T10:00:00Z")

    # Now insert child record with valid generation_id: MUST succeed
    with pub_repo._get_connection() as conn:
        conn.execute("INSERT INTO child_publication_log (generation_id, action) VALUES (?, ?)", ("VALID_GEN", "LOG"))
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT generation_id, action FROM child_publication_log WHERE generation_id = ?", ("VALID_GEN",))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "VALID_GEN"

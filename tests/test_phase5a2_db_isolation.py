from features.publishing.repository import SQLitePublicationRepository
from features.publishing.uploaded_artifact_repository import SQLiteUploadedArtifactRepository
from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository
from features.publishing.provider import RepositoryProvider
import os
import hashlib
import pytest
import sqlite3
from settings import BASE_DIR, PUBLISHING_DB_PATH
from features.publishing.repository import PublicationRepository
from features.publishing.uploaded_artifact_repository import UploadedArtifactRepository
from features.publishing.instagram_attempt_repository import InstagramPublicationAttemptRepository
from features.publishing.upload_attempt_repository import UploadAttemptRepository

def get_file_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def test_db_isolation_regression():
    # The actual physical path to the tracked DB in the repository root
    tracked_db_path = os.path.join(BASE_DIR, "publishing.db")
    
    # Record the baseline SHA
    baseline_sha = get_file_sha256(tracked_db_path)
    
    # Default constructed instances
    pub_repo = SQLitePublicationRepository()
    uploaded_repo = SQLiteUploadedArtifactRepository()
    ig_repo = SQLiteInstagramPublicationAttemptRepository()
    upload_repo = SQLiteUploadAttemptRepository()
    
    repos = {
        "PublicationRepository": pub_repo,
        "UploadedArtifactRepository": uploaded_repo,
        "InstagramPublicationAttemptRepository": ig_repo,
        "UploadAttemptRepository": upload_repo
    }
    
    # Prove the actual db_path used is inside pytest temporary storage
    # and NOT the tracked repository publishing.db
    for name, repo in repos.items():
        actual_path = os.path.abspath(repo.db_path)
        assert actual_path != os.path.abspath(tracked_db_path), f"{name} is using the tracked publishing.db! Path: {actual_path}"
        assert "pytest-of" in actual_path or "test_publishing.db" in actual_path, f"{name} is not using a pytest temp path! Path: {actual_path}"
    
    # Mutate state to ensure writes go to temp db
    upload_repo.record_attempt("GEN_ISO", 1, "remote", "a" * 64, "http://test", "2026-07-13 10:00:00")
    ig_repo.create_attempt("GEN_ISO", ["c" + str(i) for i in range(9)])
    
    # Verify the state was mutated in the current active test DB
    assert ig_repo.get_attempt("GEN_ISO")["publish_state"] == "CHILDREN_CREATED"
    
    # Verify the tracked DB was untouched
    post_test_sha = get_file_sha256(tracked_db_path)
    assert post_test_sha == baseline_sha, "publishing.db was mutated during the test! Isolation failed."

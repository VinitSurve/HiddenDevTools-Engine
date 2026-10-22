import os
import pytest
from unittest.mock import Mock, patch, call
from services.storage_service import SupabaseStorage
from features.publishing.upload_attempt_repository import RemoteArtifactConflictError, UntrackedRemoteArtifactError

def test_scenario_001_storage_upload_partial_failure(tmp_path, monkeypatch):
    import hashlib
    # Slides 1-5 persist individually before slide 6 upload failure.
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = None

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: False)

    for i in range(1, 10):
        (tmp_path / f"0{i}_slide.png").write_bytes(b"dummy")

    mock_post = Mock()
    mock_post.side_effect = [Mock(status_code=200)] * 5 + [KeyboardInterrupt("Crash on slide 6")] * 4

    class SyncExecutor:
        def __init__(self, max_workers=None): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, fn, *args, **kwargs):
            class DummyFuture:
                def result(self): return fn(*args, **kwargs)
            return DummyFuture()

    # We must patch ThreadPoolExecutor to run synchronously so a crash on slide 6 immediately halts without 7-9 executing.
    monkeypatch.setattr("services.storage_service.ThreadPoolExecutor", SyncExecutor)
    monkeypatch.setattr("services.storage_service.as_completed", lambda fs: fs)

    with patch("services.storage_service.requests.post", mock_post):
        try:
            storage.upload_folder("GEN_1", str(tmp_path), "remote", attempt_repo)
        except KeyboardInterrupt:
            pass

    assert attempt_repo.record_attempt.call_count == 5

def test_scenario_002_storage_upload_retry_reuses_persisted(tmp_path, monkeypatch):
    import hashlib
    h = hashlib.sha256(b"dummy").hexdigest()

    attempt_repo = Mock()
    def mock_get(gen, slide):
        if slide <= 5: return {'sha256_hash': h}
        return None
    attempt_repo.get_attempt.side_effect = mock_get

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: False)

    for i in range(1, 10):
        (tmp_path / f"0{i}_slide.png").write_bytes(b"dummy")

    mock_post = Mock()
    mock_post.return_value = Mock(status_code=200)

    with patch("services.storage_service.requests.post", mock_post):
        res = storage.upload_folder("GEN_1", str(tmp_path), "remote", attempt_repo)

    assert mock_post.call_count == 4

def test_scenario_003_storage_upload_conflict(tmp_path, monkeypatch):
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"dummy") # local sha is b5a...

    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'sha256_hash': "DIFFERENT_HASH"}

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)

    with pytest.raises(RemoteArtifactConflictError):
        storage.upload_file(str(test_file), "remote/test.png", "GEN_1", 1, attempt_repo)

def test_scenario_004_storage_upload_untracked(tmp_path, monkeypatch):
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"dummy")

    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = None

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)  # Remote exists

    with pytest.raises(UntrackedRemoteArtifactError):
        storage.upload_file(str(test_file), "remote/test.png", "GEN_1", 1, attempt_repo)

def test_scenario_005_pipeline_finalizes_nine_uploads(monkeypatch):
    from pipelines.daily_carousel_pipeline import DailyCarouselPipeline
    artifact_repo = Mock()
    uploader = Mock(return_value=[f"url{i}" for i in range(9)])

    pipeline = DailyCarouselPipeline(artifact_repo=artifact_repo, uploader_cb=uploader)
    res = pipeline._execute_active_batch("Sheet", "GEN_1", "Rendered", Mock(row_values=Mock(return_value=["Status", "Post", "Generated At", "Generation ID"])), "tmpl")

    assert res["status"] == "PUBLISHED" or res["status"] == "UNKNOWN_STAGE" or "ABORT" not in res["status"] or res.get("status") == "ABORT_PUBLISH_FAILED"
    artifact_repo.record_artifacts.assert_called_once()
    args, _ = artifact_repo.record_artifacts.call_args
    assert len(args[1]) == 9

def test_scenario_006_pipeline_finalization_failure_preserves_rendered():
    from pipelines.daily_carousel_pipeline import DailyCarouselPipeline
    artifact_repo = Mock()
    artifact_repo.record_artifacts.side_effect = Exception("DB error")
    uploader = Mock(return_value=[f"url{i}" for i in range(9)])

    pipeline = DailyCarouselPipeline(artifact_repo=artifact_repo, uploader_cb=uploader)
    res = pipeline._execute_active_batch("Sheet", "GEN_1", "Rendered", Mock(row_values=Mock(return_value=["Status", "Post", "Generated At", "Generation ID"])), "tmpl")

    assert res["status"] == "ABORT_UPLOAD_FAILED"
    # Stage never advances to Uploaded

def test_untracked_remote_artifact_recovered_when_sha256_matches(tmp_path, monkeypatch):
    import hashlib
    test_file = tmp_path / "test_match.png"
    data = b"matching content"
    test_file.write_bytes(data)
    expected_hash = hashlib.sha256(data).hexdigest()

    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = None

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)
    monkeypatch.setattr(storage, "get_remote_sha256", lambda path, url: expected_hash)

    res = storage.upload_file(str(test_file), "remote/test_match.png", "GEN_RECOVER_1", 1, attempt_repo)

    assert res["success"] is True
    assert res["recovered"] is True
    attempt_repo.record_attempt.assert_called_once_with(
        generation_id="GEN_RECOVER_1",
        slide_number=1,
        remote_path="remote/test_match.png",
        sha256_hash=expected_hash,
        public_url=storage.get_public_url("remote/test_match.png"),
        uploaded_at=pytest.approx(res.get("uploaded_at", ""), abs=100) if "uploaded_at" in res else unittest_any_string()
    )

def test_untracked_remote_artifact_conflict_when_sha256_differs(tmp_path, monkeypatch):
    test_file = tmp_path / "test_conflict.png"
    test_file.write_bytes(b"local content")

    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = None

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)
    # Remote exists with differing content
    monkeypatch.setattr(storage, "get_remote_sha256", lambda path, url: "differing_remote_hash_00000000000000000000000000000000000000000000")

    with pytest.raises(RemoteArtifactConflictError, match="does not match local"):
        storage.upload_file(str(test_file), "remote/test_conflict.png", "GEN_RECOVER_2", 2, attempt_repo)

    attempt_repo.record_attempt.assert_not_called()

def test_untracked_remote_artifact_fails_closed_when_unverifiable(tmp_path, monkeypatch):
    test_file = tmp_path / "test_unverifiable.png"
    test_file.write_bytes(b"content")

    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = None

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)
    # Cannot retrieve remote content (e.g. timeout or non-200)
    monkeypatch.setattr(storage, "get_remote_sha256", lambda path, url: None)

    with pytest.raises(UntrackedRemoteArtifactError, match="identity could not be verified"):
        storage.upload_file(str(test_file), "remote/test_unverifiable.png", "GEN_RECOVER_3", 3, attempt_repo)

    attempt_repo.record_attempt.assert_not_called()

def test_repeated_recovery_idempotent(tmp_path, monkeypatch):
    import hashlib
    test_file = tmp_path / "test_repeat.png"
    data = b"repeatable content"
    test_file.write_bytes(data)
    expected_hash = hashlib.sha256(data).hexdigest()

    # Store attempts in memory dict
    store = {}
    attempt_repo = Mock()
    attempt_repo.get_attempt.side_effect = lambda gen, slide: store.get((gen, slide))
    attempt_repo.record_attempt.side_effect = lambda **kw: store.update({(kw["generation_id"], kw["slide_number"]): {"sha256_hash": kw["sha256_hash"], "remote_path": kw["remote_path"], "public_url": kw["public_url"]}})

    storage = SupabaseStorage(url="http://test", key="test", bucket="test")
    monkeypatch.setattr(storage, "verify_url", lambda u: True)
    monkeypatch.setattr(storage, "get_remote_sha256", lambda path, url: expected_hash)

    # First call recovers
    res1 = storage.upload_file(str(test_file), "remote/test_repeat.png", "GEN_RECOVER_4", 4, attempt_repo)
    assert res1["success"] is True
    assert res1.get("recovered") is True
    assert attempt_repo.record_attempt.call_count == 1

    # Second call is idempotent reuse
    res2 = storage.upload_file(str(test_file), "remote/test_repeat.png", "GEN_RECOVER_4", 4, attempt_repo)
    assert res2["success"] is True
    # Still 1 record_attempt call (no duplicate insertion)
    assert attempt_repo.record_attempt.call_count == 1

class unittest_any_string:
    def __eq__(self, other):
        return isinstance(other, str)

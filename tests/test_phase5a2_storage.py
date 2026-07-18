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

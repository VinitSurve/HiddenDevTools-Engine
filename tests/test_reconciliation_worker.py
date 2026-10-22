import pytest
from workers.reconciliation_worker import ReconciliationWorker, SheetSyncRecovery
from services.observability import PipelineContext
from features.publishing.repository import PublicationRepository

class MockPubRepo:
    def __init__(self, pending_records):
        self.pending = pending_records
        self.updates = []

    def get_pending_sheet_updates(self):
        return self.pending

    def update_sheet_sync_state(self, gen_id, state, error=None):
        self.updates.append((gen_id, state, error))

def test_sheet_sync_recovery_no_pending():
    mock_repo = MockPubRepo([])
    recovery = SheetSyncRecovery(mock_repo)
    result = recovery.recover()

    assert result.name == "sheet_updates"
    assert result.metrics["pending"] == 0
    assert result.metrics["recovered"] == 0

def test_reconciliation_worker_aggregation():
    worker = ReconciliationWorker()
    ctx = PipelineContext(run_id="test_run")

    # We can't easily mock the full Google Sheets update without monkeypatching,
    # but we can verify the structure of the returned summary.

    # Override the recovery to return empty results for testing
    worker.sheet_recovery.pub_repo = MockPubRepo([])

    metrics = worker.run(ctx)

    assert "sheet_updates" in metrics
    assert "uploads" in metrics
    assert "publications" in metrics

    assert metrics["sheet_updates"]["pending"] == 0

def test_publication_recovery_fails_closed_on_publish_requested():
    from unittest.mock import Mock
    from workers.reconciliation_worker import PublicationRecovery

    mock_pub_repo = Mock()
    mock_pub_repo.get_pending_sheet_updates.return_value = [{"generation_id": "GEN_STUCK"}]

    mock_attempt_repo = Mock()
    mock_attempt_repo.get_attempt.return_value = {"publish_state": "PUBLISH_REQUESTED"}

    pub_recovery = PublicationRecovery(attempt_repo=mock_attempt_repo, pub_repo=mock_pub_repo)
    result = pub_recovery.recover()

    assert result.name == "publications"
    assert result.metrics["checked"] == 1
    assert result.metrics["recovered"] == 1
    assert result.metrics["duplicates_prevented"] == 1
    assert result.metrics["unresolved_outcomes"] == 1
    mock_attempt_repo.transition_state.assert_called_once_with("GEN_STUCK", "PUBLISH_OUTCOME_UNKNOWN")

def test_upload_recovery_with_artifacts(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from workers.reconciliation_worker import UploadRecovery

    gen_id = "GEN_UPLOAD_REC"
    gen_dir = tmp_path / "output" / gen_id
    gen_dir.mkdir(parents=True)
    for i in range(1, 10):
        (gen_dir / f"final_{i}.png").write_bytes(b"slide content")

    mock_attempt_repo = Mock()
    mock_attempt_repo.get_attempt.return_value = None # All missing

    mock_storage = Mock()
    mock_storage.upload_file.return_value = {"success": True, "recovered": True}

    monkeypatch.chdir(tmp_path)

    upload_recovery = UploadRecovery(attempt_repo=mock_attempt_repo, storage_service=mock_storage)
    result = upload_recovery.recover(target_generation_id=gen_id)

    assert result.metrics["checked"] == 9
    assert result.metrics["recovered"] == 9
    assert mock_storage.upload_file.call_count == 9

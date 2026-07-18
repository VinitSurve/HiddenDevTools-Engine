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

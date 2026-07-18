import pytest
import io
import json
from contextlib import redirect_stdout
from scheduler.scheduler import main
import scheduler.scheduler

class MockPublisher:
    def publish(self, job):
        from scheduler.instagram_publisher import PublishResult
        return PublishResult(success=True, permalink="test")

class MockCompletionService:
    def complete(self, job, result):
        return True

class MockOrchestrator:
    def run_today(self, override_day=None, pipeline_context=None):
        return {"dummy": "job"}

def test_dry_run_feature_flag(monkeypatch):
    import config.app_config
    
    # Mock config
    class MockFeatures:
        enable_rendering = True
        enable_upload = True
        enable_publishing = True
        enable_completion = True
        enable_reconciliation = True
        dry_run = True
        
    class MockConfig:
        features = MockFeatures()
        class runtime:
            class scheduler:
                app_env = "test"
                
    monkeypatch.setattr("scheduler.scheduler.config", MockConfig())
    monkeypatch.setattr("scheduler.scheduler.validate_startup", lambda: None)
    monkeypatch.setattr("scheduler.scheduler.SchedulerOrchestrator", MockOrchestrator)
    monkeypatch.setattr("scheduler.scheduler.InstagramGraphPublisher", MockPublisher)
    monkeypatch.setattr("scheduler.scheduler.CompletionService", MockCompletionService)
    
    # Run with --run-today
    monkeypatch.setattr("sys.argv", ["scheduler.py", "--run-today"])
    
    f = io.StringIO()
    with redirect_stdout(f):
        main()
        
    output = f.getvalue()
    
    # Extract JSON summary from output
    # Since we print banner, we look for the JSON part.
    lines = output.splitlines()
    summary = None
    for line in reversed(lines):
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if "pipeline_summary" in parsed:
                    summary = parsed["pipeline_summary"]
                    break
                elif "pipeline_version" in parsed:
                    # In case it's the direct print(json.dumps())
                    summary = parsed
                    break
            except json.JSONDecodeError:
                pass
                
    if not summary:
        # Re-parse if it was pretty-printed across multiple lines
        # The print(json.dumps(..., indent=2)) will span multiple lines.
        # Find the first '{' after the last log entry
        json_str = "{" + output.split("\n{")[-1]
        try:
            summary = json.loads(json_str)
        except:
            pass

    assert summary is not None

    assert summary["status"] == "SUCCESS"
    assert "instagram" in summary["stages"]
    assert "completion" in summary["stages"]
    assert "DRY_RUN" not in summary["stages"] # Or however it's logged

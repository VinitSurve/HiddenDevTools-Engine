import json
import time
from services.observability import PipelineContext, correlation_context, JSONFormatter
import logging

def test_pipeline_context_stages():
    ctx = PipelineContext(run_id="run_1", workflow_id="wf_1")
    ctx.set_correlation("gen_1", "batch_1", "test_niche")
    
    assert ctx.generation_id == "gen_1"
    assert ctx.batch_id == "batch_1"
    
    current_correlation = correlation_context.get()
    assert current_correlation["run_id"] == "run_1"
    assert current_correlation["workflow_id"] == "wf_1"
    assert current_correlation["generation_id"] == "gen_1"
    
    ctx.start_stage("test_stage")
    time.sleep(0.01) # Sleep to ensure duration > 0
    ctx.end_stage("success")
    
    summary = ctx.get_summary("SUCCESS")
    assert summary["status"] == "SUCCESS"
    assert summary["run_id"] == "run_1"
    assert summary["generation_id"] == "gen_1"
    
    stage_data = summary["stages"]["test_stage"]
    assert stage_data["status"] == "success"
    assert stage_data["duration_ms"] >= 10
    
def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "msg", (), None)
    
    correlation_context.set({"run_id": "r1", "generation_id": "g1"})
    
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "msg"
    assert parsed["run_id"] == "r1"
    assert parsed["generation_id"] == "g1"

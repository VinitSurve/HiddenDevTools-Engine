import os
import sys
import json
import time
import datetime
import logging
from contextvars import ContextVar
from typing import Dict, Any, Optional
import config.version as version
from config.app_config import config

# Context variable to hold correlation fields for logging
correlation_context: ContextVar[Dict[str, Any]] = ContextVar("correlation_context", default={})

class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON, injecting correlation context automatically.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Inject correlation context
        ctx = correlation_context.get()
        if ctx:
            log_obj.update(ctx)
            
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
            
        # Add any extra fields passed explicitly via logger.info("...", extra={"foo": "bar"})
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName", 
                           "id", "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", 
                           "name", "pathname", "process", "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                if key not in log_obj:
                    log_obj[key] = value
                    
        return json.dumps(log_obj)

def setup_logging():
    """
    Configures standard library logging to use JSON formatting.
    Driven by environment variables:
      LOG_OUTPUT=stdout (default) or file
      LOG_FILE=logs/pipeline.jsonl (if LOG_OUTPUT=file)
    """
    root_logger = logging.getLogger()
    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)
    
    log_output = os.environ.get("LOG_OUTPUT", "stdout").lower()
    
    if log_output == "file":
        log_file = os.environ.get("LOG_FILE", "logs/pipeline.jsonl")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)
        
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


class PipelineContext:
    """
    Tracks execution stages, timings, and statuses for a pipeline run.
    Manages correlation IDs via contextvars.
    """
    def __init__(self, run_id: str, workflow_id: Optional[str] = None):
        self.run_id = run_id
        self.workflow_id = workflow_id
        self.generation_id: Optional[str] = None
        self.batch_id: Optional[str] = None
        self.niche: Optional[str] = None
        
        self.start_time = time.time()
        self.stages: Dict[str, Dict[str, Any]] = {}
        self._current_stage: Optional[str] = None
        self._current_stage_start: float = 0.0
        
        self._update_context()

    def set_correlation(self, generation_id: str, batch_id: str, niche: str):
        self.generation_id = generation_id
        self.batch_id = batch_id
        self.niche = niche
        self._update_context()

    def _update_context(self):
        ctx = {
            "run_id": self.run_id,
            "engine_version": getattr(version, "ENGINE_VERSION", "unknown"),
            "pipeline_version": getattr(version, "PIPELINE_VERSION", "unknown"),
            "schema_version": getattr(version, "SCHEMA_VERSION", "unknown"),
        }
        if self.workflow_id:
            ctx["workflow_id"] = self.workflow_id
        if self.generation_id:
            ctx["generation_id"] = self.generation_id
        if self.batch_id:
            ctx["batch_id"] = self.batch_id
        if self.niche:
            ctx["niche"] = self.niche
            
        correlation_context.set(ctx)

    def start_stage(self, stage_name: str):
        self._current_stage = stage_name
        self._current_stage_start = time.time()
        self._current_stage_start_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logging.getLogger(__name__).info(f"Starting stage: {stage_name}")

    def end_stage(self, status: str, error: Optional[str] = None):
        if not self._current_stage:
            return
            
        end_time = time.time()
        end_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
        duration_ms = int((end_time - self._current_stage_start) * 1000)
        
        stage_data = {
            "status": status,
            "started_at": self._current_stage_start_dt,
            "finished_at": end_dt,
            "duration_ms": duration_ms
        }
        if error:
            stage_data["error"] = error
            
        self.stages[self._current_stage] = stage_data
        
        level = logging.ERROR if status == "failed" else logging.INFO
        logging.getLogger(__name__).log(
            level, 
            f"Ended stage: {self._current_stage}", 
            extra={"stage": self._current_stage, "stage_status": status, "duration_ms": duration_ms}
        )
        self._current_stage = None

    def get_summary(self, final_status: str) -> Dict[str, Any]:
        total_duration_ms = int((time.time() - self.start_time) * 1000)
        
        summary = {
            "pipeline_version": "6.0.0",
            "engine_version": "HiddenDevTools Engine 1.0.0",
            "run_id": self.run_id,
            "status": final_status,
            "total_duration_ms": total_duration_ms,
            "stages": self.stages
        }
        
        if self.generation_id:
            summary["generation_id"] = self.generation_id
        if self.batch_id:
            summary["batch_id"] = self.batch_id
        if self.niche:
            summary["niche"] = self.niche
            
        summary["persistence_backend"] = getattr(config.runtime, "persistence_backend", "sqlite")
            
        return summary

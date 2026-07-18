import json
import uuid
import time
import logging
from services.observability import setup_logging, PipelineContext
from workers.reconciliation_worker import ReconciliationWorker

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    run_id = f"RECON_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    ctx = PipelineContext(run_id=run_id)
    logger.info("Starting Reconciliation Worker")
    
    worker = ReconciliationWorker()
    
    try:
        metrics = worker.run(ctx)
        final_status = "SUCCESS"
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        final_status = "FAILED"
        metrics = {}
        
    summary = ctx.get_summary(final_status)
    summary.update(metrics) # Merge the metrics directly into the summary output
    
    logger.info("Reconciliation Summary", extra={"reconciliation_summary": summary})
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()

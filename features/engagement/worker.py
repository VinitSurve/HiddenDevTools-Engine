import logging
from datetime import datetime, timedelta
from typing import Optional

from config.app_config import config
from features.engagement.repository import DeduplicationRepository
from services.instagram_service import InstagramService
from features.engagement.template_renderer import TemplateRenderer

logger = logging.getLogger(__name__)

class DMWorker:
    def __init__(self, repository: DeduplicationRepository, instagram_service: InstagramService):
        self.repository = repository
        self.instagram_service = instagram_service

    def process_queue(self):
        """
        Scans for pending or retryable comments and dispatches DMs.
        Fully idempotent and concurrency-safe thanks to repository's claim mechanics.
        """
        comments = self.repository.claim_pending_comments(config.runtime.scheduler.worker_batch_size)
        if not comments:
            return
            
        for comment in comments:
            try:
                # 1. Render Template
                text = TemplateRenderer.render_dm_template(comment.username)
                
                # 2. Send Message
                result = self.instagram_service.send_message(comment.instagram_user_id, text)
                
                # 3. Handle Result
                if result.success:
                    logger.info(f"DM_SENT: Successfully sent DM to {comment.username} for comment {comment.comment_id}")
                    self.repository.mark_sent(comment.comment_id)
                elif result.retryable and comment.attempt_count < config.runtime.retry.max_dm_retries:
                    next_attempt = comment.attempt_count + 1
                    # Exponential backoff: 30s, 60s, 120s...
                    backoff_seconds = 30 * (2 ** (next_attempt - 1))
                    next_retry_at = datetime.now() + timedelta(seconds=backoff_seconds)
                    
                    logger.warning(f"DM_FAILED_RETRY: Failed to send DM to {comment.username}. "
                                   f"Error: {result.error_message}. Retrying at {next_retry_at}.")
                    
                    self.repository.mark_retry(
                        comment.comment_id, 
                        result.error_message or "Unknown retryable error", 
                        next_attempt, 
                        next_retry_at
                    )
                else:
                    logger.error(f"DM_FAILED_PERMANENT: Failed to send DM to {comment.username}. "
                                 f"Error: {result.error_message}. Giving up.")
                    self.repository.mark_failed(
                        comment.comment_id, 
                        result.error_message or "Unknown fatal error"
                    )
            except Exception as e:
                logger.error(f"DMWorker Exception processing comment {comment.comment_id}: {e}", exc_info=True)
                # Fallback to retry if we crash unexpectedly before max retries
                if comment.attempt_count < config.runtime.retry.max_dm_retries:
                    next_attempt = comment.attempt_count + 1
                    next_retry_at = datetime.now() + timedelta(seconds=60)
                    self.repository.mark_retry(comment.comment_id, str(e), next_attempt, next_retry_at)
                else:
                    self.repository.mark_failed(comment.comment_id, str(e))

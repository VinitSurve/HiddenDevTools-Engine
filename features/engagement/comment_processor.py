import logging
from datetime import datetime
from settings import ENGAGEMENT_MODE, EngagementMode
from models.webhook_event import WebhookEvent
from features.engagement.repository import DeduplicationRepository
from features.engagement.models import ProcessedComment, DMStatus
from features.engagement.keyword_matcher import KeywordMatcher
from features.engagement.dispatcher import QueueDispatcher

logger = logging.getLogger(__name__)

class CommentProcessor:
    def __init__(self, repository: DeduplicationRepository, dispatcher: QueueDispatcher):
        self.repository = repository
        self.dispatcher = dispatcher
        self.matcher = KeywordMatcher()

    def process_event(self, event: WebhookEvent) -> None:
        """
        Orchestrates the engagement pipeline for a single comment.
        """
        correlation_id = event.correlation_id
        
        # 1. Deduplicate webhook event itself
        if self.repository.has_processed_comment(event.comment_id):
            logger.info(f"[{correlation_id}] DUPLICATE_WEBHOOK_SKIPPED: Already processed comment {event.comment_id}")
            return
            
        logger.info(f"[{correlation_id}] COMMENT_RECEIVED: {event.comment_id} from {event.username}")

        # 2. Prevent sending multiple DMs to the same user for the same post
        if self.repository.has_user_received_dm(event.user_id, event.media_id):
            logger.info(f"[{correlation_id}] DM_ALREADY_QUEUED: User {event.username} already engaged with post {event.media_id}")
            self._save_comment_record(event, event.text, "", None, DMStatus.FAILED)
            return

        # 3. Normalize the text
        original_text = event.text or ""
        normalized_text = self.matcher.normalize_text(original_text)
        logger.info(f"[{correlation_id}] COMMENT_NORMALIZED: '{normalized_text}'")

        # 4. Check if it matches our criteria
        matched_keyword = None
        should_queue = False
        
        if ENGAGEMENT_MODE == EngagementMode.ANY_COMMENT:
            if normalized_text: # Any non-empty comment
                should_queue = True
                logger.info(f"[{correlation_id}] ANY_COMMENT_MATCHED")
        else: # EngagementMode.KEYWORD
            matched_keyword = self.matcher.match_keyword(normalized_text)
            if matched_keyword:
                should_queue = True
                logger.info(f"[{correlation_id}] KEYWORD_MATCHED: '{matched_keyword}'")
            else:
                logger.info(f"[{correlation_id}] COMMENT_IGNORED: No keyword matched.")

        # 5. Save and Queue
        if should_queue:
            comment_record = self._save_comment_record(event, original_text, normalized_text, matched_keyword, DMStatus.PENDING)
            self.dispatcher.dispatch(comment_record.comment_id)
        else:
            self._save_comment_record(event, original_text, normalized_text, None, DMStatus.FAILED)

    def _save_comment_record(self, event: WebhookEvent, original_text: str, normalized_text: str, matched_keyword: str | None, status: DMStatus) -> ProcessedComment:
        record = ProcessedComment(
            comment_id=event.comment_id,
            media_id=event.media_id,
            instagram_user_id=event.user_id,
            username=event.username,
            original_text=original_text,
            normalized_text=normalized_text,
            matched_keyword=matched_keyword,
            status=status,
            created_at=datetime.now()
        )
        self.repository.save_processed_comment(record)
        return record

import hmac
import hashlib
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

from config.app_config import config
from models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)

class MetaWebhookService:
    """
    Business logic for Instagram/Meta webhooks.
    Responsible for validation, parsing, logging, and saving fixtures.
    """

    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str) -> str:
        """
        Validates the GET verification request from Meta.
        """
        if mode == "subscribe" and token == config.services.instagram.verify_token:
            logger.info("WEBHOOK_VERIFIED: Successfully verified Meta challenge.")
            return challenge
        logger.warning(f"WEBHOOK_VERIFY_FAILED: Invalid token '{token}' or mode '{mode}'.")
        raise ValueError("Invalid verification token")

    @staticmethod
    def validate_signature(payload_bytes: bytes, signature_header: str) -> bool:
        """
        Validates the X-Hub-Signature-256 header against the payload using META_APP_SECRET.
        """
        if not META_APP_SECRET:
            logger.error("WEBHOOK_SIGNATURE_INVALID: META_APP_SECRET is not configured.")
            return False

        if not signature_header or not signature_header.startswith("sha256="):
            logger.error("WEBHOOK_SIGNATURE_INVALID: Missing or malformed signature header.")
            return False

        signature = signature_header.split("sha256=")[1]
        
        expected_hash = hmac.new(
            key=config.services.instagram.app_secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(expected_hash, signature)
        if not is_valid:
            if config.runtime.scheduler.app_env == "development":
                logger.warning(f"WEBHOOK_SIGNATURE_MISMATCH: Expected: {expected_hash}, Got: {signature}. Bypassing for development.")
                return True
            else:
                logger.warning(f"WEBHOOK_SIGNATURE_MISMATCH: Invalid signature in non-development environment.")
                return False
        
        return True

    @staticmethod
    def _save_for_replay(payload_dict: Dict[str, Any], correlation_id: str) -> None:
        """
        Saves incoming raw payloads to fixtures/webhooks/YYYY/MM/ for future offline development.
        """
        try:
            now = datetime.now()
            year_month_path = os.path.join("fixtures", "webhooks", now.strftime("%Y"), now.strftime("%m"))
            os.makedirs(year_month_path, exist_ok=True)
            
            filename = f"event_{now.strftime('%Y%m%d_%H%M%S')}_{correlation_id}.json"
            filepath = os.path.join(year_month_path, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload_dict, f, indent=2)
            
            logger.info(f"[{correlation_id}] Payload saved for replay at: {filepath}")
        except Exception as e:
            logger.error(f"[{correlation_id}] Failed to save payload for replay: {e}")

    @staticmethod
    def parse_payload(payload_dict: Dict[str, Any], correlation_id: str) -> List[WebhookEvent]:
        """
        Extracts Comment ID, Media ID, User ID, Username, and Text into a list of WebhookEvent models.
        Meta can batch multiple entries and changes into a single payload.
        """
        events = []
        object_type = payload_dict.get("object", "unknown")
        
        for entry in payload_dict.get("entry", []):
            entry_id = entry.get("id")
            for change in entry.get("changes", []):
                field = change.get("field", "unknown")
                value = change.get("value", {})
                
                # We currently only parse comments, but structure is ready for messages/mentions
                comment_id = value.get("id")
                media_id = value.get("media", {}).get("id")
                from_user = value.get("from", {})
                user_id = from_user.get("id")
                username = from_user.get("username")
                text = value.get("text")
                timestamp_unix = value.get("created_time")
                
                dt_timestamp = datetime.fromtimestamp(timestamp_unix) if timestamp_unix else datetime.now()
                
                event = WebhookEvent(
                    object_type=object_type,
                    event_type=field,
                    webhook_id=entry_id or "unknown",
                    correlation_id=correlation_id,
                    comment_id=comment_id,
                    media_id=media_id,
                    user_id=user_id,
                    username=username,
                    text=text,
                    timestamp=dt_timestamp,
                    raw_payload=change
                )
                events.append(event)
                
        return events

    def receive_event(self, payload_dict: Dict[str, Any], correlation_id: str, background_tasks) -> None:
        """
        The main orchestration method that parses the payload, logs it, and routes it to handlers.
        """
        self._save_for_replay(payload_dict, correlation_id)
        
        try:
            events = self.parse_payload(payload_dict, correlation_id)
            if not events:
                logger.warning(f"[{correlation_id}] WEBHOOK_PARSE_FAILED: No valid changes found in payload.")
                return

            for event in events:
                logger.info(
                    f"[{correlation_id}] WEBHOOK_RECEIVED: "
                    f"type={event.event_type} object={event.object_type} "
                    f"comment_id={event.comment_id} media_id={event.media_id} "
                    f"user={event.username} text='{event.text}'"
                )
                
                # Route to engagement feature
                if event.event_type == "comments" or event.event_type == "live_comments":
                    from features.engagement.repository import DeduplicationRepository
                    from features.engagement.comment_processor import CommentProcessor
                    from features.engagement.dispatcher import FastAPIDispatcher
                    
                    repo = DeduplicationRepository()
                    dispatcher = FastAPIDispatcher(background_tasks)
                    processor = CommentProcessor(repo, dispatcher)
                    processor.process_event(event)
                else:
                    logger.info(f"[{correlation_id}] Ignoring unsupported event type: {event.event_type}")
                
        except Exception as e:
            logger.error(f"[{correlation_id}] WEBHOOK_PARSE_FAILED: Exception during parsing: {e}", exc_info=True)

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class WebhookEvent:
    """
    Structured model for incoming Meta webhook events.
    Every downstream module should consume this instead of raw JSON.
    """
    object_type: str
    event_type: str  # e.g. "comments", "messages"
    webhook_id: str  # Unique ID for the webhook delivery (often extracted from headers or generated)
    correlation_id: str
    
    # Event specific fields
    comment_id: Optional[str] = None
    media_id: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    text: Optional[str] = None
    
    timestamp: Optional[datetime] = None
    raw_payload: Optional[Dict[str, Any]] = None

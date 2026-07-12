from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class DMStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRYING = "RETRYING"
    SENT = "SENT"
    FAILED = "FAILED"

@dataclass
class ProcessedComment:
    comment_id: str
    media_id: str
    instagram_user_id: str
    username: str
    original_text: str
    normalized_text: str
    matched_keyword: Optional[str]
    status: DMStatus
    created_at: datetime
    attempt_count: int = 0
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None

@dataclass
class MessageResult:
    success: bool
    message_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    retryable: bool
    http_status: Optional[int]
    raw_response: Optional[str]

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class PublishResult:
    success: bool
    provider: str
    provider_post_id: Optional[str] = None
    provider_container_id: Optional[str] = None
    published_at: Optional[str] = None
    permalink: Optional[str] = None
    attempt_count: int = 1
    provider_response: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

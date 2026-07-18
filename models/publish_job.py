from dataclasses import dataclass, field
from typing import List
from models.artifact import Artifact

@dataclass
class PublishJob:
    generation_id: str
    batch_id: str
    date: str
    weekday: int
    niche: str
    sheet_name: str
    caption: str
    hashtags: List[str]
    artifacts: List[Artifact] = field(default_factory=list)
    status: str = "ORCHESTRATED"

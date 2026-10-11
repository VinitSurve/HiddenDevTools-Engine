from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict

@dataclass
class BasePayload:
    id: str
    slide_number: int
    status: str
    generation_id: Optional[str] = None
    post: Optional[str] = None
    generated_at: Optional[str] = None
    published_at: Optional[str] = None
    row_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GithubRepoPayload(BasePayload):
    resource_name: str = ""
    link: str = ""
    short_description: str = ""
    pricing: str = ""
    difficulty: str = ""
    why_it_matters: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    rating: str = ""

@dataclass
class PromptPayload(BasePayload):
    prompt_title: str = ""
    prompt_number: str = ""
    prompt: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    expected_output: str = ""
    short_description: Optional[str] = None

@dataclass
class ToolsWebsitesPayload(BasePayload):
    tool_name: str = ""
    website: str = ""
    short_description: str = ""
    category: str = ""
    pricing: str = ""
    platform: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    rating: str = ""
    why_it_matters: Optional[str] = None

@dataclass
class DeveloperToolsPayload(BasePayload):
    tool_name: str = ""
    website: str = ""
    category: str = ""
    license: str = ""
    short_description: str = ""
    why_developers_love_it: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    rating: str = ""

@dataclass
class FreeAlternativePayload(BasePayload):
    alternative_name: str = ""
    replaces: str = ""
    website: str = ""
    pricing: str = ""
    category: str = ""
    why_switch: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    rating: str = ""

@dataclass
class CareerResourcePayload(BasePayload):
    resource_name: str = ""
    website: str = ""
    category: str = ""
    free_paid: str = ""
    best_for_1: str = ""
    best_for_2: str = ""
    best_for_3: str = ""
    why_use_it: str = ""
    rating: str = ""

@dataclass
class WeeklyRoundupPayload(BasePayload):
    # A generic payload for Weekly Roundup
    title: str = ""
    description: str = ""
    link: str = ""
    category: str = ""


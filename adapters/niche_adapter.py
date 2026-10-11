import logging
from typing import List, Dict, Any
from models.niche_payloads import (
    BasePayload,
    GithubRepoPayload,
    PromptPayload,
    ToolsWebsitesPayload,
    DeveloperToolsPayload,
    FreeAlternativePayload,
    CareerResourcePayload,
    WeeklyRoundupPayload,
)

logger = logging.getLogger(__name__)

class NicheAdapter:
    @staticmethod
    def adapt_rows(sheet_name: str, rows: List[Dict[str, Any]]) -> List[BasePayload]:
        """
        Adapt external Google Sheet row dictionaries exactly to internal typed dataclass payloads.
        Enforces exact mapping rules and handles null/excluded column mappings per niche.
        """
        adapted = []
        for idx, row in enumerate(rows):
            try:
                slide_num_raw = row.get("Slide Number", 0)
                slide_num = int(slide_num_raw) if slide_num_raw is not None and str(slide_num_raw).strip() != "" else 0
            except (ValueError, TypeError):
                slide_num = 0

            id_val = str(row.get("ID", "")).strip()
            status_val = str(row.get("Status", "")).strip()
            gen_id_val = str(row.get("Generation ID", "")).strip() or None
            post_val = str(row.get("Post", "")).strip() or None
            gen_at_val = str(row.get("Generated At", "")).strip() or None
            pub_at_val = str(row.get("Published At", "")).strip() or None
            row_idx = row.get("_row", idx + 2)

            base_kwargs = {
                "id": id_val,
                "slide_number": slide_num,
                "status": status_val,
                "generation_id": gen_id_val,
                "post": post_val,
                "generated_at": gen_at_val,
                "published_at": pub_at_val,
                "row_index": row_idx,
            }

            if sheet_name == "Github Repos":
                payload = GithubRepoPayload(
                    **base_kwargs,
                    resource_name=str(row.get("Resource Name", "")),
                    link=str(row.get("Link", "")),
                    short_description=str(row.get("Short Description", "")),
                    pricing=str(row.get("Pricing", "")),
                    difficulty=str(row.get("Difficulty", "")),
                    why_it_matters=str(row.get("Why it Matters", "")),
                    best_for_1=str(row.get("Best for 1", "")),
                    best_for_2=str(row.get("Best for 2", "")),
                    best_for_3=str(row.get("Best for 3", "")),
                    rating=str(row.get("Rating", "")),
                )
            elif sheet_name == "Prompt Library":
                payload = PromptPayload(
                    **base_kwargs,
                    prompt_title=str(row.get("Prompt Title", "")),
                    prompt_number=str(row.get("Prompt Number", "")),
                    prompt=str(row.get("Prompt", "")),
                    best_for_1=str(row.get("Best For 1", "")),
                    best_for_2=str(row.get("Best For 2", "")),
                    best_for_3=str(row.get("Best For 3", "")),
                    expected_output=str(row.get("Expected Output", "")),
                    short_description=None,
                )
            elif sheet_name == "Tools & Websites":
                payload = ToolsWebsitesPayload(
                    **base_kwargs,
                    tool_name=str(row.get("Tool Name", "")),
                    website=str(row.get("Website", "")),
                    short_description=str(row.get("Short Description", "")),
                    category=str(row.get("Category", "")),
                    pricing=str(row.get("Pricing", "")),
                    platform=str(row.get("Platform", "")),
                    best_for_1=str(row.get("Best for 1", "")),
                    best_for_2=str(row.get("Best for 2", "")),
                    best_for_3=str(row.get("Best for 3", "")),
                    rating=str(row.get("Rating", "")),
                    why_it_matters=None,
                )
            elif sheet_name == "Developer Tools":
                payload = DeveloperToolsPayload(
                    **base_kwargs,
                    tool_name=str(row.get("Tool Name", "")),
                    website=str(row.get("Website", "")),
                    category=str(row.get("Category", "")),
                    license=str(row.get("License", "")),
                    short_description=str(row.get("Short Description", "")),
                    why_developers_love_it=str(row.get("Why Developers Love it", "")),
                    best_for_1=str(row.get("Best for 1", "")),
                    best_for_2=str(row.get("Best for 2", "")),
                    best_for_3=str(row.get("Best for 3", "")),
                    rating=str(row.get("Rating", "")),
                )
            elif sheet_name == "Free Alternatives":
                payload = FreeAlternativePayload(
                    **base_kwargs,
                    alternative_name=str(row.get("Alternative Name", "")),
                    replaces=str(row.get("Replaces", "")),
                    website=str(row.get("Website", "")),
                    pricing=str(row.get("Pricing", "")),
                    category=str(row.get("Category", "")),
                    why_switch=str(row.get("Why Switch", "")),
                    best_for_1=str(row.get("Best For 1", "")),
                    best_for_2=str(row.get("Best For 2", "")),
                    best_for_3=str(row.get("Best For 3", "")),
                    rating=str(row.get("Rating", "")),
                )
            elif sheet_name == "Career Resources":
                payload = CareerResourcePayload(
                    **base_kwargs,
                    resource_name=str(row.get("Resource Name", "")),
                    website=str(row.get("Website", "")),
                    category=str(row.get("Category", "")),
                    free_paid=str(row.get("Free/Paid", "")),
                    best_for_1=str(row.get("Best For 1", "")),
                    best_for_2=str(row.get("Best For 2", "")),
                    best_for_3=str(row.get("Best For 3", "")),
                    why_use_it=str(row.get("Why Use It", "")),
                    rating=str(row.get("Rating", "")),
                )
            elif sheet_name == "Weekly Roundup":
                payload = WeeklyRoundupPayload(
                    **base_kwargs,
                    title=str(row.get("Title", "")),
                    description=str(row.get("Description", "")),
                    link=str(row.get("Link", "")),
                    category=str(row.get("Category", "")),
                )
            else:
                raise ValueError(f"Unsupported sheet_name for NicheAdapter: '{sheet_name}'")

            adapted.append(payload)
        return adapted

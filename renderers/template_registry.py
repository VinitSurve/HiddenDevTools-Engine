import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

TEMPLATE_MAP = {
    "github_repo": {
        "cover": "templates/Github_Master_Cover.png",
        "content": "templates/Github_Content_Slide_Template.jpg",
        "cta": "templates/Github_Last_Page.png",
        "renderer_module": "renderers.github_repo",
        "renderer_class": "GithubRepoRenderer"
    },
    "tools_websites": {
        "cover": "templates/Tools & Websites Cover Template.png",
        "content": "templates/Tools & Websites Content Template.png",
        "cta": "templates/CTA.png",
        "renderer_module": "renderers.tools_websites",
        "renderer_class": "ToolsWebsitesRenderer"
    },
    "developer_tools": {
        "cover": "templates/Developer_Tools_Cover_Page.png",
        "content": "templates/Developer_Tools_Content_Template.png",
        "cta": "templates/CTA.png",
        "renderer_module": "renderers.developer_tools_renderer",
        "renderer_class": "DeveloperToolsRenderer"
    },
    "prompt_library": {
        "cover": "templates/Prompt Library Cover Page.png",
        "content": "templates/Prompt Library Content Template.png",
        "cta": "templates/CTA.png",
        "renderer_module": "renderers.prompt_library",
        "renderer_class": "PromptLibraryRenderer"
    },
    "free_alternatives": {
        "cover": "templates/Free Alternatives Cover Page.png",
        "content": "templates/Free Alternatives Content template.png",
        "cta": "templates/CTA.png",
        "renderer_module": "renderers.free_alternatives",
        "renderer_class": "FreeAlternativesRenderer"
    },
    "career_resources": {
        "cover": "templates/Career Resources Cover Page.png",
        "content": "templates/Career Resource Content template.png",
        "cta": "templates/CTA.png",
        "renderer_module": "renderers.career_resources",
        "renderer_class": "CareerResourcesRenderer"
    }
}

class TemplateRegistry:
    @staticmethod
    def get_template_paths(template_key: str) -> Dict[str, str]:
        """Return exact cover, content, and cta asset paths for the given template_key."""
        key_clean = str(template_key).strip()
        if key_clean not in TEMPLATE_MAP:
            logger.error(f"INVALID_TEMPLATE_KEY: Unknown template key '{key_clean}'.")
            raise KeyError(f"Unknown template_key: {key_clean}")
        info = TEMPLATE_MAP[key_clean]
        return {
            "cover": info["cover"],
            "content": info["content"],
            "cta": info["cta"]
        }

    @staticmethod
    def get_renderer_class(template_key: str) -> Optional[Any]:
        """Dynamically import and return target renderer class for the given template_key."""
        key_clean = str(template_key).strip()
        if key_clean not in TEMPLATE_MAP:
            logger.error(f"INVALID_TEMPLATE_KEY: Unknown template key '{key_clean}'.")
            raise KeyError(f"Unknown template_key: {key_clean}")
        info = TEMPLATE_MAP[key_clean]
        try:
            mod = __import__(info["renderer_module"], fromlist=[info["renderer_class"]])
            return getattr(mod, info["renderer_class"], None)
        except Exception as e:
            logger.warning(f"Could not import renderer {info['renderer_class']} from {info['renderer_module']}: {e}")
            return None

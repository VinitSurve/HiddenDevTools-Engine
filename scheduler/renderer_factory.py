from renderers.github_repo import GithubRepoRenderer
from renderers.tools_websites import ToolsWebsitesRenderer
from renderers.developer_tools_renderer import DeveloperToolsRenderer
from renderers.prompt_library import PromptLibraryRenderer
from renderers.free_alternatives import FreeAlternativesRenderer
from renderers.career_resources import CareerResourcesRenderer
from renderers.base_renderer import BaseRenderer

class RendererFactory:
    @staticmethod
    def get_renderer(niche: str, templates_dir: str) -> BaseRenderer:
        registry = {
            "github_repo": GithubRepoRenderer,
            "tools_websites": ToolsWebsitesRenderer,
            "developer_tools": DeveloperToolsRenderer,
            "prompt_library": PromptLibraryRenderer,
            "free_alternatives": FreeAlternativesRenderer,
            "career_resources": CareerResourcesRenderer,
        }
        renderer_cls = registry.get(niche)
        if not renderer_cls:
            raise ValueError(f"Unknown niche: {niche}")
        return renderer_cls(templates_dir)

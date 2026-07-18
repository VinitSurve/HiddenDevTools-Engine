import os
import pytest
from PIL import Image

from renderers.career_resources import CareerResourcesRenderer
from renderers.developer_tools_renderer import DeveloperToolsRenderer
from renderers.free_alternatives import FreeAlternativesRenderer
from renderers.github_repo import GithubRepoRenderer
from renderers.prompt_library import PromptLibraryRenderer
from renderers.tools_websites import ToolsWebsitesRenderer

@pytest.fixture
def templates_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))

def test_renderer_instantiation_and_contract(templates_dir):
    renderers = [
        CareerResourcesRenderer,
        DeveloperToolsRenderer,
        FreeAlternativesRenderer,
        GithubRepoRenderer,
        PromptLibraryRenderer,
        ToolsWebsitesRenderer
    ]
    
    for cls in renderers:
        renderer = cls(templates_dir)
        assert renderer.TARGET_WIDTH == 1173
        assert renderer.TARGET_HEIGHT == 1341
        assert "Slide Number" in renderer.regions

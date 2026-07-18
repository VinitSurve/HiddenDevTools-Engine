import os
import pytest

from renderers.career_resources import CareerResourcesRenderer
from renderers.developer_tools_renderer import DeveloperToolsRenderer
from renderers.free_alternatives import FreeAlternativesRenderer
from renderers.github_repo import GithubRepoRenderer
from renderers.prompt_library import PromptLibraryRenderer
from renderers.tools_websites import ToolsWebsitesRenderer

from config.renderer_layouts.career_resources import REGIONS as CR_REGIONS
from config.renderer_layouts.developer_tools import REGIONS as DT_REGIONS
from config.renderer_layouts.free_alternatives import REGIONS as FA_REGIONS
from config.renderer_layouts.github_repo import REGIONS as GR_REGIONS
from config.renderer_layouts.prompt_library import REGIONS as PL_REGIONS
from config.renderer_layouts.tools_websites import REGIONS as TW_REGIONS

@pytest.fixture
def templates_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))

def test_renderer_loads_specific_config(templates_dir):
    # Test that each renderer loads its own configuration correctly
    
    cr_renderer = CareerResourcesRenderer(templates_dir)
    assert cr_renderer.regions == CR_REGIONS
    
    dt_renderer = DeveloperToolsRenderer(templates_dir)
    assert dt_renderer.regions == DT_REGIONS
    
    fa_renderer = FreeAlternativesRenderer(templates_dir)
    assert fa_renderer.regions == FA_REGIONS
    
    gr_renderer = GithubRepoRenderer(templates_dir)
    assert gr_renderer.regions == GR_REGIONS
    
    pl_renderer = PromptLibraryRenderer(templates_dir)
    assert pl_renderer.regions == PL_REGIONS
    
    tw_renderer = ToolsWebsitesRenderer(templates_dir)
    assert tw_renderer.regions == TW_REGIONS

    # Validate that they are distinct (e.g. Prompt Library is not Career Resources)
    assert PL_REGIONS is not CR_REGIONS
    assert DT_REGIONS is not FA_REGIONS

import pytest
from PIL import Image, ImageFont, ImageDraw
import os
import inspect

from renderers.base_renderer import BaseRenderer, RendererTextOverflowError, LayoutRegion
from renderers.github_repo import GithubRepoRenderer
from renderers.tools_websites import ToolsWebsitesRenderer
from renderers.developer_tools_renderer import DeveloperToolsRenderer
from renderers.prompt_library import PromptLibraryRenderer
from renderers.free_alternatives import FreeAlternativesRenderer
from renderers.career_resources import CareerResourcesRenderer

def setup_synthetic_templates(tmp_path, covers, contents, ctas):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    img = Image.new('RGB', (1173, 1341))
    
    for name in covers + contents + ctas:
        img.save(templates_dir / name)
    return str(templates_dir)

@pytest.fixture
def templates_dir(tmp_path):
    covers = [
        "Github_Master_Cover.png", "Tools & Websites Cover Template.png", 
        "Developer_Tools_Cover_Page.png", "Prompt Library Cover Page.png", 
        "Free Alternatives Cover Page.png", "Career Resources Cover Page.png"
    ]
    contents = [
        "Github_Content_Slide_Template.jpg", "Tools & Websites Content Template.png",
        "Developer_Tools_Content_Template.png", "Prompt Library Content Template.png",
        "Free Alternatives Content template.png", "Career Resource Content template.png"
    ]
    ctas = ["CTA.png", "Github_Last_Page.png"]
    return setup_synthetic_templates(tmp_path, covers, contents, ctas)

@pytest.fixture(autouse=True)
def mock_fonts(monkeypatch):
    class DummyFont:
        def __init__(self, size):
            self.size = size
            
        def getmetrics(self):
            return (self.size, self.size // 4)
            
    def mock_load_font(self, font_path, size):
        if not font_path.endswith(".ttf") or "invalid" in font_path:
            raise FileNotFoundError(f"Required font not found: {font_path}")
        return DummyFont(size)
        
    def mock_textbbox(self, xy, text, font=None, *args, **kwargs):
        # Deterministic width: size/2 pixels per char. Height: size pixels.
        if font is None:
            size = 10
        else:
            size = font.size
        width = len(text) * (size // 2)
        return (xy[0], xy[1], xy[0] + width, xy[1] + size)
        
    def mock_text(self, *args, **kwargs):
        pass # Do nothing when actually trying to draw the text, as we don't have a real font
        
    monkeypatch.setattr(BaseRenderer, "_load_font", mock_load_font)
    monkeypatch.setattr(ImageDraw.ImageDraw, "textbbox", mock_textbbox)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", mock_text)

def test_base_renderer_dimensions(tmp_path):
    renderer = BaseRenderer(str(tmp_path))
    img = Image.new('RGB', (100, 100))
    img.save(tmp_path / "invalid.png")
    
    with pytest.raises(ValueError, match="violates strict dimension contract"):
        renderer.open_template("invalid.png")

def test_exact_seven_payloads(templates_dir, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    renderer = GithubRepoRenderer(templates_dir)
    
    with pytest.raises(ValueError, match="Exactly 7 payloads are required"):
        renderer.render([{"Resource Name": "A"}] * 6, str(out_dir), "GEN1")
        
    with pytest.raises(ValueError, match="Exactly 7 payloads are required"):
        renderer.render([{"Resource Name": "A"}] * 8, str(out_dir), "GEN1")

def test_exact_nine_artifacts_and_dimensions(templates_dir, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    renderer = GithubRepoRenderer(templates_dir)
    
    payloads = [{"Resource Name": f"Repo {i}"} for i in range(7)]
    files = renderer.render(payloads, str(out_dir), "GEN1")
    
    assert len(files) == 9
    expected_names = [
        "01_Cover.png", "02_Content.png", "03_Content.png", "04_Content.png",
        "05_Content.png", "06_Content.png", "07_Content.png", "08_Content.png", "09_CTA.png"
    ]
    
    for f, expected in zip(files, expected_names):
        assert os.path.basename(f) == expected
        img = Image.open(f)
        assert img.width == 1173
        assert img.height == 1341
        img.close()

def test_typography_logic(templates_dir, tmp_path, monkeypatch):
    renderer = BaseRenderer(templates_dir)
    font_path = "valid.ttf"
    
    img = Image.new('RGB', (1173, 1341))
    draw = ImageDraw.Draw(img)
    
    # Test 1: Deterministic wrapping
    # size=20 -> 10px per char. max_width=100 -> 10 chars max per line.
    region = LayoutRegion("Wrap Test", 0, 0, 100, 100, 20, 20, font_path, max_lines=10)
    # "Hello" (50px), "world" (50px), "test" (40px)
    renderer.draw_field(draw, "Hello world test", region)
    
    # Test 2: Font-size reduction
    # size=40 -> 20px per char. "A long text" (11 chars) -> 220px. max_width=100.
    # To fit 11 chars in 100px width, char width must be <= 9px -> size <= 18px.
    # min_font_size = 10. So it should reduce to 18.
    region_reduce = LayoutRegion("Reduce", 0, 0, 100, 50, 40, 10, font_path, max_lines=1)
    renderer.draw_field(draw, "A long text", region_reduce)
    
    # Test 3: Unresolved text overflow
    # size=40 -> min_size=30 (15px per char). max_width=100. Max chars=6.
    # text="A very long text that must shrink". len=33. Needs 33*15=495px width.
    # Will fail!
    region_fail = LayoutRegion("Fail", 0, 0, 100, 50, 40, 30, font_path, max_lines=1)
    with pytest.raises(RendererTextOverflowError):
        renderer.draw_field(draw, "A very long text that must shrink", region_fail)
    
def test_missing_font_fails_closed(templates_dir, tmp_path):
    renderer = BaseRenderer(templates_dir)
    img = Image.new('RGB', (1173, 1341))
    draw = ImageDraw.Draw(img)
    
    region = LayoutRegion("Missing Font", 0, 0, 100, 100, 20, 20, "invalid_font.ttf")
    with pytest.raises(FileNotFoundError):
        renderer.draw_field(draw, "Test", region)

def test_no_network_imports():
    import renderers.github_repo
    source = inspect.getsource(renderers.github_repo)
    assert "import requests" not in source
    assert "import urllib" not in source

@pytest.mark.parametrize("renderer_class, expected_fields", [
    (GithubRepoRenderer, ["Resource Name", "Link", "Short Description", "Pricing", "Difficulty", "Slide Number", "Why it Matters", "Best for 1", "Best for 2", "Best for 3", "Rating"]),
    (ToolsWebsitesRenderer, ["Tool Name", "Website", "Short Description", "Category", "Pricing", "Platform", "Best for 1", "Best for 2", "Best for 3", "Rating", "Slide Number"]),
    (DeveloperToolsRenderer, ["Tool Name", "Website", "Category", "License", "Slide Number", "Short Description", "Why Developers Love it", "Best for 1", "Best for 2", "Best for 3", "Rating"]),
    (PromptLibraryRenderer, ["Prompt Title", "Slide Number", "Prompt Number", "Prompt", "Best For 1", "Best For 2", "Best For 3", "Expected Output"]),
    (FreeAlternativesRenderer, ["Alternative Name", "Replaces", "Website", "Pricing", "Category", "Slide Number", "Why Switch", "Best For 1", "Best For 2", "Best For 3", "Rating"]),
    (CareerResourcesRenderer, ["Resource Name", "Website", "Category", "Free/Paid", "Slide Number", "Best For 1", "Best For 2", "Best For 3", "Why Use It", "Rating"])
])
def test_all_renderers_consume_exact_payloads(templates_dir, tmp_path, renderer_class, expected_fields):
    renderer = renderer_class(templates_dir)
    assert set(renderer.regions.keys()) == set(expected_fields)
    
    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    
    payloads = [{f: "Val" for f in expected_fields}] * 7
    files = renderer.render(payloads, str(out_dir), "GEN1")
    assert len(files) == 9

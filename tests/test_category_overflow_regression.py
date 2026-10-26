import os
import pytest
from PIL import Image, ImageDraw, ImageFont

from renderers.career_resources import CareerResourcesRenderer
from renderers.base_renderer import RendererTextOverflowError, LayoutRegion
from config.renderer_layouts.career_resources import REGIONS as CR_REGIONS

@pytest.fixture
def templates_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))

@pytest.fixture
def career_renderer(templates_dir):
    return CareerResourcesRenderer(templates_dir)

def test_devpost_category_overflow_regression(career_renderer, tmp_path):
    """
    Regression test for Saturday scheduled run failure (incident run 40113423004).
    Row 14: Devpost with Category 'Developer Challenges' must render without overflow.
    """
    devpost_payload = {
        "resource_name": "Devpost",
        "website": "devpost.com",
        "category": "Developer Challenges",
        "free_paid": "Free",
        "best_for_1": "Hackathons",
        "best_for_2": "Project Showcases",
        "best_for_3": "Coding Competitions",
        "why_use_it": "The home for hackathons, discover online and in-person hackathons and submit projects.",
        "rating": "4.8",
        "niche": "career_resources",
        "generation_id": "REGRESSION_TEST"
    }

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    files = career_renderer.render([devpost_payload] * 7, str(out_dir), "REGRESSION_TEST")
    assert len(files) == 9
    for f in files:
        assert os.path.exists(f)
        with Image.open(f) as img:
            assert img.size == (1173, 1341)

@pytest.mark.parametrize("category", [
    "Career Planning",
    "Career Roadmap",
    "Certifications",
    "Coding Practice",
    "Company Research",
    "Developer Challenges",
    "Developer Community",
    "Freelancing",
    "Internships",
    "Interview Prep",
    "Job Board",
    "Learning Platform",
    "Mentorship",
    "Networking",
    "Open Source",
    "Other",
    "Portfolio",
    "Remote Jobs",
    "Resume Builder",
    "Salary Research",
    "System Design",
    "Technical Writing",
])
def test_all_career_resources_categories_fit(career_renderer, category):
    """
    All 22 production categories present in the Career Resources worksheet
    must render without overflow error.
    """
    region = career_renderer.regions["category"]
    img = Image.new("RGB", (1173, 1341))
    draw = ImageDraw.Draw(img)

    # Must not raise RendererTextOverflowError
    career_renderer.draw_field(draw, category, region)

@pytest.mark.parametrize("long_category", [
    "Full-Stack Web Development",      # 26 chars
    "Developer Productivity Tools",   # 28 chars
    "Cloud Architecture & DevOps",    # 27 chars
    "Artificial Intelligence Tools",   # 29 chars
])
def test_unusually_long_category_labels_fit(career_renderer, long_category):
    """
    Unusually long category labels must scale down to fit without clipping or overflow.
    """
    region = career_renderer.regions["category"]
    img = Image.new("RGB", (1173, 1341))
    draw = ImageDraw.Draw(img)

    career_renderer.draw_field(draw, long_category, region)

def test_extreme_category_overflow_fails_closed(career_renderer):
    """
    Text that exceeds even the minimum font size must raise RendererTextOverflowError
    rather than silently clipping or corrupting output.
    """
    region = career_renderer.regions["category"]
    img = Image.new("RGB", (1173, 1341))
    draw = ImageDraw.Draw(img)

    extreme_text = "This Is An Extremely Long And Unrealistic Category Name That Cannot Fit In Any Pill"
    with pytest.raises(RendererTextOverflowError, match="overflows and cannot fit"):
        career_renderer.draw_field(draw, extreme_text, region)

def test_whitespace_normalization(career_renderer):
    """
    Irregular leading/trailing/internal whitespace must be normalized safely
    without altering the underlying text meaning.
    """
    region = career_renderer.regions["category"]
    img = Image.new("RGB", (1173, 1341))
    draw = ImageDraw.Draw(img)

    # Input with excessive spaces
    career_renderer.draw_field(draw, "   Developer    Challenges   ", region)

def test_rendered_text_bounding_box_within_pill(career_renderer):
    """
    Verify text bounding box strictly stays within the blue pill boundaries.
    The blue pill is situated from x=673 to x=853 (width 180px).
    """
    region = career_renderer.regions["category"]
    PILL_LEFT = 673
    PILL_RIGHT = 853

    for category in ["Freelancing", "Developer Challenges", "Developer Community", "Company Research"]:
        # Measure text using base_renderer font resolution
        current_size = region.preferred_font_size
        font = None
        while current_size >= region.minimum_font_size:
            f = career_renderer._load_font(region.font_path, current_size)
            lines = career_renderer.wrap_text(category, f, ImageDraw.Draw(Image.new("RGB", (1, 1))), region.max_width)
            if len(lines) <= region.max_lines:
                bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), lines[0], font=f)
                if (bbox[2] - bbox[0]) <= region.max_width:
                    font = f
                    break
            current_size -= 1

        assert font is not None, f"Font could not be resolved for category: {category}"
        bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), category, font=font)
        text_width = bbox[2] - bbox[0]

        # Region is centered
        x_offset = region.x + (region.max_width - text_width) // 2
        text_left = x_offset
        text_right = x_offset + text_width

        assert text_left >= PILL_LEFT, f"{category} left edge ({text_left}) overflows pill left ({PILL_LEFT})"
        assert text_right <= PILL_RIGHT, f"{category} right edge ({text_right}) overflows pill right ({PILL_RIGHT})"

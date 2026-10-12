import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "prompt_title": LayoutRegion("prompt_title", 190, 280, 1080, 60, 40, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 140, 45, 20, 40, 30, 16, FONT_PATH, "left", 6),
    "prompt_number": LayoutRegion("prompt_number", 80, 290, 100, 40, 30, 16, FONT_PATH, "left", 6),
    "prompt": LayoutRegion("prompt", 200, 530, 920, 265, 28, 16, FONT_PATH, "left", 6),
    "best_for_1": LayoutRegion("best_for_1", 190, 930, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_2": LayoutRegion("best_for_2", 190, 970, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_3": LayoutRegion("best_for_3", 190, 1010, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "expected_output": LayoutRegion("expected_output", 660, 930, 455, 160, 25, 16, FONT_PATH, "left", 6)
}

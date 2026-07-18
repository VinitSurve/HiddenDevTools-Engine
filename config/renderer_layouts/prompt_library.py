import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Prompt Title": LayoutRegion("Prompt Title", 190, 280, 1080, 60, 40, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 140, 45, 20, 40, 30, 16, FONT_PATH, "left", 6),
    "Prompt Number": LayoutRegion("Prompt Number", 80, 290, 100, 40, 30, 16, FONT_PATH, "left", 6),
    "Prompt": LayoutRegion("Prompt", 200, 530, 920, 265, 28, 16, FONT_PATH, "left", 6),
    "Best For 1": LayoutRegion("Best For 1", 190, 930, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 2": LayoutRegion("Best For 2", 190, 970, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 3": LayoutRegion("Best For 3", 190, 1010, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Expected Output": LayoutRegion("Expected Output", 660, 930, 455, 160, 25, 16, FONT_PATH, "left", 6)
}

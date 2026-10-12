import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "alternative_name": LayoutRegion("alternative_name", 64, 222, 973, 50, 45, 25, FONT_PATH, "left", 6),
    "replaces": LayoutRegion("replaces", 77, 854, 1068, 54, 23, 16, FONT_PATH, "left", 6),
    "website": LayoutRegion("website", 111, 300, 450, 87, 25, 16, FONT_PATH, "left", 6),
    "pricing": LayoutRegion("pricing", 1037, 1003, 100, 30, 19.5, 12, FONT_PATH, "left", 6),
    "category": LayoutRegion("category", 840, 1002, 280, 30, 19.5, 14, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 141, 45, 20, 70, 32, 16, FONT_PATH, "left", 6),
    "why_switch": LayoutRegion("why_switch", 870, 487, 270, 103, 25, 16, FONT_PATH, "left", 6),
    "best_for_1": LayoutRegion("best_for_1", 908, 726, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_2": LayoutRegion("best_for_2", 908, 770, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_3": LayoutRegion("best_for_3", 908, 812, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "rating": LayoutRegion("rating", 617, 436.5, 126, 96, 28, 16, FONT_PATH, "left", 6),
}

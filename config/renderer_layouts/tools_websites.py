import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "tool_name": LayoutRegion("tool_name", 47, 255, 1080, 60, 44, 16, FONT_PATH, "left", 6),
    "website": LayoutRegion("website", 110, 345, 450, 40, 27, 16, FONT_PATH, "left", 6),
    "short_description": LayoutRegion("short_description", 720, 519, 397, 150, 25, 16, FONT_PATH, "left", 6),
    "category": LayoutRegion("category", 619, 1092, 110, 30, 25, 16, FONT_PATH, "left", 6),
    "pricing": LayoutRegion("pricing", 786, 1091.5, 110, 30, 25, 16, FONT_PATH, "left", 6),
    "platform": LayoutRegion("platform", 958, 1092, 110, 30, 19, 16, FONT_PATH, "left", 6),
    "best_for_1": LayoutRegion("best_for_1", 760, 776, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "best_for_2": LayoutRegion("best_for_2", 760, 822, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "best_for_3": LayoutRegion("best_for_3", 760, 868, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "rating": LayoutRegion("rating", 256, 1119.6, 40, 35, 27, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 141.5, 49.5, 20, 40, 30, 16, FONT_PATH, "left", 6)
}

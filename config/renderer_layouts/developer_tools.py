import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "tool_name": LayoutRegion("tool_name", 35, 218, 1080, 60, 37, 16, FONT_PATH, "left", 6),
    "website": LayoutRegion("website", 89, 277, 450, 40, 38, 19, FONT_PATH, "left", 8),
    "category": LayoutRegion("category", 704, 1023, 250, 30, 20, 14, FONT_PATH, "left", 6),
    "license": LayoutRegion("license", 988, 1023, 150, 30, 18, 14, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 134, 49, 115, 40, 31, 16, FONT_PATH, "left", 6),
    "short_description": LayoutRegion("short_description", 734, 469, 367, 160, 23, 16, FONT_PATH, "left", 6),
    "why_developers_love_it": LayoutRegion("why_developers_love_it", 155, 1015, 408, 129, 22, 18, FONT_PATH, "left", 7),
    "best_for_1": LayoutRegion("best_for_1", 775, 742, 973, 77, 24, 16, FONT_PATH, "left", 6),
    "best_for_2": LayoutRegion("best_for_2", 775, 786, 973, 50, 24, 16, FONT_PATH, "left", 6),
    "best_for_3": LayoutRegion("best_for_3", 775, 830, 973, 50, 24, 16, FONT_PATH, "left", 6),
    "rating": LayoutRegion("rating", 266, 831, 40, 35, 25, 16, FONT_PATH, "left", 6),
}

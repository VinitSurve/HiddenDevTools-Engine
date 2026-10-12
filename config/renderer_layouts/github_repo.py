import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "resource_name": LayoutRegion("resource_name", 63, 236, 800, 100, 60, 40, FONT_PATH, "left", 2),
    "link": LayoutRegion("link", 133, 340, 800, 50, 30, 20, FONT_PATH, "left", 1),
    "short_description": LayoutRegion("short_description", 724, 497, 406, 130, 25, 14, FONT_PATH, "left", 6),
    "pricing": LayoutRegion("pricing", 760, 1032, 120, 30, 25, 16, FONT_PATH, "left", 1),
    "difficulty": LayoutRegion("difficulty", 961, 1034, 120, 30, 22, 16, FONT_PATH, "right", 1),
    "Slide Number": LayoutRegion("Slide Number", 155, 55, 20, 40, 30, 16, FONT_PATH, "center", 1),
    "why_it_matters": LayoutRegion("why_it_matters", 173, 1008, 413, 140, 30, 14, FONT_PATH, "left", 7),
    "best_for_1": LayoutRegion("best_for_1", 775, 745, 300, 50, 26, 20, FONT_PATH, "left", 2),
    "best_for_2": LayoutRegion("best_for_2", 775, 785, 300, 50, 26, 20, FONT_PATH, "left", 2),
    "best_for_3": LayoutRegion("best_for_3", 775, 825, 300, 50, 26, 20, FONT_PATH, "left", 2),
    "rating": LayoutRegion("rating", 268, 834, 40, 35, 25, 16, FONT_PATH, "center", 1),
}

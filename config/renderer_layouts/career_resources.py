import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "resource_name": LayoutRegion("resource_name", 45, 207, 1080, 60, 50, 16, FONT_PATH, "left", 6),
    "website": LayoutRegion("website", 89, 290, 450, 40, 38, 19, FONT_PATH, "left", 8),
    "category": LayoutRegion("category", 688, 971, 150, 30, 19, 11, FONT_PATH, "center", 1),
    "free_paid": LayoutRegion("free_paid", 950, 971, 120, 30, 19, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 138, 37, 20, 40, 36, 16, FONT_PATH, "left", 6),
    "best_for_1": LayoutRegion("best_for_1", 820, 682, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_2": LayoutRegion("best_for_2", 820, 724, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "best_for_3": LayoutRegion("best_for_3", 820, 766, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "why_use_it": LayoutRegion("why_use_it", 785, 425, 320, 140, 25, 16, FONT_PATH, "left", 5),
    "rating": LayoutRegion("rating", 195, 961, 307, 124, 28, 16, FONT_PATH, "center", 6),
}

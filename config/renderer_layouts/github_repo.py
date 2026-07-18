import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Resource Name": LayoutRegion("Resource Name", -160, 236, 973, 100, 60, 40, FONT_PATH, "center", 2),
    "Link": LayoutRegion("Link", -218, 340, 973, 50, 30, 20, FONT_PATH, "center", 1),
    "Short Description": LayoutRegion("Short Description", 724, 497, 406, 130, 25, 16, FONT_PATH, "left", 4),
    "Pricing": LayoutRegion("Pricing", 760, 1032, 120, 30, 25, 16, FONT_PATH, "left", 1),
    "Difficulty": LayoutRegion("Difficulty", 961, 1034, 120, 30, 22, 16, FONT_PATH, "right", 1),
    "Slide Number": LayoutRegion("Slide Number", 155, 55, 20, 40, 30, 16, FONT_PATH, "center", 1),
    "Why it Matters": LayoutRegion("Why it Matters", 173, 1008, 413, 140, 40, 25, FONT_PATH, "left", 4),
    "Best for 1": LayoutRegion("Best for 1", 730, 745, 300, 50, 26, 20, FONT_PATH, "center", 2),
    "Best for 2": LayoutRegion("Best for 2", 712, 785, 300, 50, 26, 20, FONT_PATH, "center", 2),
    "Best for 3": LayoutRegion("Best for 3", 723, 825, 300, 50, 26, 20, FONT_PATH, "center", 2),
    "Rating": LayoutRegion("Rating", 268, 834, 40, 35, 25, 16, FONT_PATH, "center", 1),
}

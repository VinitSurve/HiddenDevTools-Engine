import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Alternative Name": LayoutRegion("Alternative Name", 64, 222, 973, 50, 45, 25, FONT_PATH, "left", 6),
    "Replaces": LayoutRegion("Replaces", 77, 854, 1068, 54, 23, 16, FONT_PATH, "left", 6),
    "Website": LayoutRegion("Website", 111, 295, 450, 87, 25, 16, FONT_PATH, "left", 6),
    "Pricing": LayoutRegion("Pricing", 1039, 997, 120, 30, 25, 16, FONT_PATH, "left", 6),
    "Category": LayoutRegion("Category", 840, 997, 120, 30, 25, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 141, 38, 20, 70, 32, 16, FONT_PATH, "left", 6),
    "Why Switch": LayoutRegion("Why Switch", 870, 487, 270, 103, 25, 16, FONT_PATH, "left", 6),
    "Best For 1": LayoutRegion("Best For 1", 908, 723, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 2": LayoutRegion("Best For 2", 908, 763, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 3": LayoutRegion("Best For 3", 908, 805, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Rating": LayoutRegion("Rating", 617, 428, 126, 96, 28, 16, FONT_PATH, "left", 6),
}

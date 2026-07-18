import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Tool Name": LayoutRegion("Tool Name", 47, 255, 1080, 60, 44, 16, FONT_PATH, "left", 6),
    "Website": LayoutRegion("Website", 110, 345, 450, 40, 27, 16, FONT_PATH, "left", 6),
    "Short Description": LayoutRegion("Short Description", 720, 519, 397, 150, 25, 16, FONT_PATH, "left", 6),
    "Category": LayoutRegion("Category", 619, 1092, 110, 30, 25, 16, FONT_PATH, "left", 6),
    "Pricing": LayoutRegion("Pricing", 786, 1091.5, 110, 30, 25, 16, FONT_PATH, "left", 6),
    "Platform": LayoutRegion("Platform", 958, 1092, 110, 30, 19, 16, FONT_PATH, "left", 6),
    "Best for 1": LayoutRegion("Best for 1", 760, 776, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "Best for 2": LayoutRegion("Best for 2", 760, 822, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "Best for 3": LayoutRegion("Best for 3", 760, 868, 497, 50, 20, 18, FONT_PATH, "left", 6),
    "Rating": LayoutRegion("Rating", 256, 1119.6, 40, 35, 27, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 141.5, 49.5, 20, 40, 30, 16, FONT_PATH, "left", 6)
}

import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Tool Name": LayoutRegion("Tool Name", 35, 210, 1080, 60, 37, 16, FONT_PATH, "left", 6),
    "Website": LayoutRegion("Website", 97, 272, 450, 40, 29, 16, FONT_PATH, "left", 6),
    "Category": LayoutRegion("Category", 700, 1017, 120, 30, 25, 16, FONT_PATH, "left", 6),
    "License": LayoutRegion("License", 985, 1018, 120, 30, 22, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 134, 42, 115, 40, 31, 16, FONT_PATH, "left", 6),
    "Short Description": LayoutRegion("Short Description", 734, 469, 367, 160, 23, 16, FONT_PATH, "left", 6),
    "Why Developers Love it": LayoutRegion("Why Developers Love it", 155, 1015, 408, 129, 22, 18, FONT_PATH, "left", 7),
    "Best for 1": LayoutRegion("Best for 1", 767, 735, 973, 77, 24, 16, FONT_PATH, "left", 6),
    "Best for 2": LayoutRegion("Best for 2", 767, 779, 973, 50, 24, 16, FONT_PATH, "left", 6),
    "Best for 3": LayoutRegion("Best for 3", 767, 822, 973, 50, 24, 16, FONT_PATH, "left", 6),
    "Rating": LayoutRegion("Rating", 265, 824, 40, 35, 25, 16, FONT_PATH, "left", 6),
}

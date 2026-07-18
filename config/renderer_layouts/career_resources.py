import os
from renderers.base_renderer import LayoutRegion

FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))

REGIONS = {
    "Resource Name": LayoutRegion("Resource Name", 45, 207, 1080, 60, 50, 16, FONT_PATH, "left", 6),
    "Website": LayoutRegion("Website", 89, 287, 450, 40, 38, 19, FONT_PATH, "left", 8),
    "Category": LayoutRegion("Category", 714, 967, 120, 30, 25, 16, FONT_PATH, "left", 6),
    "Free/Paid": LayoutRegion("Free/Paid", 990, 965, 120, 30, 25, 16, FONT_PATH, "left", 6),
    "Slide Number": LayoutRegion("Slide Number", 138, 33, 20, 40, 36, 16, FONT_PATH, "left", 6),
    "Best For 1": LayoutRegion("Best For 1", 820, 677, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 2": LayoutRegion("Best For 2", 820, 718, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Best For 3": LayoutRegion("Best For 3", 818, 760, 250, 30, 25, 16, FONT_PATH, "left", 6),
    "Why Use It": LayoutRegion("Why Use It", 785, 425, 320, 140, 25, 16, FONT_PATH, "left", 5),
    "Rating": LayoutRegion("Rating", 190, 952, 307, 124, 31, 16, FONT_PATH, "center", 6),
}

# ==========================================================
# Canvas
# ==========================================================

CANVAS_WIDTH = 1208
CANVAS_HEIGHT = 1302

# ==========================================================
# Templates
# ==========================================================

TEMPLATES = {
    "cover": "templates/Github_Master_Cover.png",
    "content": "templates/Github_Content_Slide_Template.jpg",
    "last": "templates/Github_Last_Page.png",
}

OUTPUT_DIR = "output"

# ==========================================================
# Google Sheet
# ==========================================================

SHEET_PUBHTML_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vS2mSiO13RHh20Jold_ehinBdYzk84mpeELPsS5K_uNn6YDwfEo3_"
    "1CV4dVRwCShxGB30z2CLtf286y/pub?output=csv"
)

# ==========================================================
# Google Sheet Columns
# ==========================================================

COL_ID = "ID"
COL_NAME = "Resource Name"
COL_LINK = "Link"
COL_DESC = "Short Description"

COL_PRICING = "Pricing"
COL_DIFFICULTY = "Difficulty"

COL_SLIDE_NUM = "Slide Number"

COL_WHY = "Why it Matters"

COL_BEST_FOR1 = "Best for 1"
COL_BEST_FOR2 = "Best for 2"
COL_BEST_FOR3 = "Best for 3"

COL_RATING = "Rating"

COL_STATUS = "Status"

# ==========================================================
# Fonts
# ==========================================================

FONT_CANDIDATES_BOLD = [
    r"E:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\assets\fonts\Inter_28pt-Bold.ttf"
]

FONT_CANDIDATES_REGULAR = [
    r"E:\Vinitt\HiddenDevTools\HiddenDevTools-Engine\assets\fonts\Inter_28pt-Regular.ttf"
]

# ==========================================================
# Colors
# ==========================================================

COLOR_DARK_NAVY = (15, 23, 42)
COLOR_DARK_TEXT = (30, 41, 59)
COLOR_BLUE_ACCENT = (37, 99, 235)
COLOR_WHITE = (255, 255, 255)
COLOR_SLIDE_NUM = (30, 41, 59)

# ==========================================================
# Content Slide Coordinates
# ==========================================================

SLIDE_NUMBER = {
    "x": 157,
    "y": 44,
    "font_size": 28,
}

REPO_NAME = {
    "x": 60,
    "y": 196,
    "max_width": 640,
    "font_size": 75,
}

REPO_URL = {
    "x": 131,
    "y": 318,
    "max_width": 640,
    "font_size": 32,
}

DESCRIPTION = {
    "x": 748,
    "y": 256,
    "max_width": 390,
    "max_height": 140,
    "font_size": 24,
}

BEST_FOR = [
    {
        "x": 785,
        "y": 487,
        
    },
    {
        "x": 785,
        "y": 525,
    },
    {
        "x": 785,
        "y": 565,
    },
]

PRICING = {
    "center_x": 766,
    "center_y": 730,
    "font_size": 30,
}

DIFFICULTY = {
    "center_x": 950,
    "center_y": 737,
    "font_size": 20.3,
}

RATING = {
    "x": 276,
    "y": 795,
    "font_size": 23.5,
}

WHY_IT_MATTERS = {
    "x": 345,
    "y": 971,
    "max_width": 670,
    "max_height": 130,
    "font_size": 28,
}
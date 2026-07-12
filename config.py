from dotenv import load_dotenv
load_dotenv(override=True)

import os

# ==========================================================
# Project Paths
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")

FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

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
# Developer Tools Columns
# ==========================================================

DEV_COL_ID = "ID"

DEV_COL_NAME = "Tool Name"

DEV_COL_WEBSITE = "Website"

DEV_COL_CATEGORY = "Category"

DEV_COL_LANGUAGES = "Supported Languages"

DEV_COL_LICENSE = "License"

DEV_COL_DESC = "Short Description"

DEV_COL_WHY = "Why Developers Love it"

DEV_COL_BEST1 = "Best for 1"

DEV_COL_BEST2 = "Best for 2"

DEV_COL_BEST3 = "Best for 3"

DEV_COL_RATING = "Rating"

DEV_COL_STATUS = "Status"

DEV_COL_POST = "Post"

DEV_COL_GENERATED = "Generated At"

DEV_COL_PUBLISHED = "Published At"

DEV_COL_GENERATION_ID = "Generation ID"

# ==========================================================
# Fonts
# ==========================================================

FONT_CANDIDATES_BOLD = [
    os.path.join(
        FONTS_DIR,
        "Inter_28pt-Bold.ttf"
    )
]

FONT_CANDIDATES_REGULAR = [
    os.path.join(
        FONTS_DIR,
        "Inter_28pt-Regular.ttf"
    )
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
    "x": 141,
    "y": 46,
    "font_size": 26,
}

REPO_NAME = {
    "x": 60,
    "y": 210,
    "max_width": 640,
    "font_size": 75,
}

REPO_URL = {
    "x": 111,
    "y": 322,
    "max_width": 640,
    "font_size": 32,
}

DESCRIPTION = {
    "x": 736,
    "y": 476,
    "max_width": 390,
    "max_height": 140,
    "font_size": 23,
}

BEST_FOR = [
    {
        "x": 785,
        "y": 718,
        
    },
    {
        "x": 785,
        "y": 757,
    },
    {
        "x": 785,
        "y": 798,
    },
]

PRICING = {
    "center_x": 793,
    "center_y": 995,
    "font_size": 30,
}

DIFFICULTY = {
    "center_x": 979,
    "center_y": 1003,
    "font_size": 20.3,
}

RATING = {
    "x": 260,
    "y": 803.7,
    "font_size": 23.5,
}

WHY_IT_MATTERS = {
    "x": 163.5,
    "y": 968,
    "max_width": 390,
    "max_height": 130,
    "font_size": 22,
}

# ==========================================================
# Google Sheets API
# ==========================================================



SERVICE_ACCOUNT_FILE = os.getenv(
    "SERVICE_ACCOUNT_FILE",
    "service_account.json"
)

SPREADSHEET_ID = os.getenv(
    "SPREADSHEET_ID",
    "1IyjUOGOoOqsiLoNiza9B9wvkeQLgXCd_tYeTFlYfEUA"
)

# ==========================================================
# Google Sheet Column Letters
# ==========================================================

STATUS_COLUMN = "M"
POST_COLUMN = "N"
GENERATED_AT_COLUMN = "O"
GENERATION_ID_COLUMN = "P"

# ==========================================================
# Google Drive
# ==========================================================

DRIVE_ROOT_FOLDER_ID = (
    "1u-wD8e0IpoURHNlIuXeL1sP6UhMOg_wE"
)

DRIVE_FOLDER_ID_COLUMN = "Q"
DRIVE_FOLDER_URL_COLUMN = "R"

# ==========================================================
# Instagram Publishing Columns
# ==========================================================

INSTAGRAM_MEDIA_ID_COLUMN = "S"
INSTAGRAM_POST_URL_COLUMN = "T"
PUBLISHED_AT_COLUMN = "U"

# ==========================================================
# Meta Graph API
# ==========================================================

META_APP_ID = os.getenv("META_APP_ID", "").strip()

META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()

INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "").strip()

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()

GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip()

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "").strip()

PORT = int(os.getenv("PORT", 8000))

# ==========================================================
# Supabase Storage
# ==========================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")

SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

SUPABASE_BUCKET = "posts"

# ==========================================================
# Instagram Caption (Fallback)
# ==========================================================

DEFAULT_CAPTION_TEMPLATE = (
    "\U0001f527 Top 7 Developer Tools You Need\n"
    "\n"
    "Comment DEV to get all links! \U0001f680\n"
    "\n"
    "#developer #programming #coding #webdev #tech"
)

# ==========================================================
# Engagement Settings (Phase 4B & 4C)
# ==========================================================
from enum import Enum

class EngagementMode(Enum):
    KEYWORD = "keyword"
    ANY_COMMENT = "any_comment"

ENGAGEMENT_MODE: EngagementMode = EngagementMode.KEYWORD

ENGAGEMENT_KEYWORDS = {
    "DEV": [
        "dev",
        "developer",
        "developers",
        "repo",
        "repos"
    ],
    "TOOLS": [
        "tool",
        "tools"
    ],
    "LINK": [
        "link",
        "links",
        "send"
    ]
}

SQLITE_DB_PATH = "engagement.db"
PUBLISHING_DB_PATH = os.getenv("PUBLISHING_DB_PATH", "publishing.db")

# Phase 5A Capability & Feature Flags
PHASE_5A_RENDERING_ENABLED = os.getenv("PHASE_5A_RENDERING_ENABLED", "False").lower() == "true"

# Environment & Queue Settings
APP_ENV = os.getenv("APP_ENV", "development")

def is_development() -> bool:
    return APP_ENV == "development"

MAX_DM_RETRIES = int(os.getenv("MAX_DM_RETRIES", 3))
PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", 600))
WORKER_BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", 10))

# DM Formatting
RESOURCE_LINK = os.getenv("RESOURCE_LINK", "https://example.com")
BRAND_NAME = os.getenv("BRAND_NAME", "HiddenDevTools")

DM_TEMPLATE = """Hi {username}! 👋

Thanks for commenting.

Here's the resource:

{resource_link}

Enjoy!

— {brand}"""

"""
utils.py

General helper functions used throughout the HiddenDevTools Engine.
"""

import os
import re
import shutil


# ==========================================================
# Folder Helpers
# ==========================================================

def ensure_folder(path: str):
    """
    Create a folder if it does not already exist.
    """
    os.makedirs(path, exist_ok=True)


# ==========================================================
# Filename Helpers
# ==========================================================

def sanitize_filename(name: str) -> str:
    """
    Convert a string into a filesystem-safe filename.
    """

    if not name:
        return "Untitled"

    name = re.sub(r"[^A-Za-z0-9]+", "_", str(name))
    name = name.strip("_")

    return name or "Untitled"


def carousel_folder_name(repo_id: str, repo_name: str) -> str:
    """
    Returns folder name like:
    GR001_Firecrawl
    """

    return f"{repo_id}_{sanitize_filename(repo_name)}"


# ==========================================================
# URL Helpers
# ==========================================================

def clean_repo_url(url: str) -> str:
    """
    Removes protocol for display.
    """

    if not url:
        return ""

    url = url.replace("https://", "")
    url = url.replace("http://", "")

    return url.rstrip("/")


# ==========================================================
# File Copy Helpers
# ==========================================================

def copy_file(source: str, destination: str):
    """
    Copy a file while preserving metadata.
    """

    shutil.copy2(source, destination)


def copy_template(template_path: str, output_folder: str, filename: str):
    """
    Copy a template into an output folder.
    """

    ensure_folder(output_folder)

    shutil.copy2(
        template_path,
        os.path.join(output_folder, filename)
    )


# ==========================================================
# Status Helpers
# ==========================================================

def is_draft(status: str) -> bool:
    """
    True if row should be generated.
    """

    return str(status).strip().lower() == "draft"


# ==========================================================
# Output Helpers
# ==========================================================

def content_slide_path(folder: str) -> str:
    return os.path.join(folder, "02_Content.png")


def cover_slide_path(folder: str) -> str:
    return os.path.join(folder, "01_Cover.png")


def last_slide_path(folder: str) -> str:
    return os.path.join(folder, "03_Last.png")


# ==========================================================
# Logging Helpers
# ==========================================================

def print_banner(message: str):
    print("\n" + "=" * 60)
    print(message)
    print("=" * 60)


def print_step(message: str):
    print(f"• {message}")


def print_success(message: str):
    print(f"✓ {message}")

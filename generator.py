"""
generator.py

Responsible for generating one complete Instagram carousel.
"""

import os
import shutil

from engine import Engine

from config import *


# ==========================================================
# Generate One Content Slide
# ==========================================================

def generate_content_slide(
    row,
    output_path
):

    engine = Engine()

    # ------------------------------------------------------
    # Slide Number
    # ------------------------------------------------------

    engine.text(
        SLIDE_NUMBER["x"],
        SLIDE_NUMBER["y"],
        row[COL_SLIDE_NUM],
        size=SLIDE_NUMBER["font_size"],
        bold=True
    )

    # ------------------------------------------------------
    # Repository Name
    # ------------------------------------------------------

    engine.text(
        REPO_NAME["x"],
        REPO_NAME["y"],
        row[COL_NAME],
        size=REPO_NAME["font_size"],
        bold=True
    )

    # ------------------------------------------------------
    # Repository URL
    # ------------------------------------------------------

    repo_url = (
        row[COL_LINK]
        .replace("https://", "")
        .replace("http://", "")
    )

    engine.text(
        REPO_URL["x"],
        REPO_URL["y"],
        repo_url,
        size=REPO_URL["font_size"],
        color=COLOR_BLUE_ACCENT
    )

    # ------------------------------------------------------
    # Description
    # ------------------------------------------------------

    engine.paragraph(
        DESCRIPTION["x"],
        DESCRIPTION["y"],
        row[COL_DESC],
        width=DESCRIPTION["max_width"],
        height=DESCRIPTION["max_height"],
        size=DESCRIPTION["font_size"],
        min_size=16,
        color=COLOR_DARK_TEXT
    )

    # ------------------------------------------------------
    # Best For
    # ------------------------------------------------------

    engine.text(
        BEST_FOR[0]["x"],
        BEST_FOR[0]["y"],
        row[COL_BEST_FOR1],
        size=22,
        color=COLOR_DARK_TEXT
    )

    engine.text(
        BEST_FOR[1]["x"],
        BEST_FOR[1]["y"],
        row[COL_BEST_FOR2],
        size=22,
        color=COLOR_DARK_TEXT
    )

    engine.text(
        BEST_FOR[2]["x"],
        BEST_FOR[2]["y"],
        row[COL_BEST_FOR3],
        size=22,
        color=COLOR_DARK_TEXT
    )

    # ------------------------------------------------------
    # Pricing
    # ------------------------------------------------------

    engine.text(
        PRICING["center_x"],
        PRICING["center_y"],
        row[COL_PRICING],
        size=PRICING["font_size"],
        color=COLOR_WHITE,
        bold=True
    )

    # ------------------------------------------------------
    # Difficulty
    # ------------------------------------------------------

    engine.text(
        DIFFICULTY["center_x"],
        DIFFICULTY["center_y"],
        row[COL_DIFFICULTY],
        size=DIFFICULTY["font_size"],
        color=COLOR_WHITE,
        bold=True
    )

    # ------------------------------------------------------
    # Rating
    # ------------------------------------------------------

    engine.text(
        RATING["x"],
        RATING["y"],
        row[COL_RATING],
        size=RATING["font_size"],
        bold=True
    )

    # ------------------------------------------------------
    # Why It Matters
    # ------------------------------------------------------

    engine.paragraph(
        WHY_IT_MATTERS["x"],
        WHY_IT_MATTERS["y"],
        row[COL_WHY],
        width=WHY_IT_MATTERS["max_width"],
        height=WHY_IT_MATTERS["max_height"],
        size=WHY_IT_MATTERS["font_size"],
        min_size=16,
        color=COLOR_DARK_TEXT
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    engine.save(output_path)


# ==========================================================
# Generate Complete Post
# ==========================================================

def generate_post(
    draft_rows,
    post_name
):

    post_folder = os.path.join(
        OUTPUT_DIR,
        post_name
    )

    os.makedirs(
        post_folder,
        exist_ok=True
    )

    print()
    print(f"Created {post_folder}")

    # ------------------------------------------------------
    # Copy Cover
    # ------------------------------------------------------

    shutil.copy2(
        TEMPLATES["cover"],
        os.path.join(
            post_folder,
            "01_Cover.png"
        )
    )

    print("✓ Cover copied")

    # ------------------------------------------------------
    # Generate Content Slides
    # ------------------------------------------------------

    for index, row in enumerate(draft_rows):

        slide_number = index + 2

        filename = f"{slide_number:02d}_Content.png"

        output_path = os.path.join(
            post_folder,
            filename
        )

        print(f"Generating {filename}...")

        generate_content_slide(
            row,
            output_path
        )

    print("✓ All content slides generated")

    # ------------------------------------------------------
    # Copy CTA
    # ------------------------------------------------------

    shutil.copy2(
        TEMPLATES["last"],
        os.path.join(
            post_folder,
            "09_CTA.png"
        )
    )

    print("✓ CTA copied")
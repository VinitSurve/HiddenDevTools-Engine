from PIL import Image, ImageDraw, ImageFont

from config import (
    TEMPLATES,
    REPO_NAME,
    FONT_CANDIDATES_BOLD,
    COLOR_DARK_NAVY,
)

from text_utils import fit_font, draw_wrapped_text


def generate_slide(repo_name: str, output_path: str):
    # Open template
    img = Image.open(TEMPLATES["content"]).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Load first available font
    font_path = FONT_CANDIDATES_BOLD[0]

    # Automatically fit repo name
    font, lines = fit_font(
        text=repo_name,
        font_path=font_path,
        max_size=REPO_NAME["font_size_max"],
        min_size=REPO_NAME["font_size_min"],
        max_width=REPO_NAME["max_width"],
        max_lines=REPO_NAME["max_lines"],
    )

    # Draw repo name
    draw_wrapped_text(
        draw,
        lines,
        REPO_NAME["x"],
        REPO_NAME["y"],
        font,
        COLOR_DARK_NAVY,
    )

    img.save(output_path)
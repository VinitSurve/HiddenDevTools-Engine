"""
text_utils.py – Reusable Pillow text-drawing helpers.

All public functions accept a Pillow ImageDraw object and return the bounding
box of what was drawn so callers can chain or verify placement.
"""

from PIL import ImageFont, ImageDraw


# ─────────────────────────────────────────────────────────────────────────────
# Font loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TTF font at the given size, falling back to default if needed."""
    try:
        return ImageFont.truetype(font_path, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def fit_font(
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    max_width: int,
    max_lines: int = 1,
    line_spacing: float = 1.35,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """
    Reduce font size until `text` fits within `max_width` and `max_lines`.

    Returns:
        (font, lines)  where lines is a list of wrapped text segments.
    """
    for size in range(max_size, min_size - 1, -1):
        font = _load_font(font_path, size)
        lines = _wrap_text(text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines

    # Last resort: return smallest size even if it overflows
    font = _load_font(font_path, min_size)
    lines = _wrap_text(text, font, max_width)
    # Truncate to max_lines with ellipsis on last line
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _truncate_with_ellipsis(lines[-1], font, max_width)
    return font, lines


def fit_font_block(
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    max_width: int,
    max_height: int,
    max_lines: int = 3,
    line_spacing: float = 1.35,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """
    Reduce font size until the wrapped text block fits within max_width × max_height.

    Returns:
        (font, lines)
    """
    for size in range(max_size, min_size - 1, -1):
        font = _load_font(font_path, size)
        lines = _wrap_text(text, font, max_width)

        if len(lines) > max_lines:
            continue  # try smaller size

        # Check total height
        line_h = _line_height(font)
        total_h = line_h + (len(lines) - 1) * int(line_h * line_spacing)
        if total_h <= max_height:
            return font, lines

    # Smallest size, truncate to max_lines
    font = _load_font(font_path, min_size)
    lines = _wrap_text(text, font, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _truncate_with_ellipsis(lines[-1], font, max_width)
    return font, lines


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _line_height(font: ImageFont.FreeTypeFont) -> int:
    """Return the pixel height of one line for the given font."""
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1]


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    """Return the pixel width of a text string."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Greedy word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(candidate, font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines or [""]


def _truncate_with_ellipsis(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate text to fit max_width, appending '…'."""
    ellipsis = "…"
    if _text_width(text + ellipsis, font) <= max_width:
        return text + ellipsis
    while text and _text_width(text + ellipsis, font) > max_width:
        text = text[:-1]
    return text + ellipsis


# ─────────────────────────────────────────────────────────────────────────────
# Public drawing functions
# ─────────────────────────────────────────────────────────────────────────────

def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    color: tuple,
) -> tuple[int, int, int, int]:
    """
    Draw a single-line text string at (x, y).

    Returns:
        (x, y, width, height) bounding box of what was drawn.
    """
    draw.text((x, y), text, font=font, fill=color)
    w = _text_width(text, font)
    h = _line_height(font)
    return (x, y, w, h)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    line_spacing: float = 1.35,
) -> tuple[int, int, int, int]:
    """
    Draw pre-wrapped lines of text starting at (x, y).

    Returns:
        (x, y, max_width, total_height) bounding box.
    """
    line_h = _line_height(font)
    step    = int(line_h * line_spacing)
    max_w   = 0

    for i, line in enumerate(lines):
        draw.text((x, y + i * step), line, font=font, fill=color)
        max_w = max(max_w, _text_width(line, font))

    total_h = line_h + (len(lines) - 1) * step if lines else 0
    return (x, y, max_w, total_h)


def center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box_x: int,
    box_y: int,
    box_w: int,
    box_h: int,
    font: ImageFont.FreeTypeFont,
    color: tuple,
) -> None:
    """
    Draw `text` centered both horizontally and vertically inside a bounding box.

    box_x, box_y  – top-left of the box
    box_w, box_h  – width and height of the box
    """
    text_w = _text_width(text, font)
    text_h = _line_height(font)
    x = box_x + (box_w - text_w) // 2
    y = box_y + (box_h - text_h) // 2
    draw.text((x, y), text, font=font, fill=color)
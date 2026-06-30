from PIL import Image, ImageDraw, ImageFont

from config import (
    TEMPLATES,
    FONT_CANDIDATES_BOLD,
    FONT_CANDIDATES_REGULAR,
    COLOR_DARK_NAVY,
)


class Engine:

    def __init__(self):

        self.image = Image.open(
            TEMPLATES["content"]
        ).convert("RGBA")

        self.draw = ImageDraw.Draw(self.image)

        self.bold_font_path = FONT_CANDIDATES_BOLD[0]
        self.regular_font_path = FONT_CANDIDATES_REGULAR[0]

    # --------------------------------------------------
    # Font
    # --------------------------------------------------

    def get_font(self, size=40, bold=False):

        path = self.bold_font_path if bold else self.regular_font_path
        return ImageFont.truetype(path, size)

    # --------------------------------------------------
    # Single line text
    # --------------------------------------------------

    def text(
        self,
        x,
        y,
        text,
        size=40,
        color=COLOR_DARK_NAVY,
        bold=False,
    ):

        if text is None:
            return

        font = self.get_font(size=size, bold=bold)

        self.draw.text(
            (x, y),
            str(text),
            fill=color,
            font=font
        )

    # --------------------------------------------------
    # Paragraph inside fixed rectangle
    # --------------------------------------------------

    def paragraph(
        self,
        x,
        y,
        text,
        width,
        height,
        size=24,
        min_size=16,
        color=COLOR_DARK_NAVY,
        bold=False,
        line_spacing=8
    ):

        if text is None:
            return

        text = str(text)

        current_size = size

        while current_size >= min_size:

            font = self.get_font(
                size=current_size,
                bold=bold
            )

            words = text.split()

            lines = []
            current = ""

            for word in words:

                candidate = word if current == "" else current + " " + word

                bbox = self.draw.textbbox(
                    (0, 0),
                    candidate,
                    font=font
                )

                if bbox[2] <= width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word

            if current:
                lines.append(current)

            line_height = self.draw.textbbox(
                (0, 0),
                "Ag",
                font=font
            )[3]

            total_height = len(lines) * (line_height + line_spacing)

            if total_height <= height:
                break

            current_size -= 1

        yy = y

        for line in lines:

            self.draw.text(
                (x, yy),
                line,
                fill=color,
                font=font
            )

            yy += line_height + line_spacing

    # --------------------------------------------------

    def save(self, path):

        self.image.save(path)

        print(f"Saved -> {path}")
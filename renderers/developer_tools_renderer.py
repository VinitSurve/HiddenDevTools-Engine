from engine import Engine

from config import (
    SLIDE_NUMBER,
    COLOR_SLIDE_NUM,
    REPO_NAME,
    REPO_URL,
    COLOR_BLUE_ACCENT,
    DESCRIPTION,
    COLOR_DARK_TEXT,
    PRICING,
    COLOR_WHITE,
    DIFFICULTY,
    RATING,
    BEST_FOR,
    WHY_IT_MATTERS,
)


class DeveloperToolsRenderer:

    def __init__(self):
        pass

    def render(
        self,
        row,
        output_path,
    ):

        # Start every slide from a fresh template
        self.engine = Engine(
            "templates/developer_tools/Developer_Tools_Content_Template.png"
        )

        print(
            "Rendering:",
            row["Tool Name"]
        )

        self.engine.text(
            SLIDE_NUMBER["x"],
            SLIDE_NUMBER["y"],
            row["Slide Number"],
            size=SLIDE_NUMBER["font_size"],
            color=COLOR_SLIDE_NUM,
            bold=True,
        )

        self.engine.text(
            REPO_NAME["x"],
            REPO_NAME["y"],
            row["Tool Name"],
            size=REPO_NAME["font_size"],
            bold=True,
        )

        website = (
            row["Website"]
            .replace("https://", "")
            .replace("http://", "")
        )

        self.engine.text(
            REPO_URL["x"],
            REPO_URL["y"],
            website,
            size=REPO_URL["font_size"],
            color=COLOR_BLUE_ACCENT,
        )

        self.engine.paragraph(
            DESCRIPTION["x"],
            DESCRIPTION["y"],
            row["Short Description"],
            width=DESCRIPTION["max_width"],
            height=DESCRIPTION["max_height"],
            size=DESCRIPTION["font_size"],
            min_size=16,
            color=COLOR_DARK_TEXT,
        )

        self.engine.text(
            PRICING["center_x"],
            PRICING["center_y"],
            row["Category"],
            size=PRICING["font_size"],
            color=COLOR_WHITE,
            bold=True,
        )

        self.engine.text(
            DIFFICULTY["center_x"],
            DIFFICULTY["center_y"],
            row["License"],
            size=DIFFICULTY["font_size"],
            color=COLOR_WHITE,
            bold=True,
        )

        self.engine.text(
            RATING["x"],
            RATING["y"],
            row["Rating"],
            size=RATING["font_size"],
            bold=True,
        )

        self.engine.text(
            BEST_FOR[0]["x"],
            BEST_FOR[0]["y"],
            row["Best for 1"],
            size=22,
            color=COLOR_DARK_TEXT,
        )

        self.engine.text(
            BEST_FOR[1]["x"],
            BEST_FOR[1]["y"],
            row["Best for 2"],
            size=22,
            color=COLOR_DARK_TEXT,
        )

        self.engine.text(
            BEST_FOR[2]["x"],
            BEST_FOR[2]["y"],
            row["Best for 3"],
            size=22,
            color=COLOR_DARK_TEXT,
        )

        self.engine.paragraph(
            WHY_IT_MATTERS["x"],
            WHY_IT_MATTERS["y"],
            row["Why Developers Love it"],
            width=WHY_IT_MATTERS["max_width"],
            height=WHY_IT_MATTERS["max_height"],
            size=WHY_IT_MATTERS["font_size"],
            min_size=16,
            color=COLOR_DARK_TEXT,
        )

        self.engine.save(output_path)
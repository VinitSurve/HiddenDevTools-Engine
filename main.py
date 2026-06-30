import os
import re

from engine import Engine
from google_sheet import fetch_rows
from config import *

os.makedirs(OUTPUT_DIR, exist_ok=True)

rows = fetch_rows()

if not rows:
    print("No rows found.")
    raise SystemExit

print(f"Loaded {len(rows)} rows from Google Sheets.")

for row in rows:
    status = row.get(COL_STATUS, "").strip().lower()
    if status != "draft":
        continue

    repo_name = row[COL_NAME]
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", repo_name).strip("_")
    folder = os.path.join(OUTPUT_DIR, f"{row[COL_ID]}_{safe_name}")
    os.makedirs(folder, exist_ok=True)

    print(f"Generating {repo_name}")

    engine = Engine()

    engine.text(SLIDE_NUMBER["x"], SLIDE_NUMBER["y"], row[COL_SLIDE_NUM], size=SLIDE_NUMBER["font_size"], bold=True)
    engine.text(REPO_NAME["x"], REPO_NAME["y"], row[COL_NAME], size=REPO_NAME["font_size"], bold=True)

    repo_url = row[COL_LINK].replace("https://","").replace("http://","")
    engine.text(REPO_URL["x"], REPO_URL["y"], repo_url, size=REPO_URL["font_size"], color=COLOR_BLUE_ACCENT)

    engine.paragraph(DESCRIPTION["x"], DESCRIPTION["y"], row[COL_DESC],
                     width=DESCRIPTION["max_width"], height=DESCRIPTION["max_height"],
                     size=DESCRIPTION["font_size"], min_size=16, color=COLOR_DARK_TEXT)

    engine.text(BEST_FOR[0]["x"], BEST_FOR[0]["y"], row[COL_BEST_FOR1], size=22, color=COLOR_DARK_TEXT)
    engine.text(BEST_FOR[1]["x"], BEST_FOR[1]["y"], row[COL_BEST_FOR2], size=22, color=COLOR_DARK_TEXT)
    engine.text(BEST_FOR[2]["x"], BEST_FOR[2]["y"], row[COL_BEST_FOR3], size=22, color=COLOR_DARK_TEXT)

    engine.text(PRICING["center_x"], PRICING["center_y"], row[COL_PRICING], size=PRICING["font_size"], color=COLOR_WHITE, bold=True)
    engine.text(DIFFICULTY["center_x"], DIFFICULTY["center_y"], row[COL_DIFFICULTY], size=DIFFICULTY["font_size"], color=COLOR_WHITE, bold=True)
    engine.text(RATING["x"], RATING["y"], row[COL_RATING], size=RATING["font_size"], bold=True)

    engine.paragraph(WHY_IT_MATTERS["x"], WHY_IT_MATTERS["y"], row[COL_WHY],
                     width=WHY_IT_MATTERS["max_width"], height=WHY_IT_MATTERS["max_height"],
                     size=WHY_IT_MATTERS["font_size"], min_size=16, color=COLOR_DARK_TEXT)

    engine.save(os.path.join(folder, "02_Content.png"))

    with open(TEMPLATES["cover"], "rb") as src, open(os.path.join(folder, "01_Cover.png"), "wb") as dst:
        dst.write(src.read())

    with open(TEMPLATES["last"], "rb") as src, open(os.path.join(folder, "03_Last.png"), "wb") as dst:
        dst.write(src.read())

    print(f"✓ Finished {repo_name}")

print("\nAll Draft carousels generated successfully.")

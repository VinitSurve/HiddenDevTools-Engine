"""
history.py

Keeps track of executed migrations.
"""

from pathlib import Path
import json

HISTORY_FILE = Path("migrations/history.json")


def load():

    if not HISTORY_FILE.exists():
        return []

    return json.loads(
        HISTORY_FILE.read_text(
            encoding="utf-8"
        )
    )


def save(history):

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            indent=4
        ),
        encoding="utf-8"
    )


def has_run(number):

    return number in load()


def mark_run(number):

    history = load()

    if number not in history:

        history.append(number)

        save(history)
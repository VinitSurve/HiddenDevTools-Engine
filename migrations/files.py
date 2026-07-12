"""
files.py

Common file operations used by migrations.
"""

from pathlib import Path

from migrations.backup import backup_file
from migrations.logger import success


def read(file_path):

    return Path(file_path).read_text(
        encoding="utf-8"
    )


def write(
    file_path,
    content
):

    backup_file(file_path)

    Path(file_path).write_text(
        content,
        encoding="utf-8"
    )

    success(
        f"Updated {file_path}"
    )


def create(
    file_path,
    content=""
):

    path = Path(file_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content,
        encoding="utf-8"
    )

    success(
        f"Created {file_path}"
    )
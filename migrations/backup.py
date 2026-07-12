"""
backup.py

Creates backups before any migration modifies files.
"""

from pathlib import Path
import shutil


def backup_file(file_path: str):

    path = Path(file_path)

    if not path.exists():
        return

    backup = path.with_suffix(path.suffix + ".bak")

    shutil.copy2(path, backup)

    print(f"✓ Backup created: {backup}")
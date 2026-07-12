"""
discover.py

Automatically discovers all migration scripts.
"""

from pathlib import Path


def discover():

    scripts = Path("migrations/scripts")

    migrations = []

    for file in scripts.glob("*.py"):

        if file.name == "__init__.py":
            continue

        migrations.append(file.stem)

    migrations.sort()

    return migrations
"""
imports.py

Utilities for manipulating imports.
"""

from migrations.files import (
    read,
    write,
)


def insert_import(
    file_path,
    import_line
):

    content = read(
        file_path
    )

    if import_line in content:
        return

    lines = content.splitlines()

    index = 0

    while index < len(lines):

        if lines[index].startswith("from") or lines[index].startswith("import"):

            index += 1

            continue

        break

    lines.insert(
        index,
        import_line
    )

    write(
        file_path,
        "\n".join(lines)
    )
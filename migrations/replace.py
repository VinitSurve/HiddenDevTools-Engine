"""
replace.py

Safe text replacement helpers.
"""

from migrations.files import (
    read,
    write,
)


def replace_text(
    file_path,
    old,
    new
):

    content = read(
        file_path
    )

    if old not in content:

        raise ValueError(
            f"Could not find text in {file_path}"
        )

    content = content.replace(
        old,
        new,
        1
    )

    write(
        file_path,
        content
    )
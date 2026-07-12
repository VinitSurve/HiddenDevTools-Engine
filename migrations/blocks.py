"""
blocks.py

Utilities for moving and extracting code blocks.
"""

from pathlib import Path

from migrations.files import write


def read_block(
    file_path,
    start_marker,
    end_marker
):

    content = Path(file_path).read_text(
        encoding="utf-8"
    )

    start = content.find(start_marker)

    if start == -1:
        raise ValueError(
            f"Start marker not found: {start_marker}"
        )

    end = content.find(
        end_marker,
        start
    )

    if end == -1:
        raise ValueError(
            f"End marker not found: {end_marker}"
        )

    end += len(end_marker)

    return content[start:end]


def remove_block(
    file_path,
    start_marker,
    end_marker
):

    content = Path(file_path).read_text(
        encoding="utf-8"
    )

    start = content.find(start_marker)

    end = content.find(
        end_marker,
        start
    )

    end += len(end_marker)

    new_content = (
        content[:start]
        + "\n\n"
        + content[end:]
    )

    write(
        file_path,
        new_content
    )


def append_block(
    file_path,
    block
):

    path = Path(file_path)

    existing = ""

    if path.exists():

        existing = path.read_text(
            encoding="utf-8"
        )

    existing += "\n\n" + block

    write(
        file_path,
        existing
    )


def move_block(
    source,
    destination,
    block_name
):
    
    start, end = marker(
        block_name
    )

    start, end = marker(
        block_name
    )

    block = read_block(
        source,
        start,
        end
    )

    append_block(
        destination,
        block
    )

    remove_block(
        source,
        start,
        end
    )

def marker(block_name):

    return (
        f"# <migration:{block_name}>",
        f"# </migration:{block_name}>"
    )

def copy_block(
    source,
    destination,
    block_name
):

    start, end = marker(
        block_name
    )

    block = read_block(
        source,
        start,
        end
    )

    append_block(
        destination,
        block
    )
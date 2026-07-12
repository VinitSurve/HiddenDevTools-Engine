"""
Migration 003

Copies the Github renderer into its own file.
"""

from pathlib import Path

from migrations.migration import Migration

from migrations.blocks import copy_block

from migrations.logger import (
    success,
    info,
)


class CopyGithubRenderer(Migration):

    NUMBER = "003"

    NAME = "Copy Github Renderer"

    DESCRIPTION = (
        "Copies generate_content_slide() "
        "into renderers/github_repo.py"
    )

    VERSION = "1.0.0"

    def run(self):

        info("Creating renderer...")

        destination = Path(
            "renderers/github_repo.py"
        )

        if not destination.exists():

            destination.write_text(
                '"""\nGithub Repo Renderer\n"""\n',
                encoding="utf-8"
            )

            success(
                "Created github_repo.py"
            )

        copy_block(
            "generator.py",
            "renderers/github_repo.py",
            "generate_content_slide"
        )

        success(
            "Copied renderer successfully."
        )

    def verify(self):

        path = Path(
            "renderers/github_repo.py"
        )

        if not path.exists():

            raise RuntimeError(
                "Renderer file not found."
            )

        content = path.read_text(
            encoding="utf-8"
        )

        if "generate_content_slide" not in content:

            raise RuntimeError(
                "Renderer function missing."
            )

        success(
            "Verification passed."
        )
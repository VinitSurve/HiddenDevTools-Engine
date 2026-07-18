"""
services/sheet_service.py

Google Sheets service for updating row metadata across
the generation and publishing lifecycle.

Provides:
- Status transitions (Rendering, Uploading, Publishing, Published, Failed)
- Generation metadata (Gen ID, Generated At)
- Publishing metadata (Media ID, Post URL, Published At)
- Drive archive metadata (Drive Folder ID, Drive Folder URL)
"""

from datetime import datetime

from sheet_api import (
    update_status,
    update_cell,
    mark_generated,
    mark_published,
    mark_failed,
)

from settings import (
    GENERATED_AT_COLUMN,
    GENERATION_ID_COLUMN,
    DRIVE_FOLDER_ID_COLUMN,
    DRIVE_FOLDER_URL_COLUMN,
)


class SheetService:
    """
    Coordinates all Google Sheets updates for the
    publishing pipeline.

    Each method has a single responsibility:
    - update_rows_status: transition status for all rows
    - write_generation_metadata: Gen ID + timestamp
    - write_publishing_metadata: Published status + Instagram data
    - write_drive_metadata: Drive archive info
    - mark_rows_failed: set Failed status on error
    """

    # --------------------------------------------------
    # Status Transitions
    # --------------------------------------------------

    def update_rows_status(
        self,
        rows,
        status,
        sheet_name,
    ):
        """
        Set status for all rows to the given value.

        Used for intermediate states:
        Rendering, Uploading, Publishing
        """
        for row in rows:
            update_status(
                row["_row"],
                status,
                sheet_name,
            )

        print(
            f"{len(rows)} rows → {status}"
        )

    # --------------------------------------------------
    # Generation Metadata
    # --------------------------------------------------

    def write_generation_metadata(
        self,
        rows,
        generation,
        sheet_name,
    ):
        """
        Write generation ID and timestamp for all rows.

        Called after rendering completes but before publishing.
        Does NOT update status (status transitions are
        handled separately).
        """
        for row in rows:
            row_number = row["_row"]

            update_cell(
                sheet_name,
                row_number,
                GENERATED_AT_COLUMN,
                generation.generated_at,
            )

            update_cell(
                sheet_name,
                row_number,
                GENERATION_ID_COLUMN,
                generation.id,
            )

        print(
            f"✓ Generation metadata written "
            f"({generation.id})"
        )

    # --------------------------------------------------
    # Publishing Metadata
    # --------------------------------------------------

    def write_publishing_metadata(
        self,
        rows,
        media_id,
        permalink,
        sheet_name,
    ):
        """
        Write Instagram publishing data for all rows
        and set status to "Published".

        Called only after verified successful Instagram publish.
        """
        published_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        for row in rows:
            mark_published(
                sheet_name=sheet_name,
                row_number=row["_row"],
                media_id=media_id,
                post_url=permalink,
                published_at=published_at,
            )

        print(
            f"✓ Publishing metadata written "
            f"(Media ID: {media_id})"
        )

    # --------------------------------------------------
    # Drive Archive Metadata
    # --------------------------------------------------

    def write_drive_metadata(
        self,
        rows,
        drive_result,
        sheet_name,
    ):
        """
        Write Google Drive archive info for all rows.

        Called after best-effort Drive archive.
        Does NOT update status.
        """
        folder_id = drive_result.get("folder_id", "")
        folder_url = drive_result.get("folder_url", "")

        for row in rows:
            row_number = row["_row"]

            update_cell(
                sheet_name,
                row_number,
                DRIVE_FOLDER_ID_COLUMN,
                folder_id,
            )

            update_cell(
                sheet_name,
                row_number,
                DRIVE_FOLDER_URL_COLUMN,
                folder_url,
            )

        print(
            f"✓ Drive metadata written "
            f"({folder_url})"
        )

    # --------------------------------------------------
    # Failure Handling
    # --------------------------------------------------

    def mark_rows_failed(
        self,
        rows,
        sheet_name,
    ):
        """
        Set status to "Failed" for all rows.

        Called when any pipeline step fails.
        Rows can be retried by resetting status to "Draft".
        """
        for row in rows:
            mark_failed(
                sheet_name=sheet_name,
                row_number=row["_row"],
            )

        print(
            f"✗ {len(rows)} rows → Failed"
        )

    # --------------------------------------------------
    # Legacy Support
    # --------------------------------------------------

    def complete_generation(
        self,
        rows,
        generation,
        upload_result,
    ):
        """
        Legacy method — marks rows as Generated with
        Drive metadata.

        Preserved for backward compatibility with any
        pipeline that still uses this pattern.
        """
        for row in rows:
            mark_generated(
                sheet_name="Developer Tools",
                row_number=row["_row"],
                generation_id=generation.id,
                generated_at=generation.generated_at,
                folder_id=upload_result["folder_id"],
                folder_url=upload_result["folder_url"],
            )
"""
pipelines/developer_tools_pipeline.py

Production orchestration pipeline for Developer Tools carousel posts.

End-to-End Flow:
1. Scheduler Lock & Correlation ID Generation
2. Google Sheets Draft Discovery & Idempotency Check
3. Render 9 Carousel Slides (via isolated DeveloperToolsRenderer)
4. Supabase Concurrent Upload (max_workers=3)
5. Public URL & Image Content Verification (HEAD + GET fallback)
6. Duplicate Publish Protection & Caption Resolution
7. Instagram Carousel Publication & Object Verification
8. Google Sheets Status & Metadata Update
9. Best-Effort Google Drive Archival
10. Lock Release
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Any

from sheet_api import get_draft_rows
from renderers.developer_tools_renderer import DeveloperToolsRenderer

from services.storage_service import SupabaseStorage
from services.instagram_service import InstagramService
from services.sheet_service import SheetService
from services.generation_service import GenerationService
from services.caption_service import CaptionService


logger = logging.getLogger(__name__)


SHEET_NAME = "Developer Tools"
LOCK_FILE = "publishing.lock"


def run() -> None:
    """
    Execute the Developer Tools production publishing workflow.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    correlation_id = f"PUB_{timestamp}"

    logger.info("==================================================")
    logger.info(f"[{correlation_id}] STARTING PIPELINE: {SHEET_NAME}")
    logger.info("==================================================")

    # --------------------------------------------------
    # Step 0: Scheduler Lock Protection
    # --------------------------------------------------
    if os.path.exists(LOCK_FILE):
        logger.warning(
            f"[{correlation_id}] Lock file '{LOCK_FILE}' exists. "
            "Another instance of the publishing pipeline may be running. Aborting cleanly."
        )
        return

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(f"PID: {os.getpid()}\nCorrelationID: {correlation_id}\nStartedAt: {datetime.now().isoformat()}\n")
        logger.info(f"[{correlation_id}] ✓ Acquired scheduler lock '{LOCK_FILE}'")

        # --------------------------------------------------
        # Step 1: Draft Discovery
        # --------------------------------------------------
        rows = get_draft_rows(sheet_name=SHEET_NAME)
        logger.info(f"[{correlation_id}] Found {len(rows)} draft rows in '{SHEET_NAME}'.")

        if not rows:
            logger.info(f"[{correlation_id}] No draft rows found. Pipeline finished cleanly.")
            return

        # Idempotency safety check
        for row in rows:
            status = str(row.get("Status", "")).strip().lower()
            if status == "published":
                logger.warning(
                    f"[{correlation_id}] Row {row.get('_row')} is already marked 'Published'. "
                    "Aborting pipeline to prevent duplicate publication."
                )
                return

        sheet = SheetService()
        generation = GenerationService()

        # --------------------------------------------------
        # Step 2: Rendering
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Transitioning rows -> Rendering")
        sheet.update_rows_status(rows, "Rendering", sheet_name=SHEET_NAME)

        post_folder = os.path.join("output", f"DeveloperTools_{timestamp}")
        os.makedirs(post_folder, exist_ok=True)

        try:
            # 01_Cover.png
            shutil.copy2(
                "templates/developer_tools/Developer_Tools_Cover_Page.png",
                os.path.join(post_folder, "01_Cover.png"),
            )
            logger.info(f"[{correlation_id}] ✓ Rendered slide 01_Cover.png")

            # 02..08 Content slides via DeveloperToolsRenderer
            renderer = DeveloperToolsRenderer()
            for index, row in enumerate(rows):
                filename = f"{index + 2:02d}_Content.png"
                output_path = os.path.join(post_folder, filename)
                renderer.render(row, output_path)
                logger.info(f"[{correlation_id}] ✓ Rendered slide {filename}")

            # 09_CTA.png
            shutil.copy2(
                "templates/shared/cta.png",
                os.path.join(post_folder, "09_CTA.png"),
            )
            logger.info(f"[{correlation_id}] ✓ Rendered slide 09_CTA.png")

        except Exception as exc:
            logger.error(f"[{correlation_id}] Rendering failed: {exc}", exc_info=True)
            sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
            return

        logger.info(f"[{correlation_id}] Transitioning rows -> Rendered")
        sheet.update_rows_status(rows, "Rendered", sheet_name=SHEET_NAME)
        sheet.write_generation_metadata(rows, generation, sheet_name=SHEET_NAME)

        # --------------------------------------------------
        # Step 3: Supabase Storage Upload
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Transitioning rows -> Uploading")
        sheet.update_rows_status(rows, "Uploading", sheet_name=SHEET_NAME)

        try:
            storage = SupabaseStorage()
            date_path = datetime.now().strftime("%Y/%m/%d")
            remote_prefix = f"{date_path}/{generation.id}"

            upload_result = storage.upload_folder(
                local_folder=post_folder,
                remote_prefix=remote_prefix,
                max_workers=3,
            )

            if not upload_result.get("success"):
                error_msg = upload_result.get("error", "Unknown upload error")
                logger.error(f"[{correlation_id}] Supabase upload failed: {error_msg}")
                sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
                return

            urls: List[str] = upload_result.get("urls", [])
            if len(urls) < 2:
                logger.error(f"[{correlation_id}] Expected at least 2 uploaded files, got {len(urls)}.")
                sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
                return

        except Exception as exc:
            logger.error(f"[{correlation_id}] Supabase storage service exception: {exc}", exc_info=True)
            sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
            return

        # --------------------------------------------------
        # Step 4: Verification of Uploaded Public URLs
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Verifying public accessibility and Content-Type of all uploaded slides...")
        for idx, url in enumerate(urls, start=1):
            is_valid = storage.verify_url(url)
            if not is_valid:
                logger.error(f"[{correlation_id}] Verification check failed for slide {idx}: {url}")
                sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
                return

        logger.info(f"[{correlation_id}] Transitioning rows -> Uploaded")
        sheet.update_rows_status(rows, "Uploaded", sheet_name=SHEET_NAME)

        # --------------------------------------------------
        # Step 5: Duplicate Publish Protection & Caption Resolution
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Transitioning rows -> Publishing")
        sheet.update_rows_status(rows, "Publishing", sheet_name=SHEET_NAME)

        try:
            # Check if any row already has an Instagram Media ID from a prior attempt prior to power outage/crash
            existing_media_id = next(
                (str(r.get("Instagram Media ID", "")).strip() for r in rows if str(r.get("Instagram Media ID", "")).strip()),
                None
            )
            if existing_media_id:
                logger.warning(
                    f"[{correlation_id}] Duplicate Publish Protection: Row already has Instagram Media ID '{existing_media_id}'. "
                    "Skipping Instagram graph publication to avoid reposting. Proceeding directly to metadata sync."
                )
                media_id = existing_media_id
                permalink = next(
                    (str(r.get("Instagram Post URL", "")).strip() for r in rows if str(r.get("Instagram Post URL", "")).strip()),
                    f"https://www.instagram.com/p/{media_id}/"
                )
            else:
                caption_service = CaptionService()
                first_row = rows[0] if rows else None
                caption = caption_service.get_caption(row=first_row, post_name=SHEET_NAME)

                instagram = InstagramService()
                publish_result = instagram.publish_carousel(image_urls=urls, caption=caption)

                if not publish_result.get("success"):
                    error_msg = publish_result.get("error", "Unknown publishing error")
                    logger.error(f"[{correlation_id}] Instagram carousel publication failed: {error_msg}")
                    sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
                    return

                media_id = publish_result.get("media_id", "")
                permalink = publish_result.get("permalink", "")
                if not permalink and media_id:
                    permalink = f"https://www.instagram.com/p/{media_id}/"

                if not media_id:
                    logger.error(f"[{correlation_id}] Publish result reported success but returned no media_id.")
                    sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
                    return

        except Exception as exc:
            logger.error(f"[{correlation_id}] Instagram publishing exception: {exc}", exc_info=True)
            sheet.mark_rows_failed(rows, sheet_name=SHEET_NAME)
            return

        # --------------------------------------------------
        # Step 6: Google Sheets Publishing Metadata Update
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Updating Google Sheets with Published status and permalink...")
        sheet.write_publishing_metadata(
            rows=rows,
            media_id=media_id,
            permalink=permalink,
            sheet_name=SHEET_NAME,
        )

        # --------------------------------------------------
        # Step 7: Best-Effort Google Drive Archival
        # --------------------------------------------------
        logger.info(f"[{correlation_id}] Performing best-effort Google Drive archival...")
        try:
            from services.drive_service import DriveService
            drive = DriveService()
            drive_result = drive.upload(post_folder)
            if drive_result and drive_result.get("success"):
                sheet.write_drive_metadata(
                    rows=rows,
                    drive_result=drive_result,
                    sheet_name=SHEET_NAME,
                )
                logger.info(f"[{correlation_id}] ✓ Google Drive archive completed successfully.")
            else:
                logger.warning(f"[{correlation_id}] Google Drive archive returned non-success: {drive_result}")
        except Exception as exc:
            # Drive failure is non-blocking since Instagram publication already succeeded
            logger.warning(
                f"[{correlation_id}] Best-effort Google Drive archival encountered an exception (non-blocking): {exc}"
            )

        logger.info("==================================================")
        logger.info(f"[{correlation_id}] PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("==================================================")

    finally:
        # Release scheduler lock
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
                logger.info(f"[{correlation_id}] ✓ Released scheduler lock '{LOCK_FILE}'")
            except Exception as lock_exc:
                logger.error(f"[{correlation_id}] Failed to release lock '{LOCK_FILE}': {lock_exc}")
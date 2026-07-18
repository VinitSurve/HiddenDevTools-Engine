"""
services/caption_service.py

Responsible for generating or resolving the Instagram post caption.

Order of precedence:
1. Dedicated 'Caption' column on the draft row (if present and non-empty)
2. Today's schedule configuration from 'Publishing Calendar' (if 'Caption' configured)
3. Fallback to DEFAULT_CAPTION_TEMPLATE from settings.py
"""

import logging
from typing import Dict, Any, Optional

from settings import DEFAULT_CAPTION_TEMPLATE
from schedule import get_today_schedule

logger = logging.getLogger(__name__)


class CaptionService:
    """
    Resolves the Instagram carousel caption based on configured precedence rules.
    """

    def get_caption(
        self,
        row: Optional[Dict[str, Any]] = None,
        post_name: str = "Developer Tools",
    ) -> str:
        """
        Get the appropriate caption for the post.
        """
        # 1. Check if the draft row directly specifies a caption
        if row and "Caption" in row and str(row["Caption"]).strip():
            caption = str(row["Caption"]).strip()
            logger.info("Using caption from draft row 'Caption' column.")
            return caption

        # 2. Check today's schedule from Publishing Calendar
        try:
            schedule_row = get_today_schedule()
            if schedule_row and "Caption" in schedule_row and str(schedule_row["Caption"]).strip():
                caption = str(schedule_row["Caption"]).strip()
                logger.info("Using caption configured in Publishing Calendar.")
                return caption
        except Exception as exc:
            logger.warning(f"Could not inspect Publishing Calendar for caption: {exc}")

        # 3. Fallback to default template in settings.py
        logger.info("Using DEFAULT_CAPTION_TEMPLATE from settings.py as fallback.")
        return DEFAULT_CAPTION_TEMPLATE

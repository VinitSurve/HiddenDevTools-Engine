import logging
from typing import List

logger = logging.getLogger(__name__)

class SchemaViolationError(Exception):
    """Raised when Google Sheet headers do not exactly match expected headers in strict ordered equality."""
    pass

EXPECTED_HEADERS = {
    "Github Repos": [
        "ID", "Resource Name", "Link", "Short Description", "Pricing", "Difficulty",
        "Slide Number", "Why it Matters", "Best for 1", "Best for 2", "Best for 3",
        "Rating", "Status", "Post", "Generated At", "Published At", "Generation ID"
    ],
    "Prompt Library": [
        "ID", "Prompt Title", "Slide Number", "Prompt Number", "Prompt",
        "Best For 1", "Best For 2", "Best For 3", "Expected Output",
        "Status", "Post", "Generated At", "Published At", "Generation ID"
    ],
    "Tools & Websites": [
        "ID", "Tool Name", "Website", "Short Description", "Category", "Pricing",
        "Platform", "Best for 1", "Best for 2", "Best for 3",
        "Rating", "Status", "Post", "Generated At", "Published At", "Generation ID", "Slide Number"
    ],
    "Developer Tools": [
        "ID", "Tool Name", "Website", "Category", "License", "Slide Number",
        "Short Description", "Why Developers Love it", "Best for 1", "Best for 2", "Best for 3",
        "Rating", "Status", "Post", "Generated At", "Published At", "Generation ID",
        "Drive Folder ID", "Drive Folder URl"
    ],
    "Free Alternatives": [
        "ID", "Alternative Name", "Replaces", "Website", "Pricing", "Category",
        "Slide Number", "Why Switch", "Best For 1", "Best For 2", "Best For 3",
        "Rating", "Status", "Post", "Generated At", "Published At", "Generation ID"
    ],
    "Career Resources": [
        "ID", "Resource Name", "Website", "Category", "Free/Paid", "Slide Number",
        "Best For 1", "Best For 2", "Best For 3", "Why Use It",
        "Rating", "Status", "Post", "Generated At", "Published At", "Generation ID"
    ],
    "Publishing Calendar": [
        "ID", "Day", "Sheet Name", "Template", "Drive Folder", "Publish Time", "Enabled"
    ]
}

class SchemaValidator:
    @staticmethod
    def validate_sheet_headers(sheet_name: str, actual_headers: List[str]) -> None:
        """
        Validate that the sheet's actual headers match EXPECTED_HEADERS exactly in ordered equality.
        Rejects missing, extra, renamed, miscapitalized, misspaced, or out-of-order columns.
        """
        if sheet_name not in EXPECTED_HEADERS:
            logger.error(f"SHEET_SCHEMA_VALIDATION_FAILED: Unknown sheet_name '{sheet_name}'.")
            raise SchemaViolationError(f"Unknown sheet_name: {sheet_name}")

        expected = EXPECTED_HEADERS[sheet_name]
        if actual_headers == expected:
            return

        missing_headers = [h for h in expected if h not in actual_headers]
        extra_headers = [h for h in actual_headers if h not in expected]
        order_mismatch = (set(actual_headers) == set(expected) and actual_headers != expected)

        logger.error(
            f"SHEET_SCHEMA_VALIDATION_FAILED: sheet_name='{sheet_name}', "
            f"expected_headers={expected}, actual_headers={actual_headers}, "
            f"missing_headers={missing_headers}, extra_headers={extra_headers}, "
            f"order_mismatch={order_mismatch}"
        )
        raise SchemaViolationError(
            f"Schema violation for sheet '{sheet_name}'. "
            f"missing={missing_headers}, extra={extra_headers}, order_mismatch={order_mismatch}"
        )

from sheet_api import (
    get_draft_rows,
    mark_ready
)

rows = get_draft_rows(
    limit=7
)

mark_ready(
    rows,
    "Post_002"
)
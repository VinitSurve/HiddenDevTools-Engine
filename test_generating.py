from sheet_api import (
    get_draft_rows,
    mark_generating
)

rows = get_draft_rows(
    limit=7
)

mark_generating(
    rows
)
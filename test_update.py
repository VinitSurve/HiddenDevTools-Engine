from sheet_api import open_sheet

ws = open_sheet()

ws.acell("R2").value
update_cell(
    row_number,
    STATUS_COLUMN,
    status
)

print("✅ Updated successfully!")
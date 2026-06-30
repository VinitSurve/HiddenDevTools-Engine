from sheet_api import open_sheet

ws = open_sheet()

ws.acell("R2").value

ws.update_acell(
    "R2",
    "Hello"
)

print("✅ Updated successfully!")
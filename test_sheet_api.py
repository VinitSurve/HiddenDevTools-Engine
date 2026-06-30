from sheet_api import open_sheet

ws = open_sheet()

print("Connected Successfully!")
print()

print("Sheet Title:")
print(ws.title)
print()

print("Rows:")
print(ws.row_count)

print()

print("Columns:")
print(ws.col_count)
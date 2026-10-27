import sheet_api

ws = sheet_api.open_sheet('Career Resources')
cell_list = ws.findall("Generating")
updated = 0
for cell in cell_list:
    if ws.cell(1, cell.col).value == "Status":
        ws.update_cell(cell.row, cell.col, "Draft")
        updated += 1

print(f"Updated {updated} cells")

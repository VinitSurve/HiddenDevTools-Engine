from sheet_api import get_draft_rows

rows = get_draft_rows()

print()

for row in rows:

    print(
        row["ID"],
        row["Resource Name"],
        row["Status"]
    )
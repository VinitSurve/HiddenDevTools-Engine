import os

from drive import (
    create_folder,
    upload_file,
)

folder = create_folder(
    "Upload_Test"
)

folder_id = folder["id"]

for filename in os.listdir(
    "output/Developer_Test"
):

    filepath = os.path.join(
        "output/Developer_Test",
        filename,
    )

    result = upload_file(
        filepath,
        folder_id,
    )

    print(result)
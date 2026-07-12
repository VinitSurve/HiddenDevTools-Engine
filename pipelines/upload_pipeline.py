import os

from drive import (
    create_folder,
    upload_file,
)


def upload_post(post_folder):

    folder_name = os.path.basename(post_folder)

    folder = create_folder(folder_name)

    folder_id = folder["id"]

    print(f"✓ Drive Folder: {folder_name}")

    uploaded = []

    files = sorted(os.listdir(post_folder))

    for filename in files:

        filepath = os.path.join(
            post_folder,
            filename,
        )

        result = upload_file(
            filepath,
            folder_id,
        )

        uploaded.append(result)

        print(f"✓ Uploaded {filename}")

    return {
        "success": True,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "folder_url": (
            f"https://drive.google.com/drive/folders/{folder_id}"
        ),
        "uploaded_count": len(uploaded),
        "files": uploaded,
    }
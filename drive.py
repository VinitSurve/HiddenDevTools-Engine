from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import DRIVE_ROOT_FOLDER_ID
from drive_auth import get_credentials


drive = build(
    "drive",
    "v3",
    credentials=get_credentials(),
)


def create_folder(
    folder_name,
    parent_id=DRIVE_ROOT_FOLDER_ID,
):

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    folder = drive.files().create(
        body=metadata,
        fields="id,name",
    ).execute()

    return folder


def upload_file(
    filepath,
    folder_id,
):

    metadata = {
        "name": filepath.split("\\")[-1],
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        filepath,
        resumable=True,
    )

    file = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    return file
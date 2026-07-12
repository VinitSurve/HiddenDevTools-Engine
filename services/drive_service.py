from pipelines.upload_pipeline import upload_post


class DriveService:

    def upload(
        self,
        post_folder,
    ):

        return upload_post(post_folder)
from config.app_config import config
from features.publishing.contracts import (
    PublicationRepository,
    UploadedArtifactRepository,
    UploadAttemptRepository,
    InstagramPublicationAttemptRepository,
)

class RepositoryProvider:
    @staticmethod
    def get_publication_repository() -> PublicationRepository:
        backend = getattr(config.runtime, "persistence_backend", "sqlite")
        if backend == "supabase":
            from features.publishing.supabase_publication_repository import SupabasePublicationRepository
            return SupabasePublicationRepository()
        else:
            from features.publishing.repository import SQLitePublicationRepository
            return SQLitePublicationRepository()

    @staticmethod
    def get_uploaded_artifact_repository() -> UploadedArtifactRepository:
        backend = getattr(config.runtime, "persistence_backend", "sqlite")
        if backend == "supabase":
            from features.publishing.supabase_uploaded_artifact_repository import SupabaseUploadedArtifactRepository
            return SupabaseUploadedArtifactRepository()
        else:
            from features.publishing.uploaded_artifact_repository import SQLiteUploadedArtifactRepository
            return SQLiteUploadedArtifactRepository()

    @staticmethod
    def get_upload_attempt_repository() -> UploadAttemptRepository:
        backend = getattr(config.runtime, "persistence_backend", "sqlite")
        if backend == "supabase":
            from features.publishing.supabase_upload_attempt_repository import SupabaseUploadAttemptRepository
            return SupabaseUploadAttemptRepository()
        else:
            from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
            return SQLiteUploadAttemptRepository()

    @staticmethod
    def get_instagram_attempt_repository() -> InstagramPublicationAttemptRepository:
        backend = getattr(config.runtime, "persistence_backend", "sqlite")
        if backend == "supabase":
            from features.publishing.supabase_instagram_attempt_repository import SupabaseInstagramPublicationAttemptRepository
            return SupabaseInstagramPublicationAttemptRepository()
        else:
            from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository
            return SQLiteInstagramPublicationAttemptRepository()

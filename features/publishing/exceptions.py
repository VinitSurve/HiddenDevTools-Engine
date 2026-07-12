class PublicationConflictError(Exception):
    """Raised when record_publication is called with an existing generation_id but differing media_id or permalink."""
    pass

class UploadArtifactConflictError(Exception):
    """Raised when record_artifacts is called with an existing generation_id but differing artifact public_urls or slides."""
    pass

class UploadedArtifactValidationError(Exception):
    """Raised when input validation fails before transaction execution in UploadedArtifactRepository.record_artifacts."""
    pass

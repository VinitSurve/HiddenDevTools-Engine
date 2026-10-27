from abc import ABC, abstractmethod
from typing import Optional, Dict, List

class PublicationRepository(ABC):
    @abstractmethod
    def get_by_generation_id(self, generation_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def record_publication(self, generation_id: str, media_id: str, permalink: str, published_at: str) -> None:
        pass

    @abstractmethod
    def update_sheet_sync_state(self, generation_id: str, state: str, error: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def get_pending_sheet_updates(self) -> List[Dict]:
        pass

    @abstractmethod
    def get_recent_publications(self, limit: int = 10) -> List[Dict]:
        pass


class UploadedArtifactRepository(ABC):
    @abstractmethod
    def get_by_generation_id(self, generation_id: str) -> List[Dict]:
        pass

    @abstractmethod
    def record_artifacts(self, generation_id: str, artifacts: List[Dict], uploaded_at: str) -> None:
        pass


class UploadAttemptRepository(ABC):
    @abstractmethod
    def record_attempt(self, generation_id: str, slide_number: int, remote_path: str, sha256_hash: str, public_url: str, uploaded_at: str) -> None:
        pass

    @abstractmethod
    def get_attempt(self, generation_id: str, slide_number: Optional[int] = None) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_all_attempts(self, generation_id: str) -> List[Dict]:
        pass


class InstagramPublicationAttemptRepository(ABC):
    @abstractmethod
    def get_attempt(self, generation_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def create_attempt(self, generation_id: str, child_creation_ids: List[str]) -> None:
        pass

    @abstractmethod
    def transition_state(self, generation_id: str, new_state: str, **kwargs) -> None:
        pass

from abc import ABC, abstractmethod
from models.publish_job import PublishJob
from models.publish_result import PublishResult

class Publisher(ABC):
    """
    Abstract interface for all social media publishers.
    """
    @abstractmethod
    def publish(self, job: PublishJob) -> PublishResult:
        pass

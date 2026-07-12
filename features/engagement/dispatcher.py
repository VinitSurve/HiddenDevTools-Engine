from abc import ABC, abstractmethod
from fastapi import BackgroundTasks

class QueueDispatcher(ABC):
    @abstractmethod
    def dispatch(self, comment_id: str):
        pass

class FastAPIDispatcher(QueueDispatcher):
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def dispatch(self, comment_id: str):
        from features.engagement.worker import DMWorker
        from features.engagement.repository import DeduplicationRepository
        from services.instagram_service import InstagramService
        
        # Instantiate worker and schedule execution
        repo = DeduplicationRepository()
        instagram_service = InstagramService()
        worker = DMWorker(repo, instagram_service)
        
        self.background_tasks.add_task(worker.process_queue)

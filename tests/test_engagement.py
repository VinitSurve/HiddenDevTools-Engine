import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from config import EngagementMode
from models.webhook_event import WebhookEvent
from features.engagement.repository import DeduplicationRepository
from features.engagement.keyword_matcher import KeywordMatcher
from features.engagement.comment_processor import CommentProcessor
from features.engagement.models import DMStatus, MessageResult
from features.engagement.dispatcher import QueueDispatcher
from features.engagement.worker import DMWorker

class MockDispatcher(QueueDispatcher):
    def __init__(self):
        self.dispatched = []
    
    def dispatch(self, comment_id: str):
        self.dispatched.append(comment_id)

class MockInstagramService:
    def __init__(self, success: bool, retryable: bool = False):
        self.success = success
        self.retryable = retryable
        self.sent_to = []
        
    def send_message(self, recipient_id: str, text: str):
        self.sent_to.append(recipient_id)
        if self.success:
            return MessageResult(True, "msg1", None, None, False, 200, "{}")
        else:
            return MessageResult(False, None, "error", "error msg", self.retryable, 400, "{}")

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """Ensure tests run against a test database"""
    import uuid
    test_db_path = f"test_engagement_{uuid.uuid4().hex}.db"
    monkeypatch.setattr("features.engagement.repository.SQLITE_DB_PATH", test_db_path)
    
    # Run tests
    yield
    
    # Cleanup
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except PermissionError:
            pass

def create_mock_event(comment_id: str, text: str, user_id: str = "u1", media_id: str = "m1") -> WebhookEvent:
    return WebhookEvent(
        object_type="instagram",
        event_type="comments",
        webhook_id="w1",
        correlation_id="c1",
        comment_id=comment_id,
        media_id=media_id,
        user_id=user_id,
        username="testuser",
        text=text,
        timestamp=datetime.now(),
        raw_payload={}
    )

def test_duplicate_webhook_detection():
    repo = DeduplicationRepository()
    dispatcher = MockDispatcher()
    processor = CommentProcessor(repo, dispatcher)
    
    event1 = create_mock_event("c1", "dev")
    processor.process_event(event1)
    assert repo.has_processed_comment("c1") is True
    
    # Sending same comment_id again
    processor.process_event(event1) 
    # Still only dispatched once
    assert len(dispatcher.dispatched) == 1

def test_duplicate_user_detection():
    repo = DeduplicationRepository()
    dispatcher = MockDispatcher()
    processor = CommentProcessor(repo, dispatcher)
    
    event1 = create_mock_event("c1", "dev", user_id="u1", media_id="m1")
    processor.process_event(event1)
    
    event2 = create_mock_event("c2", "dev", user_id="u1", media_id="m1")
    processor.process_event(event2)
    
    with sqlite3.connect(repo.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM processed_comments WHERE comment_id = 'c2'")
        status = cursor.fetchone()[0]
        assert status == DMStatus.FAILED.value
    
    # Second wasn't dispatched
    assert len(dispatcher.dispatched) == 1

def test_worker_success():
    repo = DeduplicationRepository()
    dispatcher = MockDispatcher()
    processor = CommentProcessor(repo, dispatcher)
    
    event = create_mock_event("c3", "dev", user_id="u3", media_id="m3")
    processor.process_event(event)
    
    ig_service = MockInstagramService(success=True)
    worker = DMWorker(repo, ig_service)
    
    worker.process_queue()
    
    assert len(ig_service.sent_to) == 1
    
    with sqlite3.connect(repo.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM processed_comments WHERE comment_id = 'c3'")
        assert cursor.fetchone()[0] == DMStatus.SENT.value

def test_worker_retry():
    repo = DeduplicationRepository()
    dispatcher = MockDispatcher()
    processor = CommentProcessor(repo, dispatcher)
    
    event = create_mock_event("c4", "dev", user_id="u4", media_id="m4")
    processor.process_event(event)
    
    ig_service = MockInstagramService(success=False, retryable=True)
    worker = DMWorker(repo, ig_service)
    
    worker.process_queue()
    
    assert len(ig_service.sent_to) == 1
    
    with sqlite3.connect(repo.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, attempt_count FROM processed_comments WHERE comment_id = 'c4'")
        status, attempt = cursor.fetchone()
        assert status == DMStatus.RETRYING.value
        assert attempt == 1

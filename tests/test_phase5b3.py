import pytest
from unittest.mock import patch, MagicMock
from models.publish_job import PublishJob
from models.publish_result import PublishResult
from models.artifact import Artifact
from scheduler.instagram_publisher import InstagramGraphPublisher
from services.completion_service import CompletionService

def test_instagram_publisher_idempotency():
    publisher = InstagramGraphPublisher()
    publisher.pub_repo = MagicMock()
    # Mock that it's already published
    publisher.pub_repo.get_by_generation_id.return_value = {
        "media_id": "12345",
        "permalink": "http://ig/12345",
        "published_at": "2026-07-18 12:00:00"
    }
    
    job = PublishJob(
        generation_id="GEN_123", batch_id="GEN_123", date="2026-07-18", weekday=0,
        niche="github_repo", sheet_name="Sheet", caption="Test", hashtags=[],
        artifacts=[Artifact(1, "f.png", "p", "sha", "mime", "store", "url")]
    )
    
    result = publisher.publish(job)
    
    assert result.success is True
    assert result.provider == "Instagram"
    assert result.provider_post_id == "12345"
    assert result.permalink == "http://ig/12345"
    assert result.attempt_count == 0
    assert "Idempotent success" in result.provider_response["message"]
    
@patch("services.completion_service.open_sheet")
def test_completion_service_success(mock_open_sheet):
    service = CompletionService()
    service.pub_repo = MagicMock()
    
    mock_ws = MagicMock()
    mock_open_sheet.return_value = mock_ws
    mock_ws.get_all_records.return_value = [{"Generation ID": "GEN_123", "_row": 2}]
    
    job = PublishJob(
        generation_id="GEN_123", batch_id="GEN_123", date="2026-07-18", weekday=0,
        niche="github_repo", sheet_name="Sheet", caption="Test", hashtags=[], artifacts=[]
    )
    
    result = PublishResult(
        success=True, provider="Instagram", provider_post_id="999", permalink="url", published_at="2026-07-18 12:00:00"
    )
    
    service.complete(job, result)
    
    service.pub_repo.record_publication.assert_called_once_with(
        generation_id="GEN_123", media_id="999", permalink="url", published_at=result.published_at or "2026-07-18 12:00:00" # fallback handles empty
    )
    mock_open_sheet.assert_called_once_with("Sheet")
    mock_ws.get_all_records.assert_called_once()

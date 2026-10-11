import pytest
from unittest.mock import Mock, patch, call
from services.instagram_service import InstagramService
import requests

def test_scenario_007_008_009_010_crash_restart_publish_requested():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_REQUESTED'}
    
    svc = InstagramService(access_token="test", ig_user_id="123")
    svc.publish = Mock()
    svc.create_media_container = Mock()
    svc.create_carousel = Mock()
    
    res = svc.publish_carousel("GEN_1", ["url1", "url2"], attempt_repo)
    
    assert res["success"] is False
    svc.publish.assert_not_called()
    attempt_repo.transition_state.assert_called_with("GEN_1", "PUBLISH_OUTCOME_UNKNOWN")
    svc.create_media_container.assert_not_called()
    svc.create_carousel.assert_not_called()

def test_scenario_014_015_016_017_authorized_retry():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {
        'publish_state': 'PUBLISH_RETRY_AUTHORIZED',
        'carousel_creation_id': 'CAROUSEL_ID'
    }
    
    svc = InstagramService(access_token="test", ig_user_id="123")
    svc.check_publishing_limit = Mock(return_value={"quota_usage": 0})
    svc.publish = Mock(return_value={"success": True, "media_id": "NEW_MEDIA_ID"})
    svc.verify_publication = Mock(return_value={"verified": True, "permalink": "new_link", "timestamp": "time"})
    svc.create_media_container = Mock()
    svc.create_carousel = Mock()
    
    manager = Mock()
    manager.attach_mock(attempt_repo.transition_state, 'transition_state')
    manager.attach_mock(svc.publish, 'publish')
    
    res = svc.publish_carousel("GEN_1", ["url1", "url2"], attempt_repo)
    
    assert res["success"] is True
    svc.publish.assert_called_once_with("CAROUSEL_ID")
    svc.create_media_container.assert_not_called()
    svc.create_carousel.assert_not_called()
    
    expected_calls = [
        call.transition_state("GEN_1", "PUBLISH_REQUESTED"),
        call.publish("CAROUSEL_ID"),
        call.transition_state("GEN_1", "PUBLISHED_MEDIA_KNOWN", media_id="NEW_MEDIA_ID")
    ]
    manager.assert_has_calls(expected_calls, any_order=False)

def test_scenario_018_authorized_retry_timeout():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {
        'publish_state': 'PUBLISH_RETRY_AUTHORIZED',
        'carousel_creation_id': 'CAROUSEL_ID'
    }
    
    svc = InstagramService(access_token="test", ig_user_id="123")
    svc.check_publishing_limit = Mock(return_value={"quota_usage": 0})
    svc.publish = Mock(side_effect=requests.exceptions.Timeout("Timeout"))
    
    res = svc.publish_carousel("GEN_1", ["url1", "url2"], attempt_repo)
    
    assert res["success"] is False
    attempt_repo.transition_state.assert_called_with("GEN_1", "PUBLISH_OUTCOME_UNKNOWN")

def test_scenario_022_023_024_025_026_published_media_known_recovery():
    from pipelines.daily_carousel_pipeline import DailyCarouselPipeline
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'KNOWN'}
    
    svc = InstagramService(access_token="test", ig_user_id="123")
    svc.publish = Mock()
    svc.create_media_container = Mock()
    svc.create_carousel = Mock()
    
    def fake_publisher(*args):
        return svc.publish_carousel("GEN_1", ["url1"], attempt_repo)
        
    pipeline = DailyCarouselPipeline(publisher_cb=fake_publisher)
    res = pipeline._execute_active_batch("Sheet", "GEN_1", "Uploaded", Mock(row_values=Mock(return_value=["Status", "Post", "Generated At", "Generation ID"])), "tmpl")
    
    svc.publish.assert_not_called()
    svc.create_media_container.assert_not_called()
    svc.create_carousel.assert_not_called()
    assert attempt_repo.transition_state.call_count == 0 

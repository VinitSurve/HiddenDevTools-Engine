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
        call.transition_state("GEN_1", "PUBLISHED_MEDIA_KNOWN", media_id="NEW_MEDIA_ID"),
        call.transition_state("GEN_1", "PUBLISHED_VERIFIED", media_id="NEW_MEDIA_ID", permalink="new_link")
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

def test_verification_failure_prevents_verified_transition():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {
        'publish_state': 'PUBLISH_RETRY_AUTHORIZED',
        'carousel_creation_id': 'CAROUSEL_ID'
    }
    svc = InstagramService(access_token="test", ig_user_id="123")
    svc.check_publishing_limit = Mock(return_value={"quota_usage": 0})
    svc.publish = Mock(return_value={"success": True, "media_id": "MEDIA_FAIL_VERIFY"})
    # verify_publication returns verified = False
    svc.verify_publication = Mock(return_value={"verified": False, "permalink": ""})
    svc.get_permalink = Mock(return_value="")

    res = svc.publish_carousel("GEN_FAIL", ["u1", "u2"], attempt_repo)

    # Must report failure / unverified and NOT transition to PUBLISHED_VERIFIED
    assert res["success"] is False
    assert res["verified"] is False
    # Verified transition must NOT be called
    for call_item in attempt_repo.transition_state.call_args_list:
        assert call_item[0][1] != 'PUBLISHED_VERIFIED'

def test_concurrent_workers_claim_publish_requested():
    from features.publishing.instagram_attempt_repository import InstagramAttemptConflictError
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {
        'publish_state': 'PUBLISH_RETRY_AUTHORIZED',
        'carousel_creation_id': 'CAROUSEL_ID'
    }

    # First worker claims PUBLISH_REQUESTED, second worker fails with InstagramAttemptConflictError
    claimed = set()
    def mock_transition(gen, state, **kwargs):
        if state == 'PUBLISH_REQUESTED':
            if gen in claimed:
                raise InstagramAttemptConflictError("Claim lost")
            claimed.add(gen)
        return None

    attempt_repo.transition_state.side_effect = mock_transition

    svc1 = InstagramService(access_token="test", ig_user_id="123")
    svc1.check_publishing_limit = Mock(return_value={"quota_usage": 0})
    svc1.publish = Mock(return_value={"success": True, "media_id": "MED_1"})
    svc1.verify_publication = Mock(return_value={"verified": True, "permalink": "p1", "timestamp": "t1"})

    svc2 = InstagramService(access_token="test", ig_user_id="123")
    svc2.check_publishing_limit = Mock(return_value={"quota_usage": 0})
    svc2.publish = Mock(return_value={"success": True, "media_id": "MED_2"})

    # Worker 1 runs
    res1 = svc1.publish_carousel("GEN_CONCURRENT", ["u1", "u2"], attempt_repo)
    assert res1["success"] is True
    svc1.publish.assert_called_once()

    # Worker 2 runs: claim lost
    res2 = svc2.publish_carousel("GEN_CONCURRENT", ["u1", "u2"], attempt_repo)
    assert res2["success"] is False
    assert "Failed to claim publish lock" in res2["error"]
    svc2.publish.assert_not_called()

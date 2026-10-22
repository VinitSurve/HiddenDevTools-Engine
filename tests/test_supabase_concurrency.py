import pytest
from unittest.mock import Mock, patch
from features.publishing.supabase_instagram_attempt_repository import SupabaseInstagramPublicationAttemptRepository
from features.publishing.instagram_attempt_repository import InstagramAttemptConflictError
from services.instagram_service import InstagramService

def test_supabase_publish_requested_atomic_claim(monkeypatch):
    repo = SupabaseInstagramPublicationAttemptRepository()

    mock_get_resp = Mock(status_code=200)
    mock_get_resp.json.return_value = [{
        "generation_id": "GEN_ATOMIC",
        "publish_state": "CAROUSEL_CREATED",
        "media_id": None
    }]

    mock_patch_resp = Mock(status_code=200)
    mock_patch_resp.json.return_value = [{
        "generation_id": "GEN_ATOMIC",
        "publish_state": "PUBLISH_REQUESTED"
    }]

    with patch("requests.get", return_value=mock_get_resp), \
         patch("requests.patch", return_value=mock_patch_resp) as mock_patch:
        repo.transition_state("GEN_ATOMIC", "PUBLISH_REQUESTED")

        # Verify conditional filter was included in PATCH URL
        called_url = mock_patch.call_args[0][0]
        assert "publish_state=in.(CAROUSEL_CREATED,PUBLISH_RETRY_AUTHORIZED)" in called_url

def test_supabase_concurrency_two_workers_at_most_one_publishes(monkeypatch):
    repo = SupabaseInstagramPublicationAttemptRepository()

    state_store = {
        "generation_id": "GEN_RACE",
        "publish_state": "PUBLISH_RETRY_AUTHORIZED",
        "carousel_creation_id": "CAROUSEL_123",
        "media_id": None
    }

    def mock_get(url, **kwargs):
        resp = Mock(status_code=200)
        resp.json.return_value = [dict(state_store)]
        return resp

    def mock_patch_worker1(url, json=None, **kwargs):
        resp = Mock(status_code=200)
        if json:
            state_store.update(json)
        resp.json.return_value = [dict(state_store)]
        return resp

    def mock_patch_worker2(url, json=None, **kwargs):
        resp = Mock(status_code=200)
        # Condition publish_state=in.(CAROUSEL_CREATED,PUBLISH_RETRY_AUTHORIZED) does NOT match
        # because Worker 1 already updated state_store["publish_state"] to PUBLISH_REQUESTED!
        resp.json.return_value = []
        return resp

    svc1 = InstagramService(access_token="tok1", ig_user_id="user1")
    svc1.check_publishing_limit = Mock(return_value={"success": True, "quota_usage": 0})
    svc1.publish = Mock(return_value={"success": True, "media_id": "MED_PUB_1"})
    svc1.verify_publication = Mock(return_value={"verified": True, "permalink": "link1", "timestamp": "t1"})

    svc2 = InstagramService(access_token="tok2", ig_user_id="user2")
    svc2.check_publishing_limit = Mock(return_value={"success": True, "quota_usage": 0})
    svc2.publish = Mock(return_value={"success": True, "media_id": "MED_PUB_2"})

    def mock_get_worker2(url, **kwargs):
        # Worker 2 read the attempt concurrently before Worker 1's patch took effect
        resp = Mock(status_code=200)
        resp.json.return_value = [{
            "generation_id": "GEN_RACE",
            "publish_state": "PUBLISH_RETRY_AUTHORIZED",
            "carousel_creation_id": "CAROUSEL_123",
            "media_id": None
        }]
        return resp

    with patch("requests.get", side_effect=mock_get):
        with patch("requests.patch", side_effect=mock_patch_worker1):
            res1 = svc1.publish_carousel("GEN_RACE", ["u1", "u2"], repo)
            assert res1["success"] is True
            svc1.publish.assert_called_once()

    with patch("requests.get", side_effect=mock_get_worker2):
        with patch("requests.patch", side_effect=mock_patch_worker2):
            res2 = svc2.publish_carousel("GEN_RACE", ["u1", "u2"], repo)
            assert res2["success"] is False
            assert "Failed to claim publish lock" in res2["error"]
            svc2.publish.assert_not_called()

def test_supabase_repeated_verified_transition_idempotent():
    repo = SupabaseInstagramPublicationAttemptRepository()

    mock_get_resp = Mock(status_code=200)
    mock_get_resp.json.return_value = [{
        "generation_id": "GEN_VERIFIED",
        "publish_state": "PUBLISHED_VERIFIED",
        "media_id": "MED_EXISTING",
        "permalink": "https://ig.com/p/1"
    }]

    mock_patch_resp = Mock(status_code=200)
    mock_patch_resp.json.return_value = [{
        "generation_id": "GEN_VERIFIED",
        "publish_state": "PUBLISHED_VERIFIED"
    }]

    with patch("requests.get", return_value=mock_get_resp), \
         patch("requests.patch", return_value=mock_patch_resp):
        # Repeated call with same media_id must succeed without raising InvalidStateTransitionError
        repo.transition_state("GEN_VERIFIED", "PUBLISHED_VERIFIED", media_id="MED_EXISTING", permalink="https://ig.com/p/1")

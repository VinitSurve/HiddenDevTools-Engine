import pytest
import sqlite3
import datetime
from unittest.mock import Mock, patch
from requests.exceptions import HTTPError

from features.publishing.contracts import UploadAttemptRepository
from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
from features.publishing.supabase_upload_attempt_repository import SupabaseUploadAttemptRepository
from services.idempotency_service import check_already_published, derive_canonical_generation_id
from scheduler.orchestrator import SchedulerOrchestrator
from utils.timezone import IST


class TestUploadAttemptRepositoryContract:
    def test_sqlite_upload_attempt_repository_get_attempt_single_and_multi_arg(self):
        repo = SQLiteUploadAttemptRepository()

        # Before any attempts
        assert repo.get_attempt("GEN_001") is None
        assert repo.get_attempt("GEN_001", slide_number=1) is None
        assert repo.get_all_attempts("GEN_001") == []

        # Record slide 1 and slide 2
        repo.record_attempt(
            generation_id="GEN_001",
            slide_number=1,
            remote_path="tools/GEN_001/slide_1.png",
            sha256_hash="a" * 64,
            public_url="https://storage.mock/tools/GEN_001/slide_1.png",
            uploaded_at="2026-10-27T00:00:00Z"
        )
        repo.record_attempt(
            generation_id="GEN_001",
            slide_number=2,
            remote_path="tools/GEN_001/slide_2.png",
            sha256_hash="b" * 64,
            public_url="https://storage.mock/tools/GEN_001/slide_2.png",
            uploaded_at="2026-10-27T00:01:00Z"
        )

        # Single-argument get_attempt(generation_id) returns first attempt
        attempt_any = repo.get_attempt("GEN_001")
        assert attempt_any is not None
        assert attempt_any["remote_path"] in ("tools/GEN_001/slide_1.png", "tools/GEN_001/slide_2.png")

        # Two-argument get_attempt(generation_id, slide_number) returns specific slide
        attempt_s2 = repo.get_attempt("GEN_001", slide_number=2)
        assert attempt_s2 is not None
        assert attempt_s2["remote_path"] == "tools/GEN_001/slide_2.png"

        # get_all_attempts returns both
        all_attempts = repo.get_all_attempts("GEN_001")
        assert len(all_attempts) == 2
        assert all_attempts[0]["slide_number"] == 1
        assert all_attempts[1]["slide_number"] == 2

    @patch("requests.get")
    def test_supabase_upload_attempt_repository_get_attempt_single_and_multi_arg(self, mock_get):
        repo = SupabaseUploadAttemptRepository.__new__(SupabaseUploadAttemptRepository)
        repo.url = "https://mock.supabase.co/rest/v1/upload_attempts"
        repo.headers = {"apikey": "test"}

        # 1. get_attempt with 1 argument (slide_number=None) queries limit=1
        mock_resp_1 = Mock()
        mock_resp_1.json.return_value = [{
            "generation_id": "GEN_TEST",
            "slide_number": 1,
            "remote_path": "tools/GEN_TEST/slide_1.png",
            "sha256_hash": "c" * 64,
            "public_url": "https://storage.mock/tools/GEN_TEST/slide_1.png",
            "uploaded_at": "2026-10-27T00:00:00Z"
        }]
        mock_resp_1.raise_for_status = Mock()
        mock_get.return_value = mock_resp_1

        res = repo.get_attempt("GEN_TEST")
        assert res is not None
        assert res["slide_number"] == 1
        assert "limit=1" in mock_get.call_args[0][0]

        # 2. get_attempt with 2 arguments queries slide_number=eq.2
        mock_resp_2 = Mock()
        mock_resp_2.json.return_value = [{
            "generation_id": "GEN_TEST",
            "slide_number": 2,
            "remote_path": "tools/GEN_TEST/slide_2.png",
            "sha256_hash": "d" * 64,
            "public_url": "https://storage.mock/tools/GEN_TEST/slide_2.png",
            "uploaded_at": "2026-10-27T00:01:00Z"
        }]
        mock_resp_2.raise_for_status = Mock()
        mock_get.return_value = mock_resp_2

        res_2 = repo.get_attempt("GEN_TEST", slide_number=2)
        assert res_2 is not None
        assert res_2["slide_number"] == 2
        assert "slide_number=eq.2" in mock_get.call_args[0][0]


class TestCheckAlreadyPublishedStates:
    """
    Tests checking published, not-published, and backend-error states
    for idempotency verification.
    """

    # --- 1. Published States ---

    def test_published_via_publication_repo_canonical(self):
        mock_pub_repo = Mock()
        mock_pub_repo.get_by_generation_id.return_value = {
            "generation_id": "GEN_20261026_GITHUB_REPO",
            "media_id": "18999999999999",
            "permalink": "https://www.instagram.com/p/published_canon/",
            "published_at": "2026-10-26T13:30:00Z",
            "sheet_sync_state": "SUCCESS"
        }

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            pub_repo=mock_pub_repo
        )
        assert res["is_published"] is True
        assert res["media_id"] == "18999999999999"
        assert res["source"] == "pub_repo_canonical"
        assert res["has_error"] is False

    def test_published_via_publication_repo_recent_publication(self):
        mock_pub_repo = Mock()
        mock_pub_repo.get_by_generation_id.return_value = None
        mock_pub_repo.get_recent_publications.return_value = [
            {
                "generation_id": "GEN_OTHER_HASH",
                "media_id": "181234567890",
                "permalink": "https://www.instagram.com/p/recent_match/",
                "published_at": "2026-10-26T13:30:00+00:00",
                "sheet_sync_state": "SUCCESS"
            }
        ]

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            pub_repo=mock_pub_repo
        )
        assert res["is_published"] is True
        assert res["media_id"] == "181234567890"
        assert res["source"] == "pub_repo_recent_date"
        assert res["has_error"] is False

    def test_published_via_instagram_attempt_repo(self):
        mock_ig_repo = Mock()
        mock_ig_repo.get_attempt.return_value = {
            "generation_id": "GEN_20261026_GITHUB_REPO",
            "publish_state": "PUBLISHED_VERIFIED",
            "media_id": "18444444444444",
            "permalink": "https://www.instagram.com/p/ig_repo_verified/",
            "updated_at": "2026-10-26T13:35:00Z"
        }

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            instagram_attempt_repo=mock_ig_repo
        )
        assert res["is_published"] is True
        assert res["media_id"] == "18444444444444"
        assert res["source"] == "instagram_attempt_repo"
        assert res["has_error"] is False

    def test_published_via_google_sheets(self):
        mock_ws = Mock()
        mock_ws.get_all_records.return_value = [
            {
                "ID": "GH001",
                "Status": "Published",
                "Post": "https://www.instagram.com/p/sheet_published/",
                "Generation ID": "GEN_20261026_GITHUB_REPO",
                "Published At": "2026-10-26 19:00:00"
            }
        ]

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            sheet_name="Github Repos",
            worksheet=mock_ws
        )
        assert res["is_published"] is True
        assert res["media_id"] == "SHEET_VERIFIED"
        assert res["source"] == "google_sheets"
        assert res["has_error"] is False

    # --- 2. Not-Published States ---

    def test_not_published_clean_state(self):
        mock_pub_repo = Mock()
        mock_pub_repo.get_by_generation_id.return_value = None
        mock_pub_repo.get_recent_publications.return_value = []

        mock_ig_repo = Mock()
        mock_ig_repo.get_attempt.return_value = None

        mock_up_repo = Mock(spec=UploadAttemptRepository)
        mock_up_repo.get_attempt.return_value = None
        mock_up_repo.get_all_attempts.return_value = []

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            pub_repo=mock_pub_repo,
            instagram_attempt_repo=mock_ig_repo,
            upload_attempt_repo=mock_up_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is False
        assert res["error"] is None

    def test_not_published_when_upload_attempts_exist_but_not_published(self):
        """
        When slide images were uploaded to storage (upload attempts exist),
        but the post has not yet been published to Instagram, check_already_published
        must safely return is_published=False without raising TypeError or reporting false published.
        """
        mock_up_repo = Mock(spec=UploadAttemptRepository)
        # 1-argument get_attempt returns an upload attempt dict
        mock_up_repo.get_attempt.return_value = {
            "remote_path": "github_repos/GEN_001/slide_1.png",
            "sha256_hash": "e" * 64,
            "public_url": "https://mock.storage/slide_1.png",
            "uploaded_at": "2026-10-26T12:00:00Z"
        }

        # Passed as attempt_repo (simulating orchestrator passing self.attempt_repo)
        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            attempt_repo=mock_up_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is False
        assert res["error"] is None

    def test_not_published_when_instagram_attempt_in_progress(self):
        """
        When Instagram containers were created (e.g. CHILDREN_CREATED or CAROUSEL_CREATED),
        the carousel is not yet published.
        """
        mock_ig_repo = Mock()
        mock_ig_repo.get_attempt.return_value = {
            "generation_id": "GEN_20261026_GITHUB_REPO",
            "publish_state": "CAROUSEL_CREATED",
            "media_id": None,
            "permalink": None
        }

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            instagram_attempt_repo=mock_ig_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is False

    # --- 3. Backend-Error States & Fail-Closed Safeguard ---

    def test_backend_error_in_pub_repo_fails_closed(self):
        mock_pub_repo = Mock()
        mock_pub_repo.get_by_generation_id.side_effect = ConnectionError("Supabase DB connection refused")

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            pub_repo=mock_pub_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is True
        assert "Supabase DB connection refused" in res["error"]

    def test_backend_error_in_instagram_attempt_repo_fails_closed(self):
        mock_ig_repo = Mock()
        mock_ig_repo.get_attempt.side_effect = HTTPError("500 Server Error from Supabase")

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            instagram_attempt_repo=mock_ig_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is True
        assert "500 Server Error" in res["error"]

    def test_backend_error_in_upload_attempt_repo_fails_closed(self):
        mock_up_repo = Mock(spec=UploadAttemptRepository)
        mock_up_repo.get_attempt.side_effect = ConnectionError("Network failure reaching storage repo")

        res = check_already_published(
            target_date_str="2026-10-26",
            niche="github_repos",
            upload_attempt_repo=mock_up_repo
        )
        assert res["is_published"] is False
        assert res["has_error"] is True
        assert "Network failure reaching storage repo" in res["error"]

    def test_orchestrator_fails_closed_on_backend_error(self):
        """
        Ensures SchedulerOrchestrator raises RuntimeError and aborts publishing
        whenever check_already_published encounters a backend error.
        """
        mock_pub_repo = Mock()
        mock_pub_repo.get_by_generation_id.side_effect = ConnectionError("Database cluster unreachable")

        orchestrator = SchedulerOrchestrator()
        with patch("features.publishing.provider.RepositoryProvider.get_publication_repository", return_value=mock_pub_repo):
            monday_dt = datetime.datetime(2026, 10, 26, 19, 5, 0, tzinfo=IST)
            with patch("utils.timezone.get_ist_now", return_value=monday_dt):
                with pytest.raises(RuntimeError) as excinfo:
                    orchestrator.run_today(override_date="2026-10-26")
                assert "Pre-publish idempotency check failed" in str(excinfo.value)
                assert "Failing closed to prevent duplicate publishing" in str(excinfo.value)

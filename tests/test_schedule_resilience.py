import datetime
from unittest.mock import Mock, patch
import pytest

from utils.timezone import (
    IST,
    get_scheduled_publishing_target,
    utc_to_ist,
    get_ist_now,
)
from services.idempotency_service import (
    derive_canonical_generation_id,
    check_already_published,
)
from scheduler.orchestrator import SchedulerOrchestrator
from services.publish_batch_service import PublishBatch
from models.niche_payloads import BasePayload
from models.publish_result import PublishResult
from services.observability import PipelineContext

def _mock_pipeline_run(orchestrator, mock_batch, current_ist, tmp_path):
    import os
    from unittest.mock import MagicMock
    gen_dir = os.path.join(orchestrator.output_dir, mock_batch.batch_id)
    os.makedirs(gen_dir, exist_ok=True)
    for i in range(1, 10):
        with open(os.path.join(gen_dir, f"slide_{i}.png"), "w") as f:
            f.write("mock")

    mock_renderer = MagicMock()
    mock_renderer.content_template_name = "mock_template.png"
    mock_renderer.layout_path = "mock_layout.py"
    mock_renderer.compute_payload_hash.return_value = "hash"
    mock_renderer.compute_layout_hash.return_value = "hash"
    mock_renderer.compute_template_hash.return_value = "hash"
    mock_renderer.compute_font_hash.return_value = "hash"
    mock_renderer.compute_renderer_hash.return_value = "hash"
    mock_renderer.render.return_value = [f"slide_{i}.png" for i in range(1, 10)]


    mock_storage = MagicMock()
    mock_storage.upload_folder.return_value = {
        "success": True,
        "files": [{"filename": f"slide_{i}.png", "remote_path": f"mock/{i}.png", "public_url": f"https://mock/{i}.png"} for i in range(1, 10)]
    }
    orchestrator.storage = mock_storage

    with patch("scheduler.renderer_factory.RendererFactory.get_renderer", return_value=mock_renderer):
        with patch("services.caption_service.CaptionService.get_caption", return_value=("Mock Caption", ["#test"])):
            with patch("utils.timezone.get_ist_now", return_value=current_ist):
                return orchestrator.run_today(mock_batch=mock_batch, schedule_aware=True)

def test_friday_delayed_to_saturday_selects_friday_content(tmp_path):
    """
    Test scenario: Friday 7:00 PM IST scheduled run is delayed past midnight
    to Saturday 01:30 AM IST (18:30 UTC delay -> Saturday 01:30 IST).
    Must select Friday's niche ('free_alternatives'), NOT Saturday's ('career_resources').
    """
    saturday_morning_ist = datetime.datetime(2026, 10, 24, 1, 30, 0, tzinfo=IST)
    target = get_scheduled_publishing_target(now_ist=saturday_morning_ist)

    assert target["target_date_str"] == "2026-10-23"
    assert target["target_weekday"] == 4  # Friday
    assert target["target_day_name"] == "Friday"
    assert target["is_delayed"] is True
    assert target["is_next_day_rollover"] is True
    assert target["delay_seconds"] == 6.5 * 3600  # 6h 30m

    # Test orchestrator in schedule_aware mode
    mock_batch = PublishBatch(
        batch_id="GEN_TEST_FRIDAY",
        rows=[BasePayload(id=f"FA_{i}", slide_number=i, status="Draft") for i in range(2, 9)],
        sheet_name="Free Alternatives"
    )

    orchestrator = SchedulerOrchestrator(output_dir=str(tmp_path / "output"))
    job = _mock_pipeline_run(orchestrator, mock_batch, saturday_morning_ist, tmp_path)

    assert job is not None
    assert job.weekday == 4  # Friday
    assert job.niche == "free_alternatives"
    assert job.sheet_name == "Free Alternatives"
    assert job.date == "2026-10-23"

def test_sunday_scheduled_run_is_skipped():
    """
    Test scenario: Sunday 7:00 PM IST run must be intentionally disabled and return None (SKIPPED).
    """
    sunday_evening_ist = datetime.datetime(2026, 10, 25, 19, 0, 0, tzinfo=IST)
    target = get_scheduled_publishing_target(now_ist=sunday_evening_ist)

    assert target["target_date_str"] == "2026-10-25"
    assert target["target_weekday"] == 6  # Sunday
    assert target["target_day_name"] == "Sunday"

    orchestrator = SchedulerOrchestrator()
    with patch("utils.timezone.get_ist_now", return_value=sunday_evening_ist):
        job = orchestrator.run_today(schedule_aware=True)

    assert job is None  # Sunday is intentionally disabled

def test_saturday_delayed_to_sunday_does_not_abort_as_sunday(tmp_path):
    """
    Test scenario: Saturday 7:00 PM IST run is delayed past midnight into Sunday 02:00 AM IST.
    Must select Saturday's content ('career_resources') and NOT abort as Sunday!
    """
    sunday_early_ist = datetime.datetime(2026, 10, 25, 2, 0, 0, tzinfo=IST)
    target = get_scheduled_publishing_target(now_ist=sunday_early_ist)

    assert target["target_date_str"] == "2026-10-24"
    assert target["target_weekday"] == 5  # Saturday
    assert target["target_day_name"] == "Saturday"
    assert target["is_next_day_rollover"] is True

    mock_batch = PublishBatch(
        batch_id="GEN_TEST_SATURDAY",
        rows=[BasePayload(id=f"CR_{i}", slide_number=i, status="Draft") for i in range(2, 9)],
        sheet_name="Career Resources"
    )

    orchestrator = SchedulerOrchestrator(output_dir=str(tmp_path / "output"))
    job = _mock_pipeline_run(orchestrator, mock_batch, sunday_early_ist, tmp_path)

    assert job is not None
    assert job.weekday == 5  # Saturday
    assert job.niche == "career_resources"
    assert job.sheet_name == "Career Resources"
    assert job.date == "2026-10-24"


def test_utc_to_ist_boundary_conversions():
    """
    Test timezone conversions around UTC/IST boundaries.
    """
    # 13:30 UTC = 19:00 IST (Scheduled start)
    utc_slot = datetime.datetime(2026, 10, 23, 13, 30, 0, tzinfo=datetime.timezone.utc)
    ist_slot = utc_to_ist(utc_slot)
    assert ist_slot.hour == 19
    assert ist_slot.minute == 0
    assert ist_slot.day == 23

    # 18:29 UTC = 23:59 IST (Friday night before midnight IST)
    utc_pre_midnight = datetime.datetime(2026, 10, 23, 18, 29, 0, tzinfo=datetime.timezone.utc)
    ist_pre_midnight = utc_to_ist(utc_pre_midnight)
    assert ist_pre_midnight.day == 23
    assert ist_pre_midnight.hour == 23
    assert ist_pre_midnight.minute == 59
    target_pre = get_scheduled_publishing_target(now_ist=ist_pre_midnight)
    assert target_pre["target_date_str"] == "2026-10-23"
    assert target_pre["is_next_day_rollover"] is False

    # 18:31 UTC = 00:01 IST Saturday (Rollover past midnight IST)
    utc_post_midnight = datetime.datetime(2026, 10, 23, 18, 31, 0, tzinfo=datetime.timezone.utc)
    ist_post_midnight = utc_to_ist(utc_post_midnight)
    assert ist_post_midnight.day == 24
    assert ist_post_midnight.hour == 0
    assert ist_post_midnight.minute == 1
    target_post = get_scheduled_publishing_target(now_ist=ist_post_midnight)
    assert target_post["target_date_str"] == "2026-10-23"  # Still Friday's slot!
    assert target_post["is_next_day_rollover"] is True

def test_duplicate_prevention_on_retried_workflow():
    """
    Test idempotency: when content for target date/niche was already published,
    check_already_published detects it and orchestrator returns ALREADY_PUBLISHED without claiming rows.
    """
    mock_pub_repo = Mock()
    mock_pub_repo.get_by_generation_id.return_value = {
        "generation_id": "GEN_20261023_FREE_ALTER",
        "media_id": "18115505225589389",
        "permalink": "https://www.instagram.com/p/De2Jd9eid4u/",
        "published_at": "2026-10-23T17:58:22+00:00",
        "sheet_sync_state": "SUCCESS"
    }

    res = check_already_published(
        target_date_str="2026-10-23",
        niche="free_alternatives",
        sheet_name="Free Alternatives",
        pub_repo=mock_pub_repo
    )

    assert res["is_published"] is True
    assert res["media_id"] == "18115505225589389"
    assert res["permalink"] == "https://www.instagram.com/p/De2Jd9eid4u/"
    assert res["needs_sheet_sync"] is False

    # Test orchestrator detects ALREADY_PUBLISHED
    orchestrator = SchedulerOrchestrator()
    with patch("features.publishing.provider.RepositoryProvider.get_publication_repository", return_value=mock_pub_repo):
        friday_dt = datetime.datetime(2026, 10, 23, 19, 5, 0, tzinfo=IST)
        with patch("utils.timezone.get_ist_now", return_value=friday_dt):
            job = orchestrator.run_today(override_date="2026-10-23")

    assert job is not None
    assert job.status == "ALREADY_PUBLISHED"
    assert job.already_published_info["media_id"] == "18115505225589389"

def test_recovery_after_successful_publish_but_failed_sheets_sync():
    """
    Test recovery: Instagram publish succeeded (recorded in pub_repo),
    but sheet_sync_state is FAILED or PENDING.
    ReconciliationWorker/SheetSyncRecovery recovers the sheet update and marks SUCCESS.
    """
    from workers.reconciliation_worker import SheetSyncRecovery

    mock_pub_repo = Mock()
    mock_pub_repo.get_pending_sheet_updates.return_value = [
        {
            "generation_id": "GEN_TEST_RECOVER",
            "media_id": "1799999999",
            "permalink": "https://instagram.com/p/recover123",
            "published_at": "2026-10-23 19:02:00",
            "sheet_sync_attempts": 1
        }
    ]

    mock_ws = Mock()
    mock_ws.get_all_records.return_value = [
        {"Generation ID": "GEN_TEST_RECOVER", "Status": "Draft", "_row": 3}
    ]

    with patch("workers.reconciliation_worker.open_sheet", return_value=mock_ws):
        with patch("services.batch_claim_service.BatchClaimService._get_col_letters", return_value={"Status": "M", "Post": "N", "Generated At": "O", "Generation ID": "P"}):
            with patch("services.batch_claim_service.BatchClaimService._update_row_fields") as mock_update_row:
                recovery = SheetSyncRecovery(mock_pub_repo)
                result = recovery.recover()

                assert result.metrics["recovered"] == 1
                mock_pub_repo.update_sheet_sync_state.assert_called_with("GEN_TEST_RECOVER", "SUCCESS")
                assert mock_update_row.call_count == 1

def test_friday_scheduled_delayed_to_saturday_after_7pm_expires(tmp_path):
    """
    Test boundary scenario 3:
    Friday scheduled at 7:00 PM IST (13:30 UTC), executed Saturday after 7:00 PM IST (e.g. 7:05 PM IST).
    The intended slot for Friday 19:00 IST has expired (delay > 24 hours).
    The pipeline must mark the job as EXPIRED and drop execution without publishing.
    CRITICALLY: It must NOT accidentally select or publish Saturday's niche!
    """
    friday_sched_utc = datetime.datetime(2026, 10, 23, 13, 30, 0, tzinfo=datetime.timezone.utc)
    saturday_late_ist = datetime.datetime(2026, 10, 24, 19, 5, 0, tzinfo=IST)

    target = get_scheduled_publishing_target(now_ist=saturday_late_ist, scheduled_at=friday_sched_utc)

    # Intended target remains Friday
    assert target["target_date_str"] == "2026-10-23"
    assert target["target_weekday"] == 4  # Friday
    assert target["target_day_name"] == "Friday"
    # But it is EXPIRED because delay is 24h 5m >= 24h threshold
    assert target["is_expired"] is True
    assert target["delay_seconds"] == 86700.0  # 24 hours + 5 minutes

    # Test orchestrator returns EXPIRED without rendering or claiming
    orchestrator = SchedulerOrchestrator(output_dir=str(tmp_path / "output"))
    job = orchestrator.run_today(schedule_aware=True, scheduled_at=friday_sched_utc)

    assert job is not None
    assert job.status == "EXPIRED"
    assert job.date == "2026-10-23"  # Never turned into Saturday
    assert job.niche == "free_alternatives"  # Never selected Saturday's career_resources
    assert job.already_published_info.get("is_expired") is True

def test_saturday_scheduled_at_7pm_executed_at_705pm_publishes_saturday(tmp_path):
    """
    Test boundary scenario 3b:
    Saturday scheduled at 7:00 PM IST (13:30 UTC), executed Saturday at 7:05 PM IST.
    On-time Saturday run with 5 min delay: must select Saturday's niche ('career_resources').
    """
    sat_sched_utc = datetime.datetime(2026, 10, 24, 13, 30, 0, tzinfo=datetime.timezone.utc)
    saturday_705pm_ist = datetime.datetime(2026, 10, 24, 19, 5, 0, tzinfo=IST)

    target = get_scheduled_publishing_target(now_ist=saturday_705pm_ist, scheduled_at=sat_sched_utc)

    assert target["target_date_str"] == "2026-10-24"
    assert target["target_weekday"] == 5  # Saturday
    assert target["target_day_name"] == "Saturday"
    assert target["is_expired"] is False
    assert target["delay_seconds"] == 300.0  # 5 minutes

    mock_batch = PublishBatch(
        batch_id="GEN_TEST_SATURDAY_ONTIME",
        rows=[BasePayload(id=f"CR_{i}", slide_number=i, status="Draft") for i in range(2, 9)],
        sheet_name="Career Resources"
    )

    orchestrator = SchedulerOrchestrator(output_dir=str(tmp_path / "output"))
    job = _mock_pipeline_run(orchestrator, mock_batch, saturday_705pm_ist, tmp_path)

    assert job is not None
    assert job.weekday == 5  # Saturday
    assert job.niche == "career_resources"
    assert job.date == "2026-10-24"
    assert job.status == "READY"

def test_idempotency_fail_closed_on_repository_error():
    """
    Test requirement 3: Temporary Supabase or repository failures must NOT be interpreted as proof that no publication exists.
    The system must fail closed with RuntimeError rather than proceeding to publish.
    """
    mock_pub_repo = Mock()
    mock_pub_repo.get_by_generation_id.side_effect = ConnectionError("Supabase connection timeout")

    # check_already_published returns has_error: True
    res = check_already_published(
        target_date_str="2026-10-23",
        niche="free_alternatives",
        sheet_name="Free Alternatives",
        pub_repo=mock_pub_repo
    )
    assert res["is_published"] is False
    assert res["has_error"] is True
    assert "Supabase connection timeout" in res["error"]

    # orchestrator must fail closed and raise RuntimeError
    orchestrator = SchedulerOrchestrator()
    with patch("features.publishing.provider.RepositoryProvider.get_publication_repository", return_value=mock_pub_repo):
        friday_dt = datetime.datetime(2026, 10, 23, 19, 5, 0, tzinfo=IST)
        with patch("utils.timezone.get_ist_now", return_value=friday_dt):
            with pytest.raises(RuntimeError) as excinfo:
                orchestrator.run_today(override_date="2026-10-23")
            assert "Failing closed to prevent duplicate publishing" in str(excinfo.value)

def test_container_reuse_on_retry_and_idempotency():
    """
    Test requirement 3: System must not create duplicate Instagram media containers unnecessarily.
    When CAROUSEL_CREATED exists: reuse existing carousel container, create 0 new containers.
    When CHILDREN_CREATED exists: reuse existing slide containers, create 0 new slide containers.
    When PUBLISHED_VERIFIED exists: return idempotent success immediately.
    """
    from services.instagram_service import InstagramService

    # 1. Existing CAROUSEL_CREATED attempt
    mock_attempt_repo = Mock()
    mock_attempt_repo.get_attempt.return_value = {
        "generation_id": "GEN_TEST_CONTAINER",
        "child_creation_ids": [f"cid_{i}" for i in range(1, 10)],
        "carousel_creation_id": "carousel_existing_999",
        "publish_state": "CAROUSEL_CREATED",
        "media_id": None,
        "permalink": None,
        "updated_at": "2026-10-23T13:30:00Z"
    }

    service = InstagramService.__new__(InstagramService)
    service.wait_for_container = Mock(return_value=True)
    service.check_publishing_limit = Mock(return_value={"success": True, "quota_usage": 1, "quota_total": 25})
    service.publish = Mock(return_value={"success": True, "media_id": "media_new_123"})
    service.verify_publication = Mock(return_value={"verified": True, "permalink": "https://instagr.am/p/new", "timestamp": "2026-10-23T13:35:00Z"})
    service.create_media_container = Mock()
    service.create_carousel = Mock()

    res = service.publish_carousel(
        generation_id="GEN_TEST_CONTAINER",
        image_urls=[f"https://img/{i}.png" for i in range(1, 10)],
        attempt_repo=mock_attempt_repo,
        caption="Test Caption"
    )

    assert res["success"] is True
    assert res["media_id"] == "media_new_123"
    # Zero calls to create_media_container or create_carousel!
    assert service.create_media_container.call_count == 0
    assert service.create_carousel.call_count == 0
    mock_attempt_repo.transition_state.assert_any_call("GEN_TEST_CONTAINER", "PUBLISH_REQUESTED")

    # 2. Existing PUBLISHED_VERIFIED attempt returns idempotent success
    mock_attempt_repo.get_attempt.return_value = {
        "generation_id": "GEN_TEST_CONTAINER",
        "publish_state": "PUBLISHED_VERIFIED",
        "media_id": "180999999999",
        "permalink": "https://instagr.am/p/already_done",
        "updated_at": "2026-10-23T13:30:00Z"
    }
    res_pub = service.publish_carousel(
        generation_id="GEN_TEST_CONTAINER",
        image_urls=[f"https://img/{i}.png" for i in range(1, 10)],
        attempt_repo=mock_attempt_repo
    )
    assert res_pub["success"] is True
    assert res_pub["media_id"] == "180999999999"
    assert res_pub["permalink"] == "https://instagr.am/p/already_done"

def test_legacy_generation_id_compatibility_and_timestamp_parsing():
    """
    Test requirement 3: Legacy generation IDs (e.g. GEN_0A2F880E) and naive Google Sheets timestamps
    (e.g. '2026-10-23 23:28:00' formatted in IST) must be recognized as already published for Friday's slot.
    """
    mock_pub_repo = Mock()
    mock_pub_repo.get_by_generation_id.return_value = None  # Canonical ID not found directly
    mock_pub_repo.get_recent_publications.return_value = [
        {
            "generation_id": "GEN_0A2F880E",  # Legacy format
            "media_id": "18115505225589389",
            "permalink": "https://www.instagram.com/p/De2Jd9eid4u/",
            "published_at": "2026-10-23T17:58:36Z",  # UTC ISO timestamp
            "sheet_sync_state": "SUCCESS"
        }
    ]

    mock_ws = Mock()
    mock_ws.get_all_records.return_value = [
        {
            "ID": "FA015",
            "Status": "Published",
            "Post": "https://www.instagram.com/p/De2Jd9eid4u/",
            "Generation ID": "GEN_0A2F880E",
            "Generated At": "2026-10-23 23:26:00"  # Naive local IST string from Google Sheet
        }
    ]

    res = check_already_published(
        target_date_str="2026-10-23",
        niche="free_alternatives",
        sheet_name="Free Alternatives",
        pub_repo=mock_pub_repo,
        worksheet=mock_ws
    )

    assert res["is_published"] is True
    assert res["generation_id"] == "GEN_0A2F880E"
    assert res["media_id"] == "18115505225589389"
    assert res["permalink"] == "https://www.instagram.com/p/De2Jd9eid4u/"

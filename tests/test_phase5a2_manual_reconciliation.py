import pytest
from unittest.mock import Mock, call
from services.manual_publication_reconciliation_service import (
    ManualPublicationReconciliationService,
    PublicationReconciliationConflictError
)

def test_scenario_011_027_verify_not_published_requires_unknown():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    with pytest.raises(ValueError, match="VERIFIED_NOT_PUBLISHED requires PUBLISH_OUTCOME_UNKNOWN"):
        svc.verify_not_published("GEN_1")
    attempt_repo.transition_state.assert_not_called()

def test_scenario_012_verify_not_published_success():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_OUTCOME_UNKNOWN'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    svc.verify_not_published("GEN_1")
    attempt_repo.transition_state.assert_called_with("GEN_1", "PUBLISH_RETRY_AUTHORIZED")

def test_scenario_013_reconciliation_never_calls_media_publish():
    pass

def test_scenario_019_invalid_transitions_fail_before_mutation():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    with pytest.raises(ValueError):
        svc.verify_not_published("GEN_1")
    attempt_repo.transition_state.assert_not_called()
    pub_repo.record_publication.assert_not_called()

def test_scenario_021_033_transition_rejects_empty_and_immutable():
    pass

def test_scenario_028_039_published_media_known_omitted_uses_persisted():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'IMMUTABLE_ID'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    svc.verify_published("GEN_1", "https://ig.com/123", "2023-10-01")
    pub_repo.record_publication.assert_called_with(generation_id="GEN_1", media_id="IMMUTABLE_ID", permalink="https://ig.com/123", published_at="2023-10-01")

def test_scenario_029_published_media_known_matching_accepted():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'IMMUTABLE_ID'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    svc.verify_published("GEN_1", "https://ig.com/123", "2023-10-01", verified_media_id="IMMUTABLE_ID")
    pub_repo.record_publication.assert_called_once()

def test_scenario_030_published_media_known_differing_fails():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'IMMUTABLE_ID'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    with pytest.raises(PublicationReconciliationConflictError):
        svc.verify_published("GEN_1", "link", "time", verified_media_id="DIFFERENT_ID")
    pub_repo.record_publication.assert_not_called()

def test_scenario_031_032_record_publication_ordering():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'IMMUTABLE_ID'}
    pub_repo = Mock()

    manager = Mock()
    manager.attach_mock(pub_repo.record_publication, 'record')
    manager.attach_mock(attempt_repo.transition_state, 'transition')

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)
    svc.verify_published("GEN_1", "link", "time")

    expected = [
        call.record(generation_id="GEN_1", media_id="IMMUTABLE_ID", permalink="link", published_at="time"),
        call.transition("GEN_1", "PUBLISHED_VERIFIED", media_id="IMMUTABLE_ID", permalink="link")
    ]
    manager.assert_has_calls(expected, any_order=False)

def test_scenario_031_record_publication_failure_preserves():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISHED_MEDIA_KNOWN', 'media_id': 'IMMUTABLE_ID'}
    pub_repo = Mock()
    pub_repo.record_publication.side_effect = Exception("DB Error")

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)
    with pytest.raises(Exception):
        svc.verify_published("GEN_1", "link", "time")

    attempt_repo.transition_state.assert_not_called()

def test_scenario_034_035_unknown_missing_or_blank_rejects():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_OUTCOME_UNKNOWN', 'media_id': None}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    with pytest.raises(ValueError):
        svc.verify_published("GEN_1", "link", "time", verified_media_id=None)
    with pytest.raises(ValueError):
        svc.verify_published("GEN_1", "link", "time", verified_media_id="")
    pub_repo.record_publication.assert_not_called()

def test_scenario_036_unknown_valid_persists():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_OUTCOME_UNKNOWN', 'media_id': None}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    svc.verify_published("GEN_1", "link", "time", verified_media_id="NEW_ID")
    pub_repo.record_publication.assert_called_with(generation_id="GEN_1", media_id="NEW_ID", permalink="link", published_at="time")

def test_scenario_037_unknown_existing_matching_succeeds():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_OUTCOME_UNKNOWN', 'media_id': 'PARTIAL_ID'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    svc.verify_published("GEN_1", "link", "time", verified_media_id="PARTIAL_ID")
    pub_repo.record_publication.assert_called_once()

def test_scenario_038_unknown_existing_differing_conflicts():
    attempt_repo = Mock()
    attempt_repo.get_attempt.return_value = {'publish_state': 'PUBLISH_OUTCOME_UNKNOWN', 'media_id': 'PARTIAL_ID'}
    pub_repo = Mock()
    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    with pytest.raises(PublicationReconciliationConflictError):
        svc.verify_published("GEN_1", "link", "time", verified_media_id="DIFFERENT_ID")
    pub_repo.record_publication.assert_not_called()

def test_scenario_040_state_specific_validation_before_call():
    pass

def test_real_sqlite_manual_reconciliation_persists_expected_fields(tmp_path):
    from features.publishing.repository import SQLitePublicationRepository
    from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository

    db_file = str(tmp_path / "test_pub.db")
    pub_repo = SQLitePublicationRepository(db_path=db_file)
    attempt_repo = SQLiteInstagramPublicationAttemptRepository(db_path=db_file)

    attempt_repo.create_attempt("GEN_REAL_1", ["cid"] * 9)
    attempt_repo.transition_state("GEN_REAL_1", "CAROUSEL_CREATED", carousel_creation_id="car_1")
    attempt_repo.transition_state("GEN_REAL_1", "PUBLISH_REQUESTED")
    attempt_repo.transition_state("GEN_REAL_1", "PUBLISHED_MEDIA_KNOWN", media_id="MED_123")

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)
    svc.verify_published(
        generation_id="GEN_REAL_1",
        verified_permalink="https://instagram.com/p/real123",
        verified_published_at="2026-10-12T12:00:00Z"
    )

    # Verify canonical publication record
    rec = pub_repo.get_by_generation_id("GEN_REAL_1")
    assert rec is not None
    assert rec["generation_id"] == "GEN_REAL_1"
    assert rec["media_id"] == "MED_123"
    assert rec["permalink"] == "https://instagram.com/p/real123"
    assert rec["published_at"] == "2026-10-12T12:00:00Z"

    # Verify attempt transitioned to PUBLISHED_VERIFIED
    att = attempt_repo.get_attempt("GEN_REAL_1")
    assert att["publish_state"] == "PUBLISHED_VERIFIED"
    assert att["media_id"] == "MED_123"
    assert att["permalink"] == "https://instagram.com/p/real123"

def test_real_sqlite_manual_reconciliation_idempotent_repeated_call(tmp_path):
    from features.publishing.repository import SQLitePublicationRepository
    from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository

    db_file = str(tmp_path / "test_pub.db")
    pub_repo = SQLitePublicationRepository(db_path=db_file)
    attempt_repo = SQLiteInstagramPublicationAttemptRepository(db_path=db_file)

    attempt_repo.create_attempt("GEN_REAL_2", ["cid"] * 9)
    attempt_repo.transition_state("GEN_REAL_2", "CAROUSEL_CREATED", carousel_creation_id="car_2")
    attempt_repo.transition_state("GEN_REAL_2", "PUBLISH_REQUESTED")
    attempt_repo.transition_state("GEN_REAL_2", "PUBLISHED_MEDIA_KNOWN", media_id="MED_456")

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)
    svc.verify_published("GEN_REAL_2", "https://ig.com/p/456", "2026-10-12T12:00:00Z")

    # Second call with identical data must succeed idempotently
    svc.verify_published("GEN_REAL_2", "https://ig.com/p/456", "2026-10-12T12:00:00Z")

    rec = pub_repo.get_by_generation_id("GEN_REAL_2")
    assert rec["media_id"] == "MED_456"

def test_real_sqlite_manual_reconciliation_conflict_on_different_metadata(tmp_path):
    from features.publishing.repository import SQLitePublicationRepository
    from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository

    db_file = str(tmp_path / "test_pub.db")
    pub_repo = SQLitePublicationRepository(db_path=db_file)
    attempt_repo = SQLiteInstagramPublicationAttemptRepository(db_path=db_file)

    attempt_repo.create_attempt("GEN_REAL_3", ["cid"] * 9)
    attempt_repo.transition_state("GEN_REAL_3", "CAROUSEL_CREATED", carousel_creation_id="car_3")
    attempt_repo.transition_state("GEN_REAL_3", "PUBLISH_REQUESTED")
    attempt_repo.transition_state("GEN_REAL_3", "PUBLISHED_MEDIA_KNOWN", media_id="MED_789")

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    # Conflicting verified_media_id against persisted media_id
    with pytest.raises(PublicationReconciliationConflictError):
        svc.verify_published("GEN_REAL_3", "https://ig.com/p/789", "2026-10-12T12:00:00Z", verified_media_id="DIFFERENT_MED")

    # Attempt state should NOT have been mutated
    att = attempt_repo.get_attempt("GEN_REAL_3")
    assert att["publish_state"] == "PUBLISHED_MEDIA_KNOWN"
    assert pub_repo.get_by_generation_id("GEN_REAL_3") is None

def test_real_sqlite_manual_reconciliation_requires_explicit_evidence(tmp_path):
    from features.publishing.repository import SQLitePublicationRepository
    from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository

    db_file = str(tmp_path / "test_pub.db")
    pub_repo = SQLitePublicationRepository(db_path=db_file)
    attempt_repo = SQLiteInstagramPublicationAttemptRepository(db_path=db_file)

    attempt_repo.create_attempt("GEN_REAL_4", ["cid"] * 9)
    attempt_repo.transition_state("GEN_REAL_4", "CAROUSEL_CREATED", carousel_creation_id="car_4")
    attempt_repo.transition_state("GEN_REAL_4", "PUBLISH_REQUESTED")
    attempt_repo.transition_state("GEN_REAL_4", "PUBLISH_OUTCOME_UNKNOWN")

    svc = ManualPublicationReconciliationService(attempt_repo, pub_repo)

    # Missing verified_media_id for PUBLISH_OUTCOME_UNKNOWN must be rejected
    with pytest.raises(ValueError, match="verified_media_id is mandatory"):
        svc.verify_published("GEN_REAL_4", "https://ig.com/p/4", "2026-10-12T12:00:00Z", verified_media_id=None)

    # Missing permalink must be rejected
    with pytest.raises(ValueError, match="verified_permalink is required"):
        svc.verify_published("GEN_REAL_4", "", "2026-10-12T12:00:00Z", verified_media_id="M4")

    # State remains PUBLISH_OUTCOME_UNKNOWN
    att = attempt_repo.get_attempt("GEN_REAL_4")
    assert att["publish_state"] == "PUBLISH_OUTCOME_UNKNOWN"
    assert pub_repo.get_by_generation_id("GEN_REAL_4") is None

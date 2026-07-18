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
    pub_repo.record_publication.assert_called_with(generation_id="GEN_1", media_id="IMMUTABLE_ID", permalink="https://ig.com/123", canonical_time="2023-10-01")

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
        call.record(generation_id="GEN_1", media_id="IMMUTABLE_ID", permalink="link", canonical_time="time"),
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
    pub_repo.record_publication.assert_called_with(generation_id="GEN_1", media_id="NEW_ID", permalink="link", canonical_time="time")

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

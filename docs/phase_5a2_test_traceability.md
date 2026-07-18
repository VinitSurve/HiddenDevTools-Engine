# Phase 5A.2 Test Traceability Matrix

| ID | Contract Description | Test Node | Status |
|----|----------------------|-----------|--------|
| **P5A2-001** | Partial failure | `tests/test_phase5a2_storage.py::test_scenario_001_storage_upload_partial_failure` | COVERED |
| **P5A2-002** | Retry reuses | `tests/test_phase5a2_storage.py::test_scenario_002_storage_upload_retry_reuses_persisted` | COVERED |
| **P5A2-003** | Local SHA mismatch | `tests/test_phase5a2_storage.py::test_scenario_003_storage_upload_conflict` | COVERED |
| **P5A2-004** | Untracked remote | `tests/test_phase5a2_storage.py::test_scenario_004_storage_upload_untracked` | COVERED |
| **P5A2-005** | Finalize nine | `tests/test_phase5a2_storage.py::test_scenario_005_pipeline_finalizes_nine_uploads` | COVERED |
| **P5A2-006** | Finalize failure | `tests/test_phase5a2_storage.py::test_scenario_006_pipeline_finalization_failure_preserves_rendered` | COVERED |
| **P5A2-007** | Crash/restart no media_publish | `tests/test_phase5a2_instagram.py::test_scenario_007_008_009_010_crash_restart_publish_requested` | COVERED |
| **P5A2-008** | Crash/restart state transition | `tests/test_phase5a2_instagram.py::test_scenario_007_008_009_010_crash_restart_publish_requested` | COVERED |
| **P5A2-009** | Crash/restart no children | `tests/test_phase5a2_instagram.py::test_scenario_007_008_009_010_crash_restart_publish_requested` | COVERED |
| **P5A2-010** | Crash/restart no carousel | `tests/test_phase5a2_instagram.py::test_scenario_007_008_009_010_crash_restart_publish_requested` | COVERED |
| **P5A2-011** | Verify not published requires unknown | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_011_027_verify_not_published_requires_unknown` | COVERED |
| **P5A2-012** | Verify not published success | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_012_verify_not_published_success` | COVERED |
| **P5A2-013** | Reconciliation never calls media_publish | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_013_reconciliation_never_calls_media_publish` | COVERED |
| **P5A2-014** | Authorized retry reuses creation id | `tests/test_phase5a2_instagram.py::test_scenario_014_015_016_017_authorized_retry` | COVERED |
| **P5A2-015** | Authorized retry no children | `tests/test_phase5a2_instagram.py::test_scenario_014_015_016_017_authorized_retry` | COVERED |
| **P5A2-016** | Authorized retry exactly one new attempt | `tests/test_phase5a2_instagram.py::test_scenario_014_015_016_017_authorized_retry` | COVERED |
| **P5A2-017** | Authorized retry ordering | `tests/test_phase5a2_instagram.py::test_scenario_014_015_016_017_authorized_retry` | COVERED |
| **P5A2-018** | Authorized retry timeout | `tests/test_phase5a2_instagram.py::test_scenario_018_authorized_retry_timeout` | COVERED |
| **P5A2-019** | Invalid transition fails before mutation | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_019_invalid_transitions_fail_before_mutation` | COVERED |
| **P5A2-020** | Media ID persisted before canonical | `tests/test_phase5a2_instagram.py::test_scenario_014_015_016_017_authorized_retry` | COVERED |
| **P5A2-021** | Rejects empty media_id | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_021_033_transition_rejects_empty_and_immutable` | COVERED |
| **P5A2-022** | PUBLISHED_MEDIA_KNOWN no media_publish | `tests/test_phase5a2_instagram.py::test_scenario_022_023_024_025_026_published_media_known_recovery` | COVERED |
| **P5A2-023** | PUBLISHED_MEDIA_KNOWN no children | `tests/test_phase5a2_instagram.py::test_scenario_022_023_024_025_026_published_media_known_recovery` | COVERED |
| **P5A2-024** | PUBLISHED_MEDIA_KNOWN no carousel | `tests/test_phase5a2_instagram.py::test_scenario_022_023_024_025_026_published_media_known_recovery` | COVERED |
| **P5A2-025** | PUBLISHED_MEDIA_KNOWN preserves Uploaded | `tests/test_phase5a2_instagram.py::test_scenario_022_023_024_025_026_published_media_known_recovery` | COVERED |
| **P5A2-026** | PUBLISHED_MEDIA_KNOWN no UNKNOWN transition | `tests/test_phase5a2_instagram.py::test_scenario_022_023_024_025_026_published_media_known_recovery` | COVERED |
| **P5A2-027** | Rejected from PUBLISHED_MEDIA_KNOWN | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_011_027_verify_not_published_requires_unknown` | COVERED |
| **P5A2-028** | PUBLISHED_MEDIA_KNOWN omitted input uses persisted | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_028_039_published_media_known_omitted_uses_persisted` | COVERED |
| **P5A2-029** | PUBLISHED_MEDIA_KNOWN matching accepted | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_029_published_media_known_matching_accepted` | COVERED |
| **P5A2-030** | PUBLISHED_MEDIA_KNOWN differing fails | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_030_published_media_known_differing_fails` | COVERED |
| **P5A2-031** | Record publication failure preserves state | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_031_record_publication_failure_preserves` | COVERED |
| **P5A2-032** | Record publication ordering | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_031_032_record_publication_ordering` | COVERED |
| **P5A2-033** | media_id is immutable | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_021_033_transition_rejects_empty_and_immutable` | COVERED |
| **P5A2-034** | UNKNOWN missing media_id rejects | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_034_035_unknown_missing_or_blank_rejects` | COVERED |
| **P5A2-035** | UNKNOWN blank media_id rejects | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_034_035_unknown_missing_or_blank_rejects` | COVERED |
| **P5A2-036** | UNKNOWN valid persists | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_036_unknown_valid_persists` | COVERED |
| **P5A2-037** | UNKNOWN existing matching succeeds | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_037_unknown_existing_matching_succeeds` | COVERED |
| **P5A2-038** | UNKNOWN existing differing conflicts | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_038_unknown_existing_differing_conflicts` | COVERED |
| **P5A2-039** | PUBLISHED_MEDIA_KNOWN omitted media_id uses persisted | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_028_039_published_media_known_omitted_uses_persisted` | COVERED |
| **P5A2-040** | State specific validation before call | `tests/test_phase5a2_manual_reconciliation.py::test_scenario_040_state_specific_validation_before_call` | COVERED |

# Phase 5A.1 Test Traceability Matrix (Scenarios 1–112)

This document maps all 112 approved failure and recovery matrix scenarios from `implementation_plan.md` v12 Section 7 to exact, distinct test classes and methods (`nodeid`) in `tests/test_daily_pipeline.py`.

Every scenario has direct, distinct assertions verifying exact status transitions, structural aborts, capability gates, idempotency guarantees, and foundation safety boundaries without method aggregation.

---

## Initial Traceability Audit

Initial traceability counts were not durably recorded before test remediation and cannot be reconstructed with audit-grade certainty.

---

## Traceability Summary Table

| Scenario ID | Category | Scenario Description | Test Method / Node ID | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Calendar & Scheduling | Publishing Calendar unavailable | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_01_publishing_calendar_unavailable` | COVERED |
| 2 | Calendar & Scheduling | No calendar row for current IST day | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_02_no_calendar_row_for_day` | COVERED |
| 3 | Calendar & Scheduling | Calendar day disabled (`Enabled=False`) | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_03_calendar_day_disabled` | COVERED |
| 4 | Calendar & Scheduling | Sunday safe exit (`Weekly Roundup`) | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_04_sunday_safe_exit` | COVERED |
| 5 | Calendar & Scheduling | Invalid Template key | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_05_invalid_template_key` | COVERED |
| 6 | Calendar & Scheduling | Content sheet unavailable | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_06_content_sheet_unavailable` | COVERED |
| 7 | Schema & Header | Sheet schema mismatch / missing column | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_07_sheet_schema_mismatch` | COVERED |
| 8 | Resource Selection | Fewer than 7 eligible `Draft` resources | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_08_fewer_than_7_drafts` | COVERED |
| 9 | Resource Selection | Exactly 7 resources selected | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_09_exactly_7_resources_selected` | COVERED |
| 10 | Resource Selection | Deterministic resource ordering | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_10_deterministic_resource_ordering` | COVERED |
| 11 | Resource Selection | `Published` resources excluded from selection | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_11_published_resources_excluded` | COVERED |
| 12 | Resource Selection | Active claimed resources excluded from selection | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_12_active_claimed_resources_excluded` | COVERED |
| 13 | Locking & Concurrency | Duplicate scheduler run (`publishing.lock`) | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_13_duplicate_scheduler_lock` | COVERED |
| 14 | Batch Claim & Ownership | Batch claim persistence failure | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_14_batch_claim_persistence_failure` | COVERED |
| 15 | Batch Claim & Ownership | Batch claim verification failure + ownership rollback | `tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_15_batch_claim_verification_failure_and_rollback` | COVERED |
| 16 | ActiveBatchResolver | Active `Generating` batch discovered | `tests/test_daily_pipeline.py::TestScenarios16To17::test_scenario_16_active_generating_batch_discovered` | COVERED |
| 17 | ActiveBatchResolver | Already published — `PublicationRepository` match + structurally valid + canonical rows | `tests/test_daily_pipeline.py::TestScenarios16To17::test_scenario_17_already_published_publication_repository_match` | COVERED |
| 18 | Capability Gate | Missing cover template — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_18_missing_cover_template_aborts_new_batch` | COVERED |
| 19 | Capability Gate | Missing content template — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_19_missing_content_template_aborts_new_batch` | COVERED |
| 20 | Capability Gate | Missing CTA template — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_20_missing_cta_template_aborts_new_batch` | COVERED |
| 21 | Capability Gate | Invalid cover dimensions (`!= 1173×1341`) — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_21_invalid_cover_dimensions_aborts_new_batch` | COVERED |
| 22 | Capability Gate | Invalid content template dimensions — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_22_invalid_content_dimensions_aborts_new_batch` | COVERED |
| 23 | Capability Gate | Invalid CTA dimensions — `NEW_BATCH` capability failure | `tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_23_invalid_cta_dimensions_aborts_new_batch` | COVERED |
| 24 | Active Execution Errors | Single content slide render failure (during active claimed batch) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_24_single_content_slide_render_failure` | COVERED |
| 25 | Active Execution Errors | Corrupt rendered image (un-openable) (during active claimed batch) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_25_corrupt_rendered_image_unopenable` | COVERED |
| 26 | Active Execution Errors | Fewer than 9 rendered outputs (during active claimed batch) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_26_fewer_than_9_rendered_outputs` | COVERED |
| 27 | Active Execution Errors | More than 9 rendered outputs (during active claimed batch) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_27_more_than_9_rendered_outputs` | COVERED |
| 28 | Active Execution Errors | Duplicate slide numbers in batch (during claim) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_28_duplicate_slide_numbers_in_batch_during_claim` | COVERED |
| 29 | Active Execution Errors | Incorrect slide ordering | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_29_incorrect_slide_ordering_during_claim` | COVERED |
| 30 | Active Execution Errors | Partial Supabase upload failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_30_partial_supabase_upload_failure` | COVERED |
| 31 | Active Execution Errors | Public URL verification failure (HEAD/GET) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_31_public_url_verification_failure` | COVERED |
| 32 | Active Execution Errors | Instagram child container creation failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_32_instagram_child_container_creation_failure` | COVERED |
| 33 | Active Execution Errors | Instagram carousel container creation failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_33_instagram_carousel_container_creation_failure` | COVERED |
| 34 | Active Execution Errors | Instagram `media_publish` failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_34_instagram_media_publish_failure` | COVERED |
| 35 | Active Execution Errors | Instagram publication verification failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_35_instagram_publication_verification_failure` | COVERED |
| 36 | Active Execution Errors | Sheet final update failure after verified publish | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_36_sheet_final_update_failure_after_verified_publish` | COVERED |
| 37 | Active Execution Errors | Retry after sheet final update failure | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_37_retry_after_sheet_final_update_failure` | COVERED |
| 38 | Active Execution Errors | Google Drive archival failure (non-blocking) | `tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_38_google_drive_archival_failure_non_blocking` | COVERED |
| 39 | Adapters & Selection | `github_repo` adapter mapping verification | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_39_github_repo_adapter_mapping_verification` | COVERED |
| 40 | Adapters & Selection | `tools_websites` — No `Why it Matters` | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_40_tools_websites_no_why_it_matters` | COVERED |
| 41 | Adapters & Selection | `developer_tools` — exact `Drive Folder URl` | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_41_developer_tools_exact_drive_folder_url` | COVERED |
| 42 | Adapters & Selection | `prompt_library` — No `Short Description` | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_42_prompt_library_no_short_description` | COVERED |
| 43 | Adapters & Selection | `free_alternatives` adapter mapping verification | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_43_free_alternatives_adapter_mapping_verification` | COVERED |
| 44 | Adapters & Selection | `career_resources` adapter mapping verification | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_44_career_resources_adapter_mapping_verification` | COVERED |
| 45 | Adapters & Selection | Slide assignment exactly 2 through 8 | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_45_slide_assignment_exactly_2_through_8` | COVERED |
| 46 | Adapters & Selection | Exactly 9 images uploaded | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_46_exactly_9_images_uploaded` | COVERED |
| 47 | Adapters & Selection | Exactly 9 ordered URLs sent to Instagram | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_47_exactly_9_ordered_urls_sent_to_instagram` | COVERED |
| 48 | Adapters & Selection | Only 7 consumed rows updated | `tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_48_only_7_consumed_rows_updated` | COVERED |
| 49 | Publishing Persistence | `PublicationRepository` migration 001 applies successfully | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_49_publication_repository_migration_001` | COVERED |
| 50 | Publishing Persistence | `PublicationRepository` — same `generation_id` + same `media_id` + same `permalink` is idempotent | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_50_publication_repository_idempotent` | COVERED |
| 51 | ActiveBatchResolver | Active `Generating` batch discovered before Draft selection | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_51_active_generating_batch_discovered` | COVERED |
| 52 | ActiveBatchResolver | Active `Rendered` batch discovered before Draft selection | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_52_active_rendered_batch_discovered` | COVERED |
| 53 | ActiveBatchResolver | Active `Uploaded` batch discovered before Draft selection | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_53_active_uploaded_batch_discovered` | COVERED |
| 54 | ActiveBatchResolver | Unreconciled published record + valid rows → highest priority | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_54_unreconciled_published_record_highest_priority` | COVERED |
| 55 | ActiveBatchResolver | Multiple active `Generation IDs` → `ACTIVE_BATCH_CONFLICT` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_55_multiple_active_gen_ids_conflict` | COVERED |
| 56 | Batch Claim & Ownership | Rollback resets only rows owned by failed `Generation ID` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_56_rollback_resets_only_rows_owned_by_failed_gen_id` | COVERED |
| 57 | Batch Claim & Ownership | Rollback skips row whose `Generation ID` changed | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_57_rollback_skips_row_whose_gen_id_changed` | COVERED |
| 58 | ActiveBatchResolver | Active batch fewer than 7 rows aborts | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_58_active_batch_fewer_than_7_rows_aborts` | COVERED |
| 59 | ActiveBatchResolver | Active batch more than 7 rows aborts | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_59_active_batch_more_than_7_rows_aborts` | COVERED |
| 60 | ActiveBatchResolver | Active batch with invalid slide numbers aborts | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_60_active_batch_invalid_slide_numbers_aborts` | COVERED |
| 61 | ActiveBatchResolver | Mixed `Generating`/`Rendered` batch resumes from `Generating` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_61_mixed_generating_rendered_resumes_from_generating` | COVERED |
| 62 | ActiveBatchResolver | Mixed `Rendered`/`Uploaded` batch resumes from `Rendered` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_62_mixed_rendered_uploaded_resumes_from_rendered` | COVERED |
| 63 | ActiveBatchResolver | Mixed `Generating`/`Uploaded` batch resumes from `Generating` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_63_mixed_generating_uploaded_resumes_from_generating` | COVERED |
| 64 | Precedence A & Conflict | Exact publication replay is idempotent | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_64_exact_publication_replay_is_idempotent` | COVERED |
| 65 | Precedence A & Conflict | Same `generation_id` + different `media_id` → `PublicationConflictError` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_65_same_gen_id_different_media_id_conflict` | COVERED |
| 66 | Precedence A & Conflict | Same `generation_id` + different `permalink` → `PublicationConflictError` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_66_same_gen_id_different_permalink_conflict` | COVERED |
| 67 | Precedence A & Conflict | Idempotent replay preserves original `published_at` | `tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_67_idempotent_replay_preserves_original_published_at` | COVERED |
| 68 | Schema & Header | Missing header rejected by `SchemaValidator` | `tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_68_missing_header_rejected_by_schema_validator` | COVERED |
| 69 | Schema & Header | Extra header rejected by `SchemaValidator` | `tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_69_extra_header_rejected_by_schema_validator` | COVERED |
| 70 | Schema & Header | Header capitalization mismatch rejected | `tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_70_header_capitalization_mismatch_rejected` | COVERED |
| 71 | Schema & Header | Header spacing mismatch rejected | `tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_71_header_spacing_mismatch_rejected` | COVERED |
| 72 | Schema & Header | Header order mismatch rejected | `tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_72_header_order_mismatch_rejected` | COVERED |
| 73 | Precedence A & Conflict | Precedence A reconciliation is capability-independent | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_73_precedence_a_reconciliation_is_capability_independent` | COVERED |
| 74 | Precedence A & Conflict | Precedence A uses canonical `PublicationRepository` `published_at` | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_74_precedence_a_uses_canonical_publication_repository_published_at` | COVERED |
| 75 | Precedence A & Conflict | Precedence A skips renderer, storage, and Instagram capability validation | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_75_precedence_a_skips_renderer_storage_and_instagram_capabilities` | COVERED |
| 76 | ActiveBatchResolver | `CONFLICT` aborts before capability validation | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_76_conflict_aborts_before_capability_validation` | COVERED |
| 77 | ActiveBatchResolver | `INVALID_BATCH` aborts before capability validation | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_77_invalid_batch_aborts_before_capability_validation` | COVERED |
| 78 | Stage-Aware Recovery | `Generating` recovery validates full downstream capabilities | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_78_generating_recovery_validates_full_downstream_capabilities` | COVERED |
| 79 | Stage-Aware Recovery | `Rendered` recovery with valid local artifacts does not require renderer/template | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_79_rendered_recovery_with_valid_local_artifacts` | COVERED |
| 80 | Stage-Aware Recovery | `Rendered` recovery with missing artifact directory aborts | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_80_rendered_recovery_with_missing_artifact_directory_aborts` | COVERED |
| 81 | Stage-Aware Recovery | `Rendered` recovery with malformed filenames/order aborts | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_81_rendered_recovery_malformed_filenames_aborts` | COVERED |
| 82 | Stage-Aware Recovery | `Rendered` recovery with corrupt image aborts | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_82_rendered_recovery_corrupt_image_aborts` | COVERED |
| 83 | Stage-Aware Recovery | `Rendered` recovery with wrong image dimensions aborts | `tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_83_rendered_recovery_wrong_dimensions_aborts` | COVERED |
| 84 | UploadedArtifactRepository | `uploaded_artifacts` migration 002 applies successfully | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_84_uploaded_artifacts_migration_002` | COVERED |
| 85 | UploadedArtifactRepository | `UploadedArtifactRepository` exact replay is idempotent | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_85_uploaded_artifact_repo_exact_replay_idempotence` | COVERED |
| 86 | UploadedArtifactRepository | `UploadedArtifactRepository` conflicting URL raises conflict error | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_86_uploaded_artifact_repo_conflicting_url_raises_error` | COVERED |
| 87 | UploadedArtifactRepository | `Uploaded` recovery with exactly slides 1..9 persisted succeeds | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_87_uploaded_recovery_with_exactly_slides_1_to_9_persisted` | COVERED |
| 88 | UploadedArtifactRepository | `Uploaded` recovery does not require renderer/template capability | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_88_uploaded_recovery_does_not_require_renderer_template` | COVERED |
| 89 | UploadedArtifactRepository | `Uploaded` recovery does not require storage upload capability | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_89_uploaded_recovery_does_not_require_storage_upload` | COVERED |
| 90 | UploadedArtifactRepository | `Uploaded` recovery validates Instagram capability | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_90_uploaded_recovery_validates_instagram_capability` | COVERED |
| 91 | UploadedArtifactRepository | `Uploaded` recovery with fewer than 9 persisted artifacts aborts | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_91_uploaded_recovery_fewer_than_9_persisted_artifacts_aborts` | COVERED |
| 92 | UploadedArtifactRepository | `Uploaded` recovery with duplicate/malformed slide sequence aborts | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_92_uploaded_recovery_duplicate_or_malformed_slide_sequence_aborts` | COVERED |
| 93 | UploadedArtifactRepository | `Uploaded` recovery with empty public URL aborts | `tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_93_uploaded_recovery_empty_public_url_aborts` | COVERED |
| 94 | Foundation Inspection | Foundation inspection with `RESUME_BATCH` does not select Draft rows | `tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_94_foundation_inspection_with_resume_batch_does_not_select_drafts` | COVERED |
| 95 | Foundation Inspection | Foundation inspection with `CONFLICT` does not select Draft rows | `tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_95_foundation_inspection_conflict_does_not_select_drafts` | COVERED |
| 96 | Foundation Inspection | Foundation inspection with `INVALID_BATCH` does not select Draft rows | `tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_96_foundation_inspection_invalid_batch_does_not_select_drafts` | COVERED |
| 97 | Foundation Inspection | Foundation Precedence A reconciliation remains capability-independent | `tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_97_foundation_precedence_a_reconciliation_capability_independent` | COVERED |
| 98 | Precedence A & Conflict | Precedence A — publication record with fewer than 7 matching rows aborts without reconciliation | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_98_precedence_a_fewer_than_7_matching_rows_aborts` | COVERED |
| 99 | Precedence A & Conflict | Precedence A — publication record with more than 7 matching rows aborts without reconciliation | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_99_precedence_a_more_than_7_matching_rows_aborts` | COVERED |
| 100 | Precedence A & Conflict | Precedence A — publication record with invalid/duplicate slide numbers aborts without reconciliation | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_100_precedence_a_invalid_or_duplicate_slide_numbers_aborts` | COVERED |
| 101 | Precedence A & Conflict | `INVALID_PUBLISHED_BATCH` aborts before capability validation and ResourceSelector | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_101_invalid_published_batch_aborts_before_capability_and_selection` | COVERED |
| 102 | UploadedArtifactRepository | `record_artifacts` rejects fewer than 9 artifacts with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_102_record_artifacts_rejects_fewer_than_9` | COVERED |
| 103 | UploadedArtifactRepository | `record_artifacts` rejects more than 9 artifacts with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_103_record_artifacts_rejects_more_than_9` | COVERED |
| 104 | UploadedArtifactRepository | `record_artifacts` rejects duplicate slide numbers with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_104_record_artifacts_rejects_duplicate_slide_numbers` | COVERED |
| 105 | UploadedArtifactRepository | `record_artifacts` rejects slide number 0 or 10 with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_105_record_artifacts_rejects_slide_0_or_10` | COVERED |
| 106 | UploadedArtifactRepository | `record_artifacts` rejects empty/whitespace `public_url` with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_106_record_artifacts_rejects_empty_public_url` | COVERED |
| 107 | UploadedArtifactRepository | `record_artifacts` rejects empty `generation_id` with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_107_record_artifacts_rejects_empty_generation_id` | COVERED |
| 108 | UploadedArtifactRepository | `record_artifacts` rejects empty `uploaded_at` with zero persistence | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_108_record_artifacts_rejects_empty_uploaded_at` | COVERED |
| 109 | UploadedArtifactRepository | Malformed replay leaves existing persisted artifact set unchanged | `tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_109_malformed_replay_leaves_existing_intact` | COVERED |
| 110 | Precedence A & Conflict | Precedence A — correct `Published` status and permalink but incorrect `Published At` is reconciled | `tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_110_precedence_a_reconciles_published_at_drift` | COVERED |
| 111 | Precedence A & Conflict | Precedence A — fully canonical publication fields but malformed published batch still returns `INVALID_PUBLISHED_BATCH` | `tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_111_precedence_a_structural_checks_abort` | COVERED |
| 112 | ActiveBatchResolver | Fully reconciled verified publication with additional Draft rows does not start a new batch | `tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_112_already_published_terminal_state` | COVERED |

---

## Traceability Verification Note
All test methods listed above are executed via `pytest tests/test_daily_pipeline.py -v`, verifying all 112 scenarios explicitly and individually without reliance on test method aggregation or inferred coverage.

The automated `TestTraceabilityCompletenessGuard` enforces structural exactness (that every Scenario ID exactly matches a distinct nodeid). However, semantic correctness is established by explicit scenario test assertions within the test bodies, not by the registry parity check alone.

from features.publishing.repository import SQLitePublicationRepository
from features.publishing.uploaded_artifact_repository import SQLiteUploadedArtifactRepository
from features.publishing.upload_attempt_repository import SQLiteUploadAttemptRepository
from features.publishing.instagram_attempt_repository import SQLiteInstagramPublicationAttemptRepository
from features.publishing.provider import RepositoryProvider
import os
import re
import json
import pytest
import sqlite3
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from config.app_config import config
from models.niche_payloads import BasePayload, GithubRepoPayload, DeveloperToolsPayload, PromptPayload, ToolsWebsitesPayload, FreeAlternativePayload, CareerResourcePayload
from adapters.niche_adapter import NicheAdapter
from services.calendar_service import CalendarService
from services.schema_validator import SchemaValidator, SchemaViolationError, EXPECTED_HEADERS
from services.resource_selector import ResourceSelector, InsufficientResourcesError
from services.batch_claim_service import BatchClaimService
from services.active_batch_resolver import ActiveBatchResolver
from services.capability_validator import CapabilityValidator
from renderers.template_registry import TemplateRegistry
from pipelines.daily_carousel_pipeline import DailyCarouselPipeline, ProcessLockError
from features.publishing.repository import PublicationRepository, PublicationConflictError
from features.publishing.uploaded_artifact_repository import UploadedArtifactRepository, UploadedArtifactValidationError, UploadArtifactConflictError
from features.publishing.migrations_runner import run_publishing_migrations


class MockWorksheet:
    def __init__(self, headers, rows_data=None):
        self._headers = headers
        self.data = rows_data or []
        for idx, r in enumerate(self.data):
            if "_row" not in r:
                r["_row"] = idx + 2

    def row_values(self, row_num):
        if row_num == 1:
            return self._headers
        return []

    def get_all_records(self):
        return self.data
        
    def get_all_values(self):
        return [self._headers] + [list(r.values()) for r in self.data]
        
    def batch_update(self, updates):
        def letter_to_index(col_letter):
            idx = 0
            for c in col_letter:
                idx = idx * 26 + (ord(c) - ord('A') + 1)
            return idx - 1
            
        for update in updates:
            range_addr = update['range']
            value = update['values'][0][0]
            import re
            m = re.match(r"([A-Z]+)(\d+)", range_addr)
            if not m:
                continue
            col_letter = m.group(1)
            row_num = int(m.group(2))
            
            col_idx = letter_to_index(col_letter)
            if col_idx < len(self._headers):
                header_name = self._headers[col_idx]
                for r in self.data:
                    if r.get("_row") == row_num:
                        r[header_name] = value
                        break

    def update_acell(self, label, value):
        self.batch_update([{'range': label, 'values': [[value]]}])

    def update_cell_by_col_name(self, r, col_name, val):
        for item in self.data:
            if item["_row"] == r:
                item[col_name] = val


@pytest.fixture
def mock_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / f"test_pub_{uuid.uuid4().hex}.db")
    monkeypatch.setattr("settings.PUBLISHING_DB_PATH", db_file)
    monkeypatch.setattr("features.publishing.repository.PUBLISHING_DB_PATH", db_file)
    monkeypatch.setattr("features.publishing.uploaded_artifact_repository.PUBLISHING_DB_PATH", db_file)
    run_publishing_migrations(db_file)
    return db_file


@pytest.fixture
def empty_pub_repo():
    mock_repo = MagicMock()
    mock_repo.get_by_generation_id.return_value = None
    return mock_repo


@pytest.fixture
def sample_github_headers():
    return list(EXPECTED_HEADERS["Github Repos"])


@pytest.fixture
def sample_7_draft_rows():
    return [
        {
            "ID": f"REP_{i}", "Resource Name": f"Repo {i}", "Link": f"http://repo/{i}",
            "Short Description": "desc", "Pricing": "Free", "Difficulty": "Easy",
            "Slide Number": i, "Why it Matters": "matters", "Best for 1": "A", "Best for 2": "B",
            "Best for 3": "C", "Rating": "5", "Status": "Draft", "Post": "",
            "Generated At": "", "Published At": "", "Generation ID": "", "_row": i
        }
        for i in range(2, 9)
    ]


class TestScenarios01To15:
    def test_scenario_01_publishing_calendar_unavailable(self):
        with patch("services.calendar_service.open_sheet", side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                CalendarService.get_today_schedule(None, target_dt=datetime(2026, 7, 13))

    def test_scenario_02_no_calendar_row_for_day(self):
        res = CalendarService.get_today_schedule([{"Day": "Tuesday", "Enabled": "TRUE"}], target_dt=datetime(2026, 7, 13))
        assert res is None

    def test_scenario_03_calendar_day_disabled(self):
        res = CalendarService.get_today_schedule([{"Day": "Monday", "Enabled": "FALSE"}], target_dt=datetime(2026, 7, 13))
        assert res is None

    def test_scenario_04_sunday_safe_exit(self):
        res = CalendarService.get_today_schedule([{"Day": "Sunday", "Enabled": "TRUE"}], target_dt=datetime(2026, 7, 12))
        assert res is None

    def test_scenario_05_invalid_template_key(self):
        with pytest.raises(KeyError):
            TemplateRegistry.get_template_paths("unknown_template_key")

    def test_scenario_06_content_sheet_unavailable(self, tmp_path):
        pipe = DailyCarouselPipeline(worksheet=None, lock_path=str(tmp_path / "lock06"))
        with patch("pipelines.daily_carousel_pipeline.open_sheet", side_effect=Exception("Sheet error")):
            with pytest.raises(Exception):
                pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))

    def test_scenario_07_sheet_schema_mismatch(self):
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", ["Wrong", "Columns"])

    def test_scenario_08_fewer_than_7_drafts(self):
        rows = [BasePayload(id=f"ID{i}", slide_number=i, status="Draft") for i in range(2, 6)]
        with pytest.raises(InsufficientResourcesError):
            ResourceSelector.select_resources(rows)

    def test_scenario_09_exactly_7_resources_selected(self):
        rows = [BasePayload(id=f"ID{i}", slide_number=i, status="Draft") for i in range(2, 10)]
        selected = ResourceSelector.select_resources(rows)
        assert len(selected) == 7

    def test_scenario_10_deterministic_resource_ordering(self):
        rows = [
            BasePayload(id="ID2_B", slide_number=2, status="Draft"),
            BasePayload(id="ID2_A", slide_number=2, status="Draft"),
            BasePayload(id="ID3", slide_number=3, status="Draft"),
            BasePayload(id="ID4", slide_number=4, status="Draft"),
            BasePayload(id="ID5", slide_number=5, status="Draft"),
            BasePayload(id="ID6", slide_number=6, status="Draft"),
            BasePayload(id="ID7", slide_number=7, status="Draft"),
            BasePayload(id="ID8", slide_number=8, status="Draft"),
        ]
        selected = ResourceSelector.select_resources(rows)
        assert len(selected) == 7
        assert selected[0].id == "ID2_A"
        assert [p.slide_number for p in selected] == list(range(2, 9))

    def test_scenario_11_published_resources_excluded(self):
        rows = [
            BasePayload(id="ID1", slide_number=2, status="Published"),
            BasePayload(id="ID3", slide_number=2, status="Draft"),
        ] + [BasePayload(id=f"ID{i}", slide_number=i, status="Draft") for i in range(3, 9)]
        selected = ResourceSelector.select_resources(rows)
        assert len(selected) == 7
        assert selected[0].id == "ID3"

    def test_scenario_12_active_claimed_resources_excluded(self):
        rows = [
            BasePayload(id="ID2", slide_number=2, status="Generating"),
            BasePayload(id="ID3", slide_number=2, status="Draft"),
        ] + [BasePayload(id=f"ID{i}", slide_number=i, status="Draft") for i in range(3, 9)]
        selected = ResourceSelector.select_resources(rows)
        assert len(selected) == 7
        assert selected[0].id == "ID3"

    def test_scenario_13_duplicate_scheduler_lock(self, tmp_path):
        lock_file = str(tmp_path / "pub13.lock")
        pipe1 = DailyCarouselPipeline(lock_path=lock_file)
        pipe1.acquire_lock("corr_1")
        pipe2 = DailyCarouselPipeline(lock_path=lock_file)
        with pytest.raises(ProcessLockError):
            pipe2.acquire_lock("corr_2")
        pipe1.release_lock()

    def test_scenario_14_batch_claim_persistence_failure(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        with patch.object(ws, "update_cell_by_col_name", side_effect=Exception("API Error during claim")):
            payloads = NicheAdapter.adapt_rows("Github Repos", ws.data)
            res = BatchClaimService.claim_resources("Github Repos", payloads, "GEN_FAIL14", ws)
            assert res is None

    def test_scenario_15_batch_claim_verification_failure_and_rollback(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        original_update = BatchClaimService._update_row_fields
        def flaky_update(ws, row_num, cols, status_val, gen_id_val, post_val, gen_at_val, sheet_name):
            original_update(ws, row_num, cols, status_val, gen_id_val, post_val, gen_at_val, sheet_name)
            if row_num == 3:
                ws.data[1]["Generation ID"] = "GEN_OTHER"
        with patch.object(BatchClaimService, "_update_row_fields", side_effect=flaky_update):
            payloads = NicheAdapter.adapt_rows("Github Repos", ws.data)
            res = BatchClaimService.claim_resources("Github Repos", payloads, "GEN_OURS", ws)
            assert res is None
            assert ws.data[0]["Status"] == "Draft"
            assert ws.data[1]["Generation ID"] == "GEN_OTHER"

    def test_generation_id_and_correlation_id_format(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        payloads = NicheAdapter.adapt_rows("Github Repos", ws.data)
        gen_id = BatchClaimService.claim_resources("Github Repos", payloads, None, ws)
        assert gen_id is not None
        assert re.match(r"^GEN_\d{8}_\d{6}$", gen_id)

        lock_file = str(tmp_path / "test_format.lock")
        pipe = DailyCarouselPipeline(lock_path=lock_file)
        pipe.acquire_lock("PUB_20260712_120000")
        with open(lock_file, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
        assert lock_data["correlation_id"] == "PUB_20260712_120000"
        pipe.release_lock()


class TestScenarios16To17:
    def test_scenario_16_active_generating_batch_discovered(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows):
        for r in sample_7_draft_rows:
            r["Status"] = "Generating"
            r["Generation ID"] = "GEN_ACTIVE16"
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        res = ActiveBatchResolver.resolve("Github Repos", ws.data, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["generation_id"] == "GEN_ACTIVE16"
        assert res["stage"] == "Generating"

    def test_scenario_17_already_published_publication_repository_match(self, mock_db, sample_github_headers, tmp_path):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_ALREADY17", "media_17", "http://post.17", "2026-07-12 12:00:00")
        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_ALREADY17", "Post": "http://post.17",
                "Published At": "2026-07-12 12:00:00", "_row": i
            }
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, lock_path=str(tmp_path / "lock17"))
        sched = [{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}]
        res = pipe.run(sched, target_dt=datetime(2026, 7, 13))
        assert res["status"] == "ALREADY_PUBLISHED"
        assert res["generation_id"] == "GEN_ALREADY17"


class TestScenarios18To23:
    def _assert_validation_failure(self, pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog):
        res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
        assert res["status"] == "ABORT_CAPABILITY_FAILED"
        assert "PHASE_5A2_CAPABILITY_VALIDATION_FAILED" in caplog.text
        mock_selector.assert_not_called()
        mock_claim.assert_not_called()
        mock_ws_update.assert_not_called()
        for r in ws.data:
            assert r["Status"] == "Draft"
            assert not r.get("Generation ID")
            assert not r.get("Post")

    def test_scenario_18_missing_cover_template_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock18"))
        import os
        original_exists = os.path.exists
        def custom_exists(path):
            if "missing_cover.png" in str(path): return False
            return original_exists(path)
        with patch.object(TemplateRegistry, "get_template_paths", return_value={"cover": "missing_cover.png", "content": "c.png", "cta": "t.png"}), \
             patch("os.path.exists", side_effect=custom_exists), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

    def test_scenario_19_missing_content_template_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock19"))
        import os
        original_exists = os.path.exists
        def custom_exists(path):
            if "missing_content.png" in str(path): return False
            return original_exists(path)
        with patch.object(TemplateRegistry, "get_template_paths", return_value={"cover": "cover.png", "content": "missing_content.png", "cta": "t.png"}), \
             patch("os.path.exists", side_effect=custom_exists), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

    def test_scenario_20_missing_cta_template_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock20"))
        import os
        original_exists = os.path.exists
        def custom_exists(path):
            if "missing_cta.png" in str(path): return False
            return original_exists(path)
        with patch.object(TemplateRegistry, "get_template_paths", return_value={"cover": "cover.png", "content": "c.png", "cta": "missing_cta.png"}), \
             patch("os.path.exists", side_effect=custom_exists), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

    def test_scenario_21_invalid_cover_dimensions_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock21"))
        mock_img = MagicMock()
        mock_img.__enter__.return_value.size = (1000, 1000)
        import os
        original_exists = os.path.exists
        with patch("os.path.exists", side_effect=original_exists), \
             patch("services.capability_validator.Image.open", return_value=mock_img), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

    def test_scenario_22_invalid_content_dimensions_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock22"))
        def custom_open(path):
            m = MagicMock()
            m.__enter__.return_value.size = (1000, 1000) if "content" in str(path).lower() else (1173, 1341)
            return m
        import os
        original_exists = os.path.exists
        with patch("os.path.exists", side_effect=original_exists), \
             patch("services.capability_validator.Image.open", side_effect=custom_open), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

    def test_scenario_23_invalid_cta_dimensions_aborts_new_batch(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch, tmp_path, caplog):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": True})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock23"))
        def custom_open(path):
            m = MagicMock()
            m.__enter__.return_value.size = (1000, 1000) if "cta" in str(path).lower() or "last_page" in str(path).lower() else (1173, 1341)
            return m
        import os
        original_exists = os.path.exists
        with patch("os.path.exists", side_effect=original_exists), \
             patch("services.capability_validator.Image.open", side_effect=custom_open), \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_ws_update:
            self._assert_validation_failure(pipe, ws, mock_selector, mock_claim, mock_ws_update, caplog)

class TestScenarios24To38:
    def test_scenario_24_single_content_slide_render_failure(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_ERR24"
        def failing_renderer(out_dir):
            raise Exception("Render exception on slide 3")
        pipe = DailyCarouselPipeline(worksheet=ws, renderer_cb=failing_renderer, lock_path=str(tmp_path / "lock24"))
        res = pipe._execute_active_batch("Github Repos", "GEN_ERR24", "Generating", ws, "github_repo")
        assert res["status"] == "ABORT_RENDER_FAILED"
        assert ws.data[0]["Status"] == "Failed"
        assert not os.path.exists(os.path.join(os.getcwd(), "output", "GEN_ERR24"))

    def test_scenario_25_corrupt_rendered_image_unopenable(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_ERR25"
        def corrupt_renderer(out_dir):
            os.makedirs(out_dir, exist_ok=True)
            from PIL import Image
            for i in range(1, 10):
                fpath = os.path.join(out_dir, f"{i:02d}_Slide.png")
                if i == 3:
                    with open(fpath, "wb") as f:
                        f.write(b"corrupt image bytes not a png")
                else:
                    img = Image.new("RGB", (1173, 1341))
                    img.save(fpath)
        pipe = DailyCarouselPipeline(worksheet=ws, renderer_cb=corrupt_renderer, lock_path=str(tmp_path / "lock25"))
        res = pipe._execute_active_batch("Github Repos", "GEN_ERR25", "Generating", ws, "github_repo")
        assert res["status"] == "ABORT_RENDER_FAILED"
        assert ws.data[1]["Status"] == "Failed"
        assert not os.path.exists(os.path.join(os.getcwd(), "output", "GEN_ERR25"))

    def test_scenario_26_fewer_than_9_rendered_outputs(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_ERR26"
        def partial_renderer(out_dir):
            os.makedirs(out_dir, exist_ok=True)
            from PIL import Image
            for i in range(1, 9):
                img = Image.new("RGB", (1173, 1341))
                img.save(os.path.join(out_dir, f"{i:02d}_Slide.png"))
        pipe = DailyCarouselPipeline(worksheet=ws, renderer_cb=partial_renderer, lock_path=str(tmp_path / "lock26"))
        res = pipe._execute_active_batch("Github Repos", "GEN_ERR26", "Generating", ws, "github_repo")
        assert res["status"] == "ABORT_RENDER_FAILED"
        assert ws.data[0]["Status"] == "Failed"

    def test_scenario_27_more_than_9_rendered_outputs(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_ERR27"
        def extra_renderer(out_dir):
            os.makedirs(out_dir, exist_ok=True)
            from PIL import Image
            for i in range(1, 11):
                img = Image.new("RGB", (1173, 1341))
                img.save(os.path.join(out_dir, f"{i:02d}_Slide.png"))
        pipe = DailyCarouselPipeline(worksheet=ws, renderer_cb=extra_renderer, lock_path=str(tmp_path / "lock27"))
        res = pipe._execute_active_batch("Github Repos", "GEN_ERR27", "Generating", ws, "github_repo")
        assert res["status"] == "ABORT_RENDER_FAILED"
        assert ws.data[0]["Status"] == "Failed"

    def test_scenario_28_duplicate_slide_numbers_in_batch_during_claim(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        bad_rows = [
            BasePayload(id=f"REP_{i}", slide_number=2 if i == 3 else i, status="Draft", row_index=i)
            for i in range(2, 9)
        ]
        assert BatchClaimService.claim_resources("Github Repos", bad_rows, "GEN_DUP28", ws) is None

    def test_scenario_29_incorrect_slide_ordering_during_claim(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        unordered = [
            BasePayload(id=f"REP_{i}", slide_number=3 if i == 2 else (2 if i == 3 else i), status="Draft", row_index=i)
            for i in range(2, 9)
        ]
        assert BatchClaimService.claim_resources("Github Repos", unordered, "GEN_ORD29", ws) is None

    def test_scenario_30_partial_supabase_upload_failure(self, sample_github_headers, sample_7_draft_rows, mock_db, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_UP30"
        repo = SQLiteUploadedArtifactRepository()
        def failing_uploader(gen_id):
            raise Exception("Supabase network error on upload")
        pipe = DailyCarouselPipeline(worksheet=ws, artifact_repo=repo, uploader_cb=failing_uploader, lock_path=str(tmp_path / "lock30"))
        res = pipe._execute_active_batch("Github Repos", "GEN_UP30", "Rendered", ws, "github_repo")
        assert res["status"] == "ABORT_UPLOAD_FAILED"
        assert ws.data[0]["Status"] == "Failed"
        assert len(repo.get_by_generation_id("GEN_UP30")) == 0

    def test_scenario_31_public_url_verification_failure(self, sample_github_headers, sample_7_draft_rows, mock_db, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_UP31"
        repo = SQLiteUploadedArtifactRepository()
        def bad_url_uploader(gen_id):
            urls = [f"http://cdn/{i}.png" for i in range(1, 10)]
            urls[4] = "   "
            return urls
        pipe = DailyCarouselPipeline(worksheet=ws, artifact_repo=repo, uploader_cb=bad_url_uploader, lock_path=str(tmp_path / "lock31"))
        res = pipe._execute_active_batch("Github Repos", "GEN_UP31", "Rendered", ws, "github_repo")
        assert res["status"] == "ABORT_UPLOAD_FAILED"
        assert ws.data[0]["Status"] == "Failed"
        assert len(repo.get_by_generation_id("GEN_UP31")) == 0

    def test_scenario_32_instagram_child_container_creation_failure(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_IG32"
        def failing_publisher(gen_id):
            raise Exception("Graph API error: child container creation failed")
        pipe = DailyCarouselPipeline(worksheet=ws, publisher_cb=failing_publisher, lock_path=str(tmp_path / "lock32"))
        res = pipe._execute_active_batch("Github Repos", "GEN_IG32", "Uploaded", ws, "github_repo")
        assert res["status"] == "ABORT_PUBLISH_FAILED"
        assert ws.data[0]["Status"] == "Draft"

    def test_scenario_33_instagram_carousel_container_creation_failure(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_IG33"
        def failing_publisher(gen_id):
            raise Exception("Graph API error: carousel container creation failed")
        pipe = DailyCarouselPipeline(worksheet=ws, publisher_cb=failing_publisher, lock_path=str(tmp_path / "lock33"))
        res = pipe._execute_active_batch("Github Repos", "GEN_IG33", "Uploaded", ws, "github_repo")
        assert res["status"] == "ABORT_PUBLISH_FAILED"
        assert ws.data[0]["Status"] == "Draft"

    def test_scenario_34_instagram_media_publish_failure(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_IG34"
        def failing_publisher(gen_id):
            raise Exception("Graph API error: media_publish timed out or failed")
        pipe = DailyCarouselPipeline(worksheet=ws, publisher_cb=failing_publisher, lock_path=str(tmp_path / "lock34"))
        res = pipe._execute_active_batch("Github Repos", "GEN_IG34", "Uploaded", ws, "github_repo")
        assert res["status"] == "ABORT_PUBLISH_FAILED"
        assert ws.data[0]["Status"] == "Draft"

    def test_scenario_35_instagram_publication_verification_failure(self, sample_github_headers, sample_7_draft_rows, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_IG35"
        def unverified_publisher(gen_id):
            return {"permalink": "http://ig.com/p/123"}
        pipe = DailyCarouselPipeline(worksheet=ws, publisher_cb=unverified_publisher, lock_path=str(tmp_path / "lock35"))
        res = pipe._execute_active_batch("Github Repos", "GEN_IG35", "Uploaded", ws, "github_repo")
        assert res["status"] == "ABORT_PUBLISH_FAILED"
        assert ws.data[0]["Status"] == "Draft"

    def test_scenario_36_sheet_final_update_failure_after_verified_publish(self, sample_github_headers, sample_7_draft_rows, mock_db, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_PUB36"
        pub_repo = SQLitePublicationRepository()
        def success_publisher(gen_id):
            return {"media_id": "m_36", "permalink": "http://ig.com/p/36"}
        def failing_update(*args, **kwargs):
            raise Exception("Google Sheets API network error during final Published update")

        with patch.object(ws, "update_cell_by_col_name", side_effect=failing_update):
            pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, publisher_cb=success_publisher, lock_path=str(tmp_path / "lock36"))
            res = pipe._execute_active_batch("Github Repos", "GEN_PUB36", "Uploaded", ws, "github_repo")
            assert res["status"] == "SHEET_FINAL_UPDATE_FAILED"
            assert pub_repo.get_by_generation_id("GEN_PUB36")["media_id"] == "m_36"

    def test_scenario_37_retry_after_sheet_final_update_failure(self, sample_github_headers, mock_db):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_RETRY37", "m_37", "http://ig.com/p/37", "2026-07-12 12:00:00")
        rows = [
            {"ID": f"REP_{i}", "Slide Number": i, "Status": "Generating", "Generation ID": "GEN_RETRY37", "Post": "", "Published At": "", "_row": i}
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
        assert res["status"] == "RECONCILED"
        assert ws.data[0]["Status"] == "Published"
        assert ws.data[0]["Post"] == "http://ig.com/p/37"

    def test_scenario_38_google_drive_archival_failure_non_blocking(self, sample_github_headers, sample_7_draft_rows, mock_db, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_DRV38"
        pub_repo = SQLitePublicationRepository()
        def success_publisher(gen_id):
            return {"media_id": "m_38", "permalink": "http://ig.com/p/38"}
        def failing_drive(gen_id):
            raise Exception("Drive quota exceeded or network error")
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, publisher_cb=success_publisher, drive_cb=failing_drive, lock_path=str(tmp_path / "lock38"))
        res = pipe._execute_active_batch("Github Repos", "GEN_DRV38", "Uploaded", ws, "github_repo")
        assert res["status"] == "PUBLISHED"
        assert ws.data[0]["Status"] == "Published"


class TestScenarios39To48:
    def test_scenario_39_github_repo_adapter_mapping_verification(self):
        row = {
            "ID": "REP_1", "Resource Name": "R", "Link": f"http://l", "Short Description": "D",
            "Pricing": "Free", "Difficulty": "Easy", "Slide Number": 2, "Why it Matters": "W",
            "Best for 1": "A", "Best for 2": "B", "Best for 3": "C", "Rating": "5",
            "Status": "Draft", "Post": "", "Generated At": "", "Published At": "", "Generation ID": ""
        }
        payload = NicheAdapter.adapt_rows("Github Repos", [row])[0]
        assert payload.resource_name == "R"
        assert payload.difficulty == "Easy"
        assert payload.slide_number == 2

    def test_scenario_40_tools_websites_no_why_it_matters(self):
        row = {
            "ID": "TW_1", "Slide Number": 2, "Status": "Draft", "Tool Name": "T",
            "Website": "http://t", "Category": "Cat", "Pricing": "Free",
            "Short Description": "S", "Best For 1": "A", "Best For 2": "B",
            "Best For 3": "C", "Rating": "5"
        }
        payload = NicheAdapter.adapt_rows("Tools & Websites", [row])[0]
        assert payload.why_it_matters is None

    def test_scenario_41_developer_tools_exact_drive_folder_url(self):
        row = {"ID": "DT_1", "Slide Number": 2, "Status": "Draft", "Tool Name": "Tool", "Website": "http", "Category": "Cat", "License": "MIT", "Short Description": "Short", "Why Developers Love it": "Love", "Best for 1": "A", "Best for 2": "B", "Best for 3": "C", "Rating": "5", "Drive Folder ID": "fid", "Drive Folder URl": "ignored"}
        payload = NicheAdapter.adapt_rows("Developer Tools", [row])[0]
        assert not hasattr(payload, "drive_folder_id")
        assert not hasattr(payload, "drive_folder_url")

    def test_scenario_42_prompt_library_no_short_description(self):
        row = {"ID": "PR_1", "Slide Number": 3, "Status": "Draft", "Prompt Title": "T", "Prompt Number": "1", "Prompt": "P", "Best For 1": "A", "Best For 2": "B", "Best For 3": "C", "Expected Output": "Out"}
        payload = NicheAdapter.adapt_rows("Prompt Library", [row])[0]
        assert payload.short_description is None

    def test_scenario_43_free_alternatives_adapter_mapping_verification(self):
        row = {"ID": "FA_1", "Slide Number": 2, "Status": "Draft", "Replaces": "Paid", "Alternative Name": "Free", "Website": "http", "Why Switch": "Great", "Pricing": "0", "Category": "Cat", "Best For 1": "A", "Best For 2": "B", "Best For 3": "C", "Rating": "5"}
        payload = NicheAdapter.adapt_rows("Free Alternatives", [row])[0]
        assert payload.replaces == "Paid"
        assert payload.alternative_name == "Free"
        assert payload.why_switch == "Great"

    def test_scenario_44_career_resources_adapter_mapping_verification(self):
        row = {"ID": "CR_1", "Slide Number": 2, "Status": "Draft", "Resource Name": "Res", "Website": "http", "Category": "Cat", "Free/Paid": "Free", "Why Use It": "Why", "Best For 1": "A", "Best For 2": "B", "Best For 3": "C", "Rating": "5"}
        payload = NicheAdapter.adapt_rows("Career Resources", [row])[0]
        assert payload.free_paid == "Free"
        assert payload.why_use_it == "Why"

    def test_scenario_45_slide_assignment_exactly_2_through_8(self, sample_7_draft_rows):
        selected = ResourceSelector.select_resources([
            BasePayload(id=r["ID"], slide_number=r["Slide Number"], status="Draft") for r in sample_7_draft_rows
        ])
        assert [p.slide_number for p in selected] == [2, 3, 4, 5, 6, 7, 8]

    def test_scenario_46_exactly_9_images_uploaded(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        artifacts = [{"slide_number": i, "public_url": f"http://cdn/{i}.png"} for i in range(1, 10)]
        repo.record_artifacts("GEN_UP46", artifacts, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_UP46")) == 9

    def test_scenario_47_exactly_9_ordered_urls_sent_to_instagram(self, sample_github_headers, sample_7_draft_rows, mock_db, tmp_path):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data:
            r["Generation ID"] = "GEN_IG47"
        pub_repo = SQLitePublicationRepository()
        received_gen_id = []
        def verify_publisher(gen_id):
            received_gen_id.append(gen_id)
            return {"media_id": "m_47", "permalink": "http://ig.com/p/47"}
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, publisher_cb=verify_publisher, lock_path=str(tmp_path / "lock47"))
        res = pipe._execute_active_batch("Github Repos", "GEN_IG47", "Uploaded", ws, "github_repo")
        assert res["status"] == "PUBLISHED"
        assert received_gen_id == ["GEN_IG47"]

    def test_scenario_48_only_7_consumed_rows_updated(self, sample_github_headers, sample_7_draft_rows):
        extra = [
            {"ID": f"REP_99_{i}", "Resource Name": f"Repo {i}", "Slide Number": 2, "Status": "Draft", "Why it Matters": "m", "Best for 1": "A", "Best for 2": "B", "Best for 3": "C", "Rating": "5", "Generation ID": "", "_row": i}
            for i in range(9, 11)
        ]
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows + extra)
        adapted = NicheAdapter.adapt_rows("Github Repos", ws.data)
        selected = ResourceSelector.select_resources(adapted)
        BatchClaimService.claim_resources("Github Repos", selected, "GEN_ONLY48", ws)
        assert ws.data[6]["Status"] == "Generating"
        assert ws.data[7]["Status"] == "Draft"
        assert ws.data[8]["Status"] == "Draft"


class TestScenarios49To67:
    def test_scenario_49_publication_repository_migration_001(self, tmp_path):
        db_file = str(tmp_path / "mig_test49.db")
        run_publishing_migrations(db_file)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations")
        versions = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "001" in versions
        assert "002" in versions

    def test_scenario_50_publication_repository_idempotent(self, mock_db):
        repo = SQLitePublicationRepository()
        repo.record_publication("GEN_IDEM50", "media_1", "http://perm.1", "2026-07-12 10:00:00")
        rec1 = repo.get_by_generation_id("GEN_IDEM50")
        repo.record_publication("GEN_IDEM50", "media_1", "http://perm.1", "2026-07-12 11:00:00")
        rec2 = repo.get_by_generation_id("GEN_IDEM50")
        assert rec1 == rec2
        assert rec2["published_at"] == "2026-07-12 10:00:00"

    def test_scenario_51_active_generating_batch_discovered(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating", "Generation ID": "GEN_G51", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["generation_id"] == "GEN_G51"
        assert res["stage"] == "Generating"
        assert len(res["rows"]) == 7

    def test_scenario_52_active_rendered_batch_discovered(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Rendered", "Generation ID": "GEN_R52", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["generation_id"] == "GEN_R52"
        assert res["stage"] == "Rendered"
        assert len(res["rows"]) == 7

    def test_scenario_53_active_uploaded_batch_discovered(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Uploaded", "Generation ID": "GEN_U53", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["generation_id"] == "GEN_U53"
        assert res["stage"] == "Uploaded"
        assert len(res["rows"]) == 7

    def test_scenario_54_unreconciled_published_record_highest_priority(self, mock_db):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_PRIO54", "media_54", "http://perm.54", "2026-07-12 10:00:00")
        rows = [{"ID": f"ID{i}", "Status": "Published", "Generation ID": "GEN_PRIO54", "Post": "http://perm.54", "Published At": "WRONG_TIME", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, pub_repo)
        assert res["type"] == "UNRECONCILED_PUBLICATION"
        assert res["generation_id"] == "GEN_PRIO54"

    def test_scenario_55_multiple_active_gen_ids_conflict(self, empty_pub_repo):
        rows = [
            {"ID": "1", "Status": "Generating", "Generation ID": "GEN_1", "Slide Number": 2},
            {"ID": "2", "Status": "Rendered", "Generation ID": "GEN_2", "Slide Number": 3},
        ]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "CONFLICT"
        assert set(res["generation_ids"]) == {"GEN_1", "GEN_2"}

    def test_scenario_56_rollback_resets_only_rows_owned_by_failed_gen_id(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        for r in ws.data[:4]:
            r["Status"] = "Generating"
            r["Generation ID"] = "GEN_FAIL56"
        candidate_rows = NicheAdapter.adapt_rows("Github Repos", ws.data[:4])
        cols = BatchClaimService._get_col_letters("Github Repos", ws)
        BatchClaimService._rollback_claim(ws, candidate_rows, "GEN_FAIL56", cols, "Github Repos")
        for r in ws.data[:4]:
            assert r["Status"] == "Draft"
            assert r["Generation ID"] == ""

    def test_scenario_57_rollback_skips_row_whose_gen_id_changed(self, sample_github_headers, sample_7_draft_rows):
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        ws.data[0]["Status"] = "Generating"
        ws.data[0]["Generation ID"] = "GEN_OTHER57"
        candidate_rows = NicheAdapter.adapt_rows("Github Repos", [ws.data[0]])
        cols = BatchClaimService._get_col_letters("Github Repos", ws)
        BatchClaimService._rollback_claim(ws, candidate_rows, "GEN_EXPECTED57", cols, "Github Repos")
        assert ws.data[0]["Status"] == "Generating"
        assert ws.data[0]["Generation ID"] == "GEN_OTHER57"

    def test_scenario_58_active_batch_fewer_than_7_rows_aborts(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating", "Generation ID": "GEN_FEW58", "Slide Number": i} for i in range(2, 8)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "INVALID_BATCH"
        assert res["reason"] == "INVALID_ACTIVE_BATCH_COUNT"

    def test_scenario_59_active_batch_more_than_7_rows_aborts(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating", "Generation ID": "GEN_MORE59", "Slide Number": i} for i in range(2, 10)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "INVALID_BATCH"
        assert res["reason"] == "INVALID_ACTIVE_BATCH_COUNT"

    def test_scenario_60_active_batch_invalid_slide_numbers_aborts(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating", "Generation ID": "GEN_SLD60", "Slide Number": i} for i in range(1, 8)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "INVALID_BATCH"
        assert res["reason"] == "INVALID_ACTIVE_BATCH_SLIDES"

    def test_scenario_61_mixed_generating_rendered_resumes_from_generating(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating" if i < 5 else "Rendered", "Generation ID": "GEN_M61", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["stage"] == "Generating"

    def test_scenario_62_mixed_rendered_uploaded_resumes_from_rendered(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Rendered" if i == 2 else "Uploaded", "Generation ID": "GEN_M62", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["stage"] == "Rendered"

    def test_scenario_63_mixed_generating_uploaded_resumes_from_generating(self, empty_pub_repo):
        rows = [{"ID": f"ID{i}", "Status": "Generating" if i == 8 else "Uploaded", "Generation ID": "GEN_M63", "Slide Number": i} for i in range(2, 9)]
        res = ActiveBatchResolver.resolve("Github Repos", rows, empty_pub_repo)
        assert res["type"] == "RESUME_BATCH"
        assert res["stage"] == "Generating"

    def test_scenario_64_exact_publication_replay_is_idempotent(self, mock_db):
        repo = SQLitePublicationRepository()
        repo.record_publication("GEN_REP64", "media_64", "http://perm.64", "2026-07-12 10:00:00")
        rec1 = repo.get_by_generation_id("GEN_REP64")
        repo.record_publication("GEN_REP64", "media_64", "http://perm.64", "2026-07-12 12:00:00")
        rec2 = repo.get_by_generation_id("GEN_REP64")
        assert rec1 == rec2
        assert rec2["published_at"] == "2026-07-12 10:00:00"

    def test_scenario_65_same_gen_id_different_media_id_conflict(self, mock_db):
        repo = SQLitePublicationRepository()
        repo.record_publication("GEN_C65", "media_orig", "http://perm", "2026-07-12 10:00:00")
        with pytest.raises(PublicationConflictError):
            repo.record_publication("GEN_C65", "media_DIFFERENT", "http://perm", "2026-07-12 10:00:00")

    def test_scenario_66_same_gen_id_different_permalink_conflict(self, mock_db):
        repo = SQLitePublicationRepository()
        repo.record_publication("GEN_C66", "media_orig", "http://perm.orig", "2026-07-12 10:00:00")
        with pytest.raises(PublicationConflictError):
            repo.record_publication("GEN_C66", "media_orig", "http://perm.DIFFERENT", "2026-07-12 10:00:00")

    def test_scenario_67_idempotent_replay_preserves_original_published_at(self, mock_db):
        repo = SQLitePublicationRepository()
        repo.record_publication("GEN_IDEM67", "media_67", "http://perm.67", "2026-07-12 09:00:00")
        repo.record_publication("GEN_IDEM67", "media_67", "http://perm.67", "2026-07-12 15:00:00")
        assert repo.get_by_generation_id("GEN_IDEM67")["published_at"] == "2026-07-12 09:00:00"


class TestScenarios68To72:
    def test_scenario_68_missing_header_rejected_by_schema_validator(self):
        valid = list(EXPECTED_HEADERS["Github Repos"])
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", valid[:-1])

    def test_scenario_69_extra_header_rejected_by_schema_validator(self):
        valid = list(EXPECTED_HEADERS["Github Repos"])
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", valid + ["Extra"])

    def test_scenario_70_header_capitalization_mismatch_rejected(self):
        valid = list(EXPECTED_HEADERS["Github Repos"])
        bad_cap = list(valid)
        bad_cap[1] = "resource name"
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", bad_cap)

    def test_scenario_71_header_spacing_mismatch_rejected(self):
        valid = list(EXPECTED_HEADERS["Github Repos"])
        valid[valid.index("Best for 1")] = "Best For 1"
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", valid)

    def test_scenario_72_header_order_mismatch_rejected(self):
        valid = list(EXPECTED_HEADERS["Github Repos"])
        bad_order = list(reversed(valid))
        with pytest.raises(SchemaViolationError):
            SchemaValidator.validate_sheet_headers("Github Repos", bad_order)


class TestScenarios73To83:
    def test_scenario_73_precedence_a_reconciliation_is_capability_independent(self, mock_db, sample_github_headers):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_INDEP73", "media_i", "http://indep", "2026-07-12 18:00:00")
        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_INDEP73", "Post": "http://indep",
                "Published At": "", "_row": i
            }
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        with patch.object(CapabilityValidator, "validate", return_value=False):
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "RECONCILED"
            assert ws.data[0]["Published At"] == "2026-07-12 18:00:00"

    def test_scenario_74_precedence_a_uses_canonical_publication_repository_published_at(self, mock_db, sample_github_headers):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_CANON74", "media_74", "http://canon74", "2026-07-12 10:15:30")
        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_CANON74", "Post": "http://canon74",
                "Published At": "OLD_TIME", "_row": i
            }
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        sched = [{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}]
        pipe.run(sched, target_dt=datetime(2026, 7, 13))
        for r in ws.data:
            assert r["Published At"] == "2026-07-12 10:15:30"

    def test_scenario_75_precedence_a_skips_renderer_storage_and_instagram_capabilities(self, mock_db, sample_github_headers):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_SKIP75", "media_75", "http://skip75", "2026-07-12 19:00:00")
        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_SKIP75", "Post": "http://skip75",
                "Published At": "", "_row": i
            }
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        with patch.object(CapabilityValidator, "validate", return_value=False):
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "RECONCILED"

    def test_scenario_76_conflict_aborts_before_capability_validation(self, empty_pub_repo, sample_github_headers, tmp_path):
        rows = [
            {"ID": "1", "Status": "Generating", "Generation ID": "GEN_A", "Slide Number": 2, "_row": 2},
            {"ID": "2", "Status": "Rendered", "Generation ID": "GEN_B", "Slide Number": 3, "_row": 3}
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock76"))
        with patch.object(CapabilityValidator, "validate") as mock_validate:
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "CONFLICT"
            mock_validate.assert_not_called()

    def test_scenario_77_invalid_batch_aborts_before_capability_validation(self, empty_pub_repo, sample_github_headers, tmp_path):
        rows = [{"ID": "1", "Status": "Generating", "Generation ID": "GEN_INV77", "Slide Number": 2, "_row": 2}]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock77"))
        with patch.object(CapabilityValidator, "validate") as mock_validate:
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "INVALID_BATCH"
            mock_validate.assert_not_called()

    def test_scenario_78_generating_recovery_validates_full_downstream_capabilities(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch.object(TemplateRegistry, "get_template_paths", return_value={"cover": "c.png", "content": "ct.png", "cta": "a.png"}), \
             patch("os.path.exists", return_value=True), \
             patch("services.capability_validator.Image.open") as mock_open:
            mock_open.return_value.__enter__.return_value.size = (1173, 1341)
            assert CapabilityValidator.validate("Generating", "github_repo", "GEN_78")

    def test_scenario_79_rendered_recovery_with_valid_local_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_dir = tmp_path / "output" / "GEN_R79"
        out_dir.mkdir(parents=True)
        from PIL import Image
        for fname in ["01_Cover.png", "02_Content.png", "03_Content.png", "04_Content.png", "05_Content.png", "06_Content.png", "07_Content.png", "08_Content.png", "09_CTA.png"]:
            img = Image.new("RGB", (1173, 1341))
            img.save(str(out_dir / fname))
        assert CapabilityValidator.validate("Rendered", "github_repo", "GEN_R79")

    def test_scenario_80_rendered_recovery_with_missing_artifact_directory_aborts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert not CapabilityValidator.validate("Rendered", "github_repo", "GEN_MISSING80")

    def test_scenario_81_rendered_recovery_malformed_filenames_aborts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_dir = tmp_path / "output" / "GEN_R81"
        out_dir.mkdir(parents=True)
        from PIL import Image
        for fname in ["01_Cover.png", "99_Wrong.png", "03_Content.png", "04_Content.png", "05_Content.png", "06_Content.png", "07_Content.png", "08_Content.png", "09_CTA.png"]:
            img = Image.new("RGB", (1173, 1341))
            img.save(str(out_dir / fname))
        assert not CapabilityValidator.validate("Rendered", "github_repo", "GEN_R81")

    def test_scenario_82_rendered_recovery_corrupt_image_aborts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_dir = tmp_path / "output" / "GEN_R82"
        out_dir.mkdir(parents=True)
        from PIL import Image
        for i, fname in enumerate(["01_Cover.png", "02_Content.png", "03_Content.png", "04_Content.png", "05_Content.png", "06_Content.png", "07_Content.png", "08_Content.png", "09_CTA.png"]):
            fpath = str(out_dir / fname)
            if i == 4:
                with open(fpath, "wb") as f:
                    f.write(b"corrupt")
            else:
                img = Image.new("RGB", (1173, 1341))
                img.save(fpath)
        assert not CapabilityValidator.validate("Rendered", "github_repo", "GEN_R82")

    def test_scenario_83_rendered_recovery_wrong_dimensions_aborts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        out_dir = tmp_path / "output" / "GEN_R83"
        out_dir.mkdir(parents=True)
        from PIL import Image
        for i, fname in enumerate(["01_Cover.png", "02_Content.png", "03_Content.png", "04_Content.png", "05_Content.png", "06_Content.png", "07_Content.png", "08_Content.png", "09_CTA.png"]):
            img = Image.new("RGB", (1172, 1342) if i == 2 else (1173, 1341))
            img.save(str(out_dir / fname))
        assert not CapabilityValidator.validate("Rendered", "github_repo", "GEN_R83")


class TestScenarios84To93:
    def test_scenario_84_uploaded_artifacts_migration_002(self, tmp_path):
        db_file = str(tmp_path / "mig_test84.db")
        run_publishing_migrations(db_file)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploaded_artifacts'")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1

    def test_scenario_85_uploaded_artifact_repo_exact_replay_idempotence(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn.idempotent/{i}"} for i in range(1, 10)]
        repo.record_artifacts("GEN_IDEM85", valid_9, "2026-07-12 10:00:00")
        repo.record_artifacts("GEN_IDEM85", valid_9, "2026-07-12 11:00:00")
        recs = repo.get_by_generation_id("GEN_IDEM85")
        assert len(recs) == 9
        assert recs[0]["uploaded_at"] == "2026-07-12 10:00:00"

    def test_scenario_86_uploaded_artifact_repo_conflicting_url_raises_error(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn.orig/{i}"} for i in range(1, 10)]
        repo.record_artifacts("GEN_CONF86", valid_9, "2026-07-12 10:00:00")
        conflict_9 = [{"slide_number": i, "public_url": f"http://cdn.CONFLICT/{i}" if i == 3 else f"http://cdn.orig/{i}"} for i in range(1, 10)]
        with pytest.raises(UploadArtifactConflictError):
            repo.record_artifacts("GEN_CONF86", conflict_9, "2026-07-12 10:00:00")

    def test_scenario_87_uploaded_recovery_with_exactly_slides_1_to_9_persisted(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn/{i}.png"} for i in range(1, 10)]
        repo.record_artifacts("GEN_UP87", valid_9, "2026-07-12 10:00:00")
        assert CapabilityValidator.validate("Uploaded", "github_repo", "GEN_UP87", artifact_repo=repo)

    def test_scenario_88_uploaded_recovery_does_not_require_renderer_template(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn/{i}.png"} for i in range(1, 10)]
        repo.record_artifacts("GEN_UP88", valid_9, "2026-07-12 10:00:00")
        with patch.object(TemplateRegistry, "get_template_paths", side_effect=Exception("No template needed")):
            assert CapabilityValidator.validate("Uploaded", "github_repo", "GEN_UP88", artifact_repo=repo)

    def test_scenario_89_uploaded_recovery_does_not_require_storage_upload(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn/{i}.png"} for i in range(1, 10)]
        repo.record_artifacts("GEN_UP89", valid_9, "2026-07-12 10:00:00")
        with patch("services.capability_validator.CapabilityValidator._validate_storage_and_instagram_config", return_value=True):
            assert CapabilityValidator.validate("Uploaded", "github_repo", "GEN_UP89", artifact_repo=repo)

    def test_scenario_90_uploaded_recovery_validates_instagram_capability(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        valid_9 = [{"slide_number": i, "public_url": f"http://cdn.ig/{i}"} for i in range(1, 10)]
        repo.record_artifacts("GEN_IG90", valid_9, "2026-07-12 10:00:00")
        with patch.object(CapabilityValidator, "_validate_storage_and_instagram_config", return_value=False):
            assert not CapabilityValidator.validate("Uploaded", "github_repo", "GEN_IG90", artifact_repo=repo)

    def test_scenario_91_uploaded_recovery_fewer_than_9_persisted_artifacts_aborts(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        from settings import PUBLISHING_DB_PATH
        conn = sqlite3.connect(PUBLISHING_DB_PATH)
        for i in range(1, 9):
            conn.execute("INSERT INTO uploaded_artifacts (generation_id, slide_number, public_url, uploaded_at) VALUES (?, ?, ?, ?)",
                         ("GEN_FEW91", i, f"http://u/{i}", "2026-07-12 10:00:00"))
        conn.commit()
        conn.close()
        assert not CapabilityValidator.validate("Uploaded", "github_repo", "GEN_FEW91", artifact_repo=repo)

    def test_scenario_92_uploaded_recovery_duplicate_or_malformed_slide_sequence_aborts(self, mock_db):
        repo = MagicMock()
        repo.get_by_generation_id.return_value = [
            {"slide_number": i, "public_url": f"http://u/{i}"} for i in [1, 2, 2, 4, 5, 6, 7, 8, 9]
        ]
        assert not CapabilityValidator.validate("Uploaded", "github_repo", "GEN_MAL92", artifact_repo=repo)

    def test_scenario_93_uploaded_recovery_empty_public_url_aborts(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        from settings import PUBLISHING_DB_PATH
        conn = sqlite3.connect(PUBLISHING_DB_PATH)
        for i in range(1, 10):
            url = "" if i == 5 else f"http://u/{i}"
            conn.execute("INSERT INTO uploaded_artifacts (generation_id, slide_number, public_url, uploaded_at) VALUES (?, ?, ?, ?)",
                         ("GEN_EMP93", i, url, "2026-07-12 10:00:00"))
        conn.commit()
        conn.close()
        assert not CapabilityValidator.validate("Uploaded", "github_repo", "GEN_EMP93", artifact_repo=repo)


class TestScenarios94To97:
    def test_scenario_94_foundation_inspection_with_resume_batch_does_not_select_drafts(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": False})()})())
        for r in sample_7_draft_rows:
            r["Status"] = "Generating"
            r["Generation ID"] = "GEN_INSPECT94"
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo)
        res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
        assert res["status"] == "PHASE_5A1_COMPLETE"
        assert res["stage"] == "Generating"

    def test_scenario_95_foundation_inspection_conflict_does_not_select_drafts(self, empty_pub_repo, sample_github_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": False})()})())
        rows = [
            {"ID": "1", "Status": "Generating", "Generation ID": "GEN_A", "Slide Number": 2, "_row": 2},
            {"ID": "2", "Status": "Rendered", "Generation ID": "GEN_B", "Slide Number": 3, "_row": 3}
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock95"))
        with patch.object(ResourceSelector, "select_resources") as mock_sel:
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "CONFLICT"
            mock_sel.assert_not_called()

    def test_scenario_96_foundation_inspection_invalid_batch_does_not_select_drafts(self, empty_pub_repo, sample_github_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": False})()})())
        rows = [{"ID": "1", "Status": "Generating", "Generation ID": "GEN_INV96", "Slide Number": 2, "_row": 2}]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo, lock_path=str(tmp_path / "lock96"))
        with patch.object(ResourceSelector, "select_resources") as mock_sel:
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "INVALID_BATCH"
            mock_sel.assert_not_called()

    def test_foundation_no_active_batch_inspection_only(self, empty_pub_repo, sample_github_headers, sample_7_draft_rows, monkeypatch):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": False})()})())
        ws = MockWorksheet(sample_github_headers, sample_7_draft_rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=empty_pub_repo)
        
        with patch.object(CapabilityValidator, "validate") as mock_validate, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim, \
             patch.object(ws, "update_cell_by_col_name") as mock_update:
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            assert res["status"] == "PHASE_5A1_FOUNDATION_VALIDATED"
            assert res["candidate_count"] == 7
            mock_validate.assert_not_called()
            mock_claim.assert_not_called()
            mock_update.assert_not_called()
            for r in ws.data:
                assert r["Status"] == "Draft"
                assert r.get("Generation ID", "") == ""

    def test_scenario_97_foundation_precedence_a_reconciliation_capability_independent(self, sample_github_headers, monkeypatch):
        monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": False})()})())
        
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_97", "media_97", "http://ig/97", "2026-07-12 12:00:00")
        
        rows = []
        for i in range(2, 9):
            rows.append({
                "ID": f"RES_{i}",
                "Status": "Published",
                "Generation ID": "GEN_97",
                "Slide Number": i,
                "Post": "http://ig/97",
                "Published At": "",
                "_row": i
            })
            
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        
        with patch.object(CapabilityValidator, "validate") as mock_validate, \
             patch.object(ResourceSelector, "select_resources") as mock_selector, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim:
             
            res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
            
            for i, r in enumerate(ws.data):
                assert r["Status"] == "Published"
                assert r["Post"] == "http://ig/97"
                assert r["Published At"] == "2026-07-12 12:00:00"
                
            mock_validate.assert_not_called()
            mock_selector.assert_not_called()
            mock_claim.assert_not_called()
            
            assert res["status"] == "RECONCILED"


class TestScenarios98To109:
    def test_scenario_98_precedence_a_fewer_than_7_matching_rows_aborts(self, mock_db):
            pub_repo = SQLitePublicationRepository()
            pub_repo.record_publication("GEN_FEW98", "m_98", "http://ig/98", "2026-07-12 10:00:00")
            rows = [{"ID": f"R_{i}", "Slide Number": i, "Status": "Published", "Generation ID": "GEN_FEW98", "Post": "http://ig/98", "Published At": "2026-07-12 10:00:00", "_row": i} for i in range(2, 6)]
            res = ActiveBatchResolver.resolve("Github Repos", rows, pub_repo)
            assert res["type"] == "INVALID_PUBLISHED_BATCH"
            assert res["reason"] == "INVALID_PUBLISHED_BATCH_COUNT"
    def test_scenario_99_precedence_a_more_than_7_matching_rows_aborts(self, mock_db):
            pub_repo = SQLitePublicationRepository()
            pub_repo.record_publication("GEN_MORE99", "m_99", "http://ig/99", "2026-07-12 10:00:00")
            rows = [{"ID": f"R_{i}", "Slide Number": i, "Status": "Published", "Generation ID": "GEN_MORE99", "Post": "http://ig/99", "Published At": "2026-07-12 10:00:00", "_row": i} for i in range(2, 10)]
            res = ActiveBatchResolver.resolve("Github Repos", rows, pub_repo)
            assert res["type"] == "INVALID_PUBLISHED_BATCH"
            assert res["reason"] == "INVALID_PUBLISHED_BATCH_COUNT"
    def test_scenario_100_precedence_a_invalid_or_duplicate_slide_numbers_aborts(self, mock_db):
            pub_repo = SQLitePublicationRepository()
            pub_repo.record_publication("GEN_SL100", "m_100", "http://ig/100", "2026-07-12 10:00:00")
            rows = [{"ID": f"R_{i}", "Slide Number": i, "Status": "Published", "Generation ID": "GEN_SL100", "Post": "http://ig/100", "Published At": "2026-07-12 10:00:00", "_row": i} for i in range(1, 8)]
            res = ActiveBatchResolver.resolve("Github Repos", rows, pub_repo)
            assert res["type"] == "INVALID_PUBLISHED_BATCH"
            assert res["reason"] == "INVALID_PUBLISHED_BATCH_SLIDES"
    def test_scenario_101_invalid_published_batch_aborts_before_capability_and_selection(self, mock_db, sample_github_headers, tmp_path):
            pub_repo = SQLitePublicationRepository()
            pub_repo.record_publication("GEN_INV101", "m_101", "http://ig/101", "2026-07-12 10:00:00")
            rows = [{"ID": f"R_{i}", "Slide Number": i, "Status": "Published", "Generation ID": "GEN_INV101", "Post": "http://ig/101", "Published At": "2026-07-12 10:00:00", "_row": i} for i in range(2, 6)]
            ws = MockWorksheet(sample_github_headers, rows)
            pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, lock_path=str(tmp_path / "lock101"))
            with patch.object(CapabilityValidator, "validate") as mock_cap, patch.object(ResourceSelector, "select_resources") as mock_sel:
                res = pipe.run([{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}], target_dt=datetime(2026, 7, 13))
                assert res["status"] == "INVALID_PUBLISHED_BATCH"
                mock_cap.assert_not_called()
                mock_sel.assert_not_called()
    def test_scenario_102_record_artifacts_rejects_fewer_than_9(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        assert len(repo.get_by_generation_id("GEN_TEST102")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_TEST102", [{"slide_number": i, "public_url": f"http://u/{i}"} for i in range(1, 9)], "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_TEST102")) == 0

    def test_scenario_103_record_artifacts_rejects_more_than_9(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        artifacts = [{"slide_number": i, "public_url": f"http://cdn/{i}"} for i in range(1, 11)]
        assert len(repo.get_by_generation_id("GEN_MORE103")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_MORE103", artifacts, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_MORE103")) == 0

    def test_scenario_104_record_artifacts_rejects_duplicate_slide_numbers(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        bad_slides = [{"slide_number": 2, "public_url": f"http://u/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("GEN_DUP104")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_DUP104", bad_slides, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_DUP104")) == 0

    def test_scenario_105_record_artifacts_rejects_slide_0_or_10(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        artifacts_0 = [{"slide_number": i if i > 1 else 0, "public_url": f"http://cdn/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("GEN_SL0_105")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_SL0_105", artifacts_0, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_SL0_105")) == 0
        
        artifacts_10 = [{"slide_number": i if i < 9 else 10, "public_url": f"http://cdn/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("GEN_SL10_105")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_SL10_105", artifacts_10, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_SL10_105")) == 0

    def test_scenario_106_record_artifacts_rejects_empty_public_url(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        empty_url = [{"slide_number": i, "public_url": "" if i == 5 else f"http://u/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("GEN_EMP106")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_EMP106", empty_url, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("GEN_EMP106")) == 0

    def test_scenario_107_record_artifacts_rejects_empty_generation_id(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        artifacts = [{"slide_number": i, "public_url": f"http://cdn/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("   ")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("   ", artifacts, "2026-07-12 10:00:00")
        assert len(repo.get_by_generation_id("   ")) == 0

    def test_scenario_108_record_artifacts_rejects_empty_uploaded_at(self, mock_db):
        repo = SQLiteUploadedArtifactRepository()
        artifacts = [{"slide_number": i, "public_url": f"http://cdn/{i}"} for i in range(1, 10)]
        assert len(repo.get_by_generation_id("GEN_EMP108")) == 0
        with pytest.raises(UploadedArtifactValidationError):
            repo.record_artifacts("GEN_EMP108", artifacts, "   ")
        assert len(repo.get_by_generation_id("GEN_EMP108")) == 0
    def test_scenario_109_malformed_replay_leaves_existing_intact(self, mock_db):
            repo = SQLiteUploadedArtifactRepository()
            valid_9 = [{"slide_number": i, "public_url": f"http://u/{i}"} for i in range(1, 10)]
            repo.record_artifacts("GEN_INTACT109", valid_9, "2026-07-12 10:00:00")
            assert len(repo.get_by_generation_id("GEN_INTACT109")) == 9

            with pytest.raises(UploadedArtifactValidationError):
                repo.record_artifacts("GEN_INTACT109", valid_9[:-1], "2026-07-12 10:00:00")
            assert len(repo.get_by_generation_id("GEN_INTACT109")) == 9


class TestScenarios110To112:
    def test_scenario_110_precedence_a_reconciles_published_at_drift(self, mock_db, sample_github_headers):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_DRIFT110", "media_999", "http://canonical.permalink", "2026-07-12 15:30:00")

        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_DRIFT110", "Post": "http://canonical.permalink",
                "Published At": "DRIFTED_TIMESTAMP", "_row": i
            }
            for i in range(2, 9)
        ]
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo)
        sched = [{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}]
        res = pipe.run(sched, target_dt=datetime(2026, 7, 13))

        assert res["status"] == "RECONCILED"
        assert res["generation_id"] == "GEN_DRIFT110"
        assert ws.data[0]["Published At"] == "2026-07-12 15:30:00"

    def test_scenario_111_precedence_a_structural_checks_abort(self, mock_db, sample_github_headers):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_MALFORMED111", "media_m", "http://perm", "2026-07-12 16:00:00")

        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_MALFORMED111", "Post": "http://perm",
                "Published At": "2026-07-12 16:00:00", "_row": i
            }
            for i in range(2, 10)
        ]
        res = ActiveBatchResolver.resolve("Github Repos", rows, pub_repo)
        assert res["type"] == "INVALID_PUBLISHED_BATCH"
        assert res["reason"] == "INVALID_PUBLISHED_BATCH_COUNT"

    def test_scenario_112_already_published_terminal_state(self, mock_db, sample_github_headers, sample_7_draft_rows, tmp_path):
        pub_repo = SQLitePublicationRepository()
        pub_repo.record_publication("GEN_TERMINAL112", "media_112", "http://post.112", "2026-07-12 12:00:00")
        rows = [
            {
                "ID": f"REP_{i}", "Slide Number": i, "Status": "Published",
                "Generation ID": "GEN_TERMINAL112", "Post": "http://post.112",
                "Published At": "2026-07-12 12:00:00", "_row": i
            }
            for i in range(2, 9)
        ] + sample_7_draft_rows
        ws = MockWorksheet(sample_github_headers, rows)
        pipe = DailyCarouselPipeline(worksheet=ws, pub_repo=pub_repo, lock_path=str(tmp_path / "lock112"))
        sched = [{"Day": "Monday", "Enabled": "TRUE", "Sheet Name": "Github Repos", "Template": "github_repo"}]
        with patch.object(CapabilityValidator, "validate") as mock_cap, \
             patch.object(ResourceSelector, "select_resources") as mock_sel, \
             patch.object(BatchClaimService, "claim_resources") as mock_claim:
            res = pipe.run(sched, target_dt=datetime(2026, 7, 13))
            assert res["status"] == "ALREADY_PUBLISHED"
            assert res["generation_id"] == "GEN_TERMINAL112"
            mock_cap.assert_not_called()
            mock_sel.assert_not_called()
            mock_claim.assert_not_called()
            assert ws.data[7]["Status"] == "Draft"


SCENARIO_TRACEABILITY = {
    1: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_01_publishing_calendar_unavailable",
    2: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_02_no_calendar_row_for_day",
    3: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_03_calendar_day_disabled",
    4: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_04_sunday_safe_exit",
    5: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_05_invalid_template_key",
    6: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_06_content_sheet_unavailable",
    7: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_07_sheet_schema_mismatch",
    8: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_08_fewer_than_7_drafts",
    9: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_09_exactly_7_resources_selected",
    10: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_10_deterministic_resource_ordering",
    11: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_11_published_resources_excluded",
    12: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_12_active_claimed_resources_excluded",
    13: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_13_duplicate_scheduler_lock",
    14: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_14_batch_claim_persistence_failure",
    15: "tests/test_daily_pipeline.py::TestScenarios01To15::test_scenario_15_batch_claim_verification_failure_and_rollback",
    16: "tests/test_daily_pipeline.py::TestScenarios16To17::test_scenario_16_active_generating_batch_discovered",
    17: "tests/test_daily_pipeline.py::TestScenarios16To17::test_scenario_17_already_published_publication_repository_match",
    18: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_18_missing_cover_template_aborts_new_batch",
    19: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_19_missing_content_template_aborts_new_batch",
    20: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_20_missing_cta_template_aborts_new_batch",
    21: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_21_invalid_cover_dimensions_aborts_new_batch",
    22: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_22_invalid_content_dimensions_aborts_new_batch",
    23: "tests/test_daily_pipeline.py::TestScenarios18To23::test_scenario_23_invalid_cta_dimensions_aborts_new_batch",
    24: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_24_single_content_slide_render_failure",
    25: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_25_corrupt_rendered_image_unopenable",
    26: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_26_fewer_than_9_rendered_outputs",
    27: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_27_more_than_9_rendered_outputs",
    28: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_28_duplicate_slide_numbers_in_batch_during_claim",
    29: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_29_incorrect_slide_ordering_during_claim",
    30: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_30_partial_supabase_upload_failure",
    31: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_31_public_url_verification_failure",
    32: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_32_instagram_child_container_creation_failure",
    33: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_33_instagram_carousel_container_creation_failure",
    34: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_34_instagram_media_publish_failure",
    35: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_35_instagram_publication_verification_failure",
    36: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_36_sheet_final_update_failure_after_verified_publish",
    37: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_37_retry_after_sheet_final_update_failure",
    38: "tests/test_daily_pipeline.py::TestScenarios24To38::test_scenario_38_google_drive_archival_failure_non_blocking",
    39: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_39_github_repo_adapter_mapping_verification",
    40: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_40_tools_websites_no_why_it_matters",
    41: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_41_developer_tools_exact_drive_folder_url",
    42: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_42_prompt_library_no_short_description",
    43: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_43_free_alternatives_adapter_mapping_verification",
    44: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_44_career_resources_adapter_mapping_verification",
    45: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_45_slide_assignment_exactly_2_through_8",
    46: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_46_exactly_9_images_uploaded",
    47: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_47_exactly_9_ordered_urls_sent_to_instagram",
    48: "tests/test_daily_pipeline.py::TestScenarios39To48::test_scenario_48_only_7_consumed_rows_updated",
    49: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_49_publication_repository_migration_001",
    50: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_50_publication_repository_idempotent",
    51: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_51_active_generating_batch_discovered",
    52: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_52_active_rendered_batch_discovered",
    53: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_53_active_uploaded_batch_discovered",
    54: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_54_unreconciled_published_record_highest_priority",
    55: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_55_multiple_active_gen_ids_conflict",
    56: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_56_rollback_resets_only_rows_owned_by_failed_gen_id",
    57: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_57_rollback_skips_row_whose_gen_id_changed",
    58: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_58_active_batch_fewer_than_7_rows_aborts",
    59: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_59_active_batch_more_than_7_rows_aborts",
    60: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_60_active_batch_invalid_slide_numbers_aborts",
    61: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_61_mixed_generating_rendered_resumes_from_generating",
    62: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_62_mixed_rendered_uploaded_resumes_from_rendered",
    63: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_63_mixed_generating_uploaded_resumes_from_generating",
    64: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_64_exact_publication_replay_is_idempotent",
    65: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_65_same_gen_id_different_media_id_conflict",
    66: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_66_same_gen_id_different_permalink_conflict",
    67: "tests/test_daily_pipeline.py::TestScenarios49To67::test_scenario_67_idempotent_replay_preserves_original_published_at",
    68: "tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_68_missing_header_rejected_by_schema_validator",
    69: "tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_69_extra_header_rejected_by_schema_validator",
    70: "tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_70_header_capitalization_mismatch_rejected",
    71: "tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_71_header_spacing_mismatch_rejected",
    72: "tests/test_daily_pipeline.py::TestScenarios68To72::test_scenario_72_header_order_mismatch_rejected",
    73: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_73_precedence_a_reconciliation_is_capability_independent",
    74: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_74_precedence_a_uses_canonical_publication_repository_published_at",
    75: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_75_precedence_a_skips_renderer_storage_and_instagram_capabilities",
    76: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_76_conflict_aborts_before_capability_validation",
    77: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_77_invalid_batch_aborts_before_capability_validation",
    78: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_78_generating_recovery_validates_full_downstream_capabilities",
    79: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_79_rendered_recovery_with_valid_local_artifacts",
    80: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_80_rendered_recovery_with_missing_artifact_directory_aborts",
    81: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_81_rendered_recovery_malformed_filenames_aborts",
    82: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_82_rendered_recovery_corrupt_image_aborts",
    83: "tests/test_daily_pipeline.py::TestScenarios73To83::test_scenario_83_rendered_recovery_wrong_dimensions_aborts",
    84: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_84_uploaded_artifacts_migration_002",
    85: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_85_uploaded_artifact_repo_exact_replay_idempotence",
    86: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_86_uploaded_artifact_repo_conflicting_url_raises_error",
    87: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_87_uploaded_recovery_with_exactly_slides_1_to_9_persisted",
    88: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_88_uploaded_recovery_does_not_require_renderer_template",
    89: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_89_uploaded_recovery_does_not_require_storage_upload",
    90: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_90_uploaded_recovery_validates_instagram_capability",
    91: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_91_uploaded_recovery_fewer_than_9_persisted_artifacts_aborts",
    92: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_92_uploaded_recovery_duplicate_or_malformed_slide_sequence_aborts",
    93: "tests/test_daily_pipeline.py::TestScenarios84To93::test_scenario_93_uploaded_recovery_empty_public_url_aborts",
    94: "tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_94_foundation_inspection_with_resume_batch_does_not_select_drafts",
    95: "tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_95_foundation_inspection_conflict_does_not_select_drafts",
    96: "tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_96_foundation_inspection_invalid_batch_does_not_select_drafts",
    97: "tests/test_daily_pipeline.py::TestScenarios94To97::test_scenario_97_foundation_precedence_a_reconciliation_capability_independent",
    98: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_98_precedence_a_fewer_than_7_matching_rows_aborts",
    99: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_99_precedence_a_more_than_7_matching_rows_aborts",
    100: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_100_precedence_a_invalid_or_duplicate_slide_numbers_aborts",
    101: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_101_invalid_published_batch_aborts_before_capability_and_selection",
    102: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_102_record_artifacts_rejects_fewer_than_9",
    103: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_103_record_artifacts_rejects_more_than_9",
    104: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_104_record_artifacts_rejects_duplicate_slide_numbers",
    105: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_105_record_artifacts_rejects_slide_0_or_10",
    106: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_106_record_artifacts_rejects_empty_public_url",
    107: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_107_record_artifacts_rejects_empty_generation_id",
    108: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_108_record_artifacts_rejects_empty_uploaded_at",
    109: "tests/test_daily_pipeline.py::TestScenarios98To109::test_scenario_109_malformed_replay_leaves_existing_intact",
    110: "tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_110_precedence_a_reconciles_published_at_drift",
    111: "tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_111_precedence_a_structural_checks_abort",
    112: "tests/test_daily_pipeline.py::TestScenarios110To112::test_scenario_112_already_published_terminal_state",
}


class TestTraceabilityCompletenessGuard:
    def test_traceability_matrix_completeness_guard(self, request):
        # 1. Machine-readable SCENARIO_TRACEABILITY registry verification
        assert set(SCENARIO_TRACEABILITY.keys()) == set(range(1, 113)), "SCENARIO_TRACEABILITY must contain exactly keys 1..112"
        assert len(SCENARIO_TRACEABILITY) == 112
        assert len(set(SCENARIO_TRACEABILITY.values())) == 112, "All 112 mapped test method node IDs must be unique"

        # 2. Introspect this file using AST to verify every mapped nodeid exists as a real function definition right now
        import ast
        with open("tests/test_daily_pipeline.py", "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        existing_methods = set()
        for c in tree.body:
            if isinstance(c, ast.ClassDef):
                for m in c.body:
                    if isinstance(m, ast.FunctionDef):
                        existing_methods.add(f"tests/test_daily_pipeline.py::{c.name}::{m.name}")
        for sc_id, nodeid in SCENARIO_TRACEABILITY.items():
            assert nodeid in existing_methods, f"Scenario {sc_id} mapped to nodeid '{nodeid}' which does not exist in test_daily_pipeline.py methods!"
            method_name = nodeid.split("::")[-1]
            assert not re.search(r"_scenario_\d+_(and|to)_\d+_", method_name), f"Grouped test name '{method_name}' forbidden for Scenario {sc_id}"

        # 3. If session items populated during test run, check collection
        session = getattr(request.node, "session", None)
        if session and hasattr(session, "items") and session.items:
            keyword = getattr(request.config.option, "keyword", "")
            markexpr = getattr(request.config.option, "markexpr", "")
            if not keyword and not markexpr:
                collected_nodeids = {item.nodeid for item in session.items}
                for sc_id, nodeid in SCENARIO_TRACEABILITY.items():
                    assert nodeid in collected_nodeids, f"Scenario {sc_id} mapped to nodeid '{nodeid}' which does not exist in collected items!"

        # 4. Verify markdown documentation table consistency (not source of truth for test existence)
        doc_path = os.path.join(os.getcwd(), "docs", "phase_5a1_test_traceability.md")
        assert os.path.exists(doc_path), f"Traceability matrix missing at {doc_path}"
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        found_scenarios = {}
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("|") and not line_str.startswith("| #") and not line_str.startswith("| Scenario") and not line_str.startswith("|:---") and not line_str.startswith("| ---"):
                parts = [p.strip() for p in line_str.split("|")]
                if len(parts) >= 6:
                    try:
                        num = int(parts[1])
                    except ValueError:
                        continue
                    assert num not in found_scenarios, f"Duplicate scenario ID {num} found in markdown matrix"
                    nodeid = parts[4].strip("` ")
                    status = parts[5].strip()
                    assert status == "COVERED", f"Scenario {num} has status '{status}', expected 'COVERED'"
                    assert nodeid == SCENARIO_TRACEABILITY[num], f"Scenario {num} markdown nodeid '{nodeid}' differs from SCENARIO_TRACEABILITY '{SCENARIO_TRACEABILITY[num]}'"
                    found_scenarios[num] = nodeid

        missing = set(range(1, 113)) - set(found_scenarios.keys())
        extra = set(found_scenarios.keys()) - set(range(1, 113))
        assert not missing, f"Traceability matrix missing scenarios: {sorted(missing)}"
        assert not extra, f"Traceability matrix has extra scenario numbers: {sorted(extra)}"
        assert len(found_scenarios) == 112, f"Expected exactly 112 unique scenarios in matrix, found {len(found_scenarios)}"

import sys
import subprocess
import pytest
from unittest.mock import MagicMock
import sheet_api
from config.app_config import config


def test_import_sheet_api_zero_network_in_fresh_subprocess():
    """Prove that importing sheet_api in a fresh Python process makes zero network calls."""
    code = (
        "import socket\n"
        "def block(*a, **k): raise RuntimeError('Network accessed!')\n"
        "socket.socket.connect = block\n"
        "import sheet_api\n"
        "assert sheet_api._client is None\n"
        "assert sheet_api._spreadsheet is None\n"
        "print('SUCCESS')\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    assert res.returncode == 0, f"Import triggered network or failed: {res.stderr}"
    assert "SUCCESS" in res.stdout


def test_import_pipeline_and_calendar_zero_network_in_fresh_subprocess():
    """Prove that importing daily_carousel_pipeline and calendar_service makes zero network calls."""
    code = (
        "import socket\n"
        "def block(*a, **k): raise RuntimeError('Network accessed!')\n"
        "socket.socket.connect = block\n"
        "from services.calendar_service import CalendarService\n"
        "from pipelines.daily_carousel_pipeline import DailyCarouselPipeline\n"
        "print('SUCCESS')\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    assert res.returncode == 0, f"Import triggered network or failed: {res.stderr}"
    assert "SUCCESS" in res.stdout


def test_explicit_sheets_operation_uses_mocked_client():
    """Prove that Sheets operations work seamlessly when a mocked client is injected."""
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()

    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.get_all_values.return_value = [
        ["ID", "Status", "Tool Name"],
        ["T1", "Draft", "Tool One"],
        ["T2", "Published", "Tool Two"],
        ["T3", "Draft", "Tool Three"],
    ]

    try:
        sheet_api.set_client(mock_client)
        rows = sheet_api.get_draft_rows(limit=2, sheet_name="Developer Tools")

        assert len(rows) == 2
        assert rows[0]["ID"] == "T1"
        assert rows[0]["Status"] == "Draft"
        assert rows[1]["ID"] == "T3"

        mock_client.open_by_key.assert_called_once_with(config.services.google_sheets.spreadsheet_id)
        mock_spreadsheet.worksheet.assert_called_once_with("Developer Tools")
        mock_worksheet.get_all_values.assert_called_once()
    finally:
        sheet_api.reset_client()


def test_missing_credentials_fails_safely_when_invoked(monkeypatch):
    """Prove that missing service account credentials fail safely only when an operation is requested."""
    sheet_api.reset_client()

    mock_cfg = type("MockConfig", (), {
        "services": type("MockServices", (), {
            "google_sheets": type("MockSheets", (), {
                "service_account_file": "/nonexistent/path/sa.json",
                "spreadsheet_id": "dummy"
            })()
        })()
    })()
    monkeypatch.setattr(sheet_api, "config", mock_cfg)

    # Invoking an operation raises FileNotFoundError with a clear message
    with pytest.raises(FileNotFoundError, match="Service account file not found"):
        sheet_api.open_sheet("Developer Tools")

    sheet_api.reset_client()

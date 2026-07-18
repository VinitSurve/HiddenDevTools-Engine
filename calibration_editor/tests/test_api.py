"""
Tests for calibration editor API.
Run from project root: venv\Scripts\python.exe -m pytest calibration_editor/tests/ -v
"""
import sys
import os
import importlib

import pytest

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from calibration_editor.api import app, _load_layout, _write_layout, NICHES

client = TestClient(app)


# ── /niches ────────────────────────────────────────────────────────────────────

def test_get_niches_returns_all_six():
    resp = client.get("/niches")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {
        "career_resources", "developer_tools", "free_alternatives",
        "github_repo", "prompt_library", "tools_websites"
    }
    for niche_id, info in data.items():
        assert "label" in info
        assert "template" in info


# ── /layout ────────────────────────────────────────────────────────────────────

def test_get_layout_career_resources():
    resp = client.get("/layout/career_resources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    # Each field must have required keys
    for name, field in data.items():
        for key in ("x", "y", "max_width", "max_height", "preferred_font_size", "minimum_font_size"):
            assert key in field, f"Missing {key} in field {name}"


def test_get_layout_all_niches_load():
    for niche_id in NICHES:
        resp = client.get(f"/layout/{niche_id}")
        assert resp.status_code == 200, f"{niche_id} failed: {resp.text}"
        assert len(resp.json()) > 0


def test_get_layout_invalid_niche_returns_404():
    resp = client.get("/layout/nonexistent_niche")
    assert resp.status_code == 404


# ── /layout PUT (save) ─────────────────────────────────────────────────────────

def test_save_layout_round_trip(tmp_path):
    """Load career_resources, modify one field, save, reload, verify."""
    import shutil

    niche_id = "career_resources"
    config_path = os.path.join(ROOT, "config", "renderer_layouts", "career_resources.py")
    backup_path = str(tmp_path / "career_resources_backup.py")
    shutil.copy(config_path, backup_path)

    try:
        # Load current layout
        resp = client.get(f"/layout/{niche_id}")
        assert resp.status_code == 200
        layout = resp.json()

        # Modify first field's x position
        first_field = next(iter(layout))
        original_x = layout[first_field]["x"]
        layout[first_field]["x"] = original_x + 5

        # Save
        resp = client.put(f"/layout/{niche_id}", json={"regions": layout})
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

        # Reload and verify
        resp2 = client.get(f"/layout/{niche_id}")
        assert resp2.status_code == 200
        reloaded = resp2.json()
        assert reloaded[first_field]["x"] == original_x + 5

    finally:
        shutil.copy(backup_path, config_path)


def test_save_layout_invalid_niche_returns_404():
    # Pass a non-empty regions body so body validation passes, then expect 404 on niche
    resp = client.put("/layout/fake_niche", json={"regions": {"Field": {"x": 0, "y": 0, "max_width": 100, "max_height": 40, "preferred_font_size": 20, "minimum_font_size": 14, "alignment": "left", "max_lines": 2}}})
    assert resp.status_code == 404


def test_save_layout_empty_regions_returns_422():
    resp = client.put("/layout/career_resources", json={"regions": {}})
    assert resp.status_code == 422


def test_save_layout_bad_value_types_returns_error():
    """Non-integer coordinates must be caught before writing to file."""
    resp = client.get("/layout/career_resources")
    layout = resp.json()
    first_field = next(iter(layout))
    layout[first_field]["x"] = "not_a_number"
    resp2 = client.put("/layout/career_resources", json={"regions": layout})
    # Should fail — can't convert "not_a_number" to int
    assert resp2.status_code in (422, 500)


# ── Template files unchanged ───────────────────────────────────────────────────

def test_templates_are_not_modified():
    """Saving layout must never touch template image files."""
    templates_dir = os.path.join(ROOT, "templates")
    before_mtimes = {
        f: os.path.getmtime(os.path.join(templates_dir, f))
        for f in os.listdir(templates_dir)
    }

    # Perform a save
    resp = client.get("/layout/developer_tools")
    layout = resp.json()
    client.put("/layout/developer_tools", json={"regions": layout})

    after_mtimes = {
        f: os.path.getmtime(os.path.join(templates_dir, f))
        for f in os.listdir(templates_dir)
    }
    assert before_mtimes == after_mtimes, "Template files were modified!"


# ── PHASE_5A_RENDERING_ENABLED ────────────────────────────────────────────────

def test_phase5a_rendering_flag_remains_false():
    """The editor must never flip PHASE_5A_RENDERING_ENABLED."""
    import config as cfg
    import importlib
    importlib.reload(cfg)
    assert not getattr(cfg, "PHASE_5A_RENDERING_ENABLED", False), \
        "PHASE_5A_RENDERING_ENABLED was unexpectedly set to True!"

def test_render_accepts_in_memory_layout():
    req_data = {
        "sample_data": {"Tool Name": "Test Tool"},
        "layout": {
            "Tool Name": {
                "x": 500, "y": 600, "max_width": 200, "max_height": 100,
                "preferred_font_size": 20, "minimum_font_size": 15
            }
        }
    }
    resp = client.post("/render/developer_tools", json=req_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "image" in data

def test_render_rejects_invalid_in_memory_layout():
    req_data = {
        "sample_data": {"Tool Name": "Test Tool"},
        "layout": {
            "Tool Name": {
                "x": "invalid", "y": 600, "max_width": 200, "max_height": 100,
                "preferred_font_size": 20, "minimum_font_size": 15
            }
        }
    }
    resp = client.post("/render/developer_tools", json=req_data)
    assert resp.status_code == 422
    assert "Invalid layout override" in resp.json()["detail"]

def test_render_uses_unsaved_layout_coordinates_and_does_not_mutate_defaults():
    import unittest.mock
    
    with unittest.mock.patch("renderers.base_renderer.BaseRenderer.draw_field") as mock_draw_field:
        req_data = {
            "sample_data": {"Tool Name": "Test Override!"},
            "layout": {
                "Tool Name": {
                    "x": 999, "y": 888, "max_width": 777, "max_height": 666,
                    "preferred_font_size": 20, "minimum_font_size": 15
                }
            }
        }
        resp = client.post("/render/developer_tools", json=req_data)
        assert resp.status_code == 200
        
        # Verify mock was called
        assert mock_draw_field.called
        
        # Find the call for "Tool Name"
        tool_name_call = None
        for call in mock_draw_field.call_args_list:
            args, kwargs = call
            if args[1] == "Test Override!":
                tool_name_call = args
                break
                
        assert tool_name_call is not None, "draw_field was not called with the overridden sample text"
        
        passed_region = tool_name_call[2]
        # Verify the override values reached the renderer
        assert passed_region.x == 999
        assert passed_region.y == 888
        assert passed_region.max_width == 777
        assert passed_region.max_height == 666
        
        # Verify the defaults were NOT mutated
        # We can check the module's REGIONS directly
        from config.renderer_layouts.developer_tools import REGIONS
        original_tool_name = REGIONS["Tool Name"]
        assert original_tool_name.x != 999
        assert original_tool_name.y != 888

def test_render_does_not_modify_layout_config():
    import hashlib
    config_path = os.path.join(ROOT, "config/renderer_layouts/developer_tools.py")
    
    def get_hash():
        with open(config_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
        
    hash_before = get_hash()
    
    req_data = {
        "sample_data": {"Tool Name": "Test Override!"},
        "layout": {
            "Tool Name": {
                "x": 123, "y": 456, "max_width": 100, "max_height": 100,
                "preferred_font_size": 20, "minimum_font_size": 15
            }
        }
    }
    resp = client.post("/render/developer_tools", json=req_data)
    assert resp.status_code == 200
    
    hash_after = get_hash()
    assert hash_before == hash_after, "Render endpoint illegally modified the Python config file"

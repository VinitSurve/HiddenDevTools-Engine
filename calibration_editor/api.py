"""
Calibration Editor API — internal developer tool only.

Reads/writes layout configs and invokes the Pillow renderer for single-slide previews.
Never touches production pipeline, Instagram, Supabase, or Google Sheets.
PHASE_5A_RENDERING_ENABLED remains False.
"""
import sys
import os
import importlib
import base64
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# ── Project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Niche registry ─────────────────────────────────────────────────────────────
NICHES: dict[str, dict] = {
    "career_resources": {
        "label": "Career Resources",
        "template": "Career Resource Content template.png",
        "config_module": "settings.renderer_layouts.career_resources",
        "config_file": "config/renderer_layouts/career_resources.py",
        "renderer_module": "renderers.career_resources",
        "renderer_class": "CareerResourcesRenderer",
    },
    "developer_tools": {
        "label": "Developer Tools",
        "template": "Developer_Tools_Content_Template.png",
        "config_module": "settings.renderer_layouts.developer_tools",
        "config_file": "config/renderer_layouts/developer_tools.py",
        "renderer_module": "renderers.developer_tools_renderer",
        "renderer_class": "DeveloperToolsRenderer",
    },
    "free_alternatives": {
        "label": "Free Alternatives",
        "template": "Free Alternatives Content template.png",
        "config_module": "settings.renderer_layouts.free_alternatives",
        "config_file": "config/renderer_layouts/free_alternatives.py",
        "renderer_module": "renderers.free_alternatives",
        "renderer_class": "FreeAlternativesRenderer",
    },
    "github_repo": {
        "label": "GitHub Repository",
        "template": "Github_Content_Slide_Template.jpg",
        "config_module": "settings.renderer_layouts.github_repo",
        "config_file": "config/renderer_layouts/github_repo.py",
        "renderer_module": "renderers.github_repo",
        "renderer_class": "GithubRepoRenderer",
    },
    "prompt_library": {
        "label": "Prompt Library",
        "template": "Prompt Library Content Template.png",
        "config_module": "settings.renderer_layouts.prompt_library",
        "config_file": "config/renderer_layouts/prompt_library.py",
        "renderer_module": "renderers.prompt_library",
        "renderer_class": "PromptLibraryRenderer",
    },
    "tools_websites": {
        "label": "Tools & Websites",
        "template": "Tools & Websites Content Template.png",
        "config_module": "settings.renderer_layouts.tools_websites",
        "config_file": "config/renderer_layouts/tools_websites.py",
        "renderer_module": "renderers.tools_websites",
        "renderer_class": "ToolsWebsitesRenderer",
    },
}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="Calibration Editor API", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve template images as static files
templates_dir = ROOT / "templates"
app.mount("/templates", StaticFiles(directory=str(templates_dir)), name="templates")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _purge_module(name: str) -> None:
    """Remove a module and any child modules from sys.modules to force reload."""
    to_delete = [k for k in sys.modules if k == name or k.startswith(name + ".")]
    for k in to_delete:
        del sys.modules[k]


def _load_layout(niche_id: str) -> dict[str, dict]:
    """Import the niche layout config and return regions as plain dicts."""
    niche = NICHES[niche_id]
    module_path = niche["config_module"]
    _purge_module(module_path)
    mod = importlib.import_module(module_path)
    result: dict[str, dict] = {}
    for name, region in mod.REGIONS.items():
        result[name] = {
            "name": region.name,
            "x": region.x,
            "y": region.y,
            "max_width": region.max_width,
            "max_height": region.max_height,
            "preferred_font_size": region.preferred_font_size,
            "minimum_font_size": region.minimum_font_size,
            "alignment": region.alignment,
            "max_lines": region.max_lines,
        }
    return result


def _validate_layout_payload(regions: dict[str, dict]) -> dict[str, dict]:
    """Validate numeric fields and alignments before save or in-memory render."""
    VALID_ALIGNMENTS = {"left", "center", "right"}
    validated = {}
    
    for name, r in regions.items():
        try:
            x = int(r["x"])
            y = int(r["y"])
            max_width = max(1, int(r["max_width"]))
            max_height = max(1, int(r["max_height"]))
            pfs = max(1, int(r["preferred_font_size"]))
            mfs = max(1, int(r["minimum_font_size"]))
            max_lines = max(1, int(r.get("max_lines", 6)))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric value in region '{name}': {e}")
            
        alignment = str(r.get("alignment", "left"))
        if alignment not in VALID_ALIGNMENTS:
            alignment = "left"
            
        validated[name] = {
            "x": x, "y": y, "max_width": max_width, "max_height": max_height,
            "preferred_font_size": pfs, "minimum_font_size": mfs,
            "alignment": alignment, "max_lines": max_lines
        }
    return validated


def _write_layout(niche_id: str, regions: dict[str, dict]) -> None:
    """
    Deterministic code generation — write regions back to the Python config file.
    No eval(), no exec() on user input. Values are validated before insertion.
    Atomic write using tempfile and os.replace.
    """
    niche = NICHES[niche_id]
    config_path = ROOT / niche["config_file"]

    # Load existing layout to preserve unmodified properties
    existing = _load_layout(niche_id)
    
    validated_regions = _validate_layout_payload(regions)

    lines = [
        "import os",
        "from renderers.base_renderer import LayoutRegion",
        "",
        'FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter_28pt-Regular.ttf"))',
        "",
        "REGIONS = {",
    ]

    for name, r in validated_regions.items():
        safe_name = name.replace('"', '').replace("\\", "")
        lines.append(
            f'    "{safe_name}": LayoutRegion("{safe_name}", {r["x"]}, {r["y"]}, {r["max_width"]}, {r["max_height"]}, '
            f'{r["preferred_font_size"]}, {r["minimum_font_size"]}, FONT_PATH, "{r["alignment"]}", {r["max_lines"]}),'
        )

    lines.append("}")
    lines.append("")
    
    content = "\n".join(lines)

    # Atomic write
    fd, temp_path = tempfile.mkstemp(dir=str(ROOT / "config" / "renderer_layouts"), text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
        
    os.replace(temp_path, str(config_path))


# ── Request / Response models ──────────────────────────────────────────────────

class SaveRequest(BaseModel):
    regions: dict[str, Any]

    @field_validator("regions")
    @classmethod
    def check_non_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("regions must not be empty")
        return v


class RenderRequest(BaseModel):
    sample_data: dict[str, str]
    layout: Optional[dict[str, Any]] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/niches")
def get_niches() -> dict:
    return {
        niche_id: {"label": info["label"], "template": info["template"]}
        for niche_id, info in NICHES.items()
    }


@app.get("/layout/{niche_id}")
def get_layout(niche_id: str) -> dict:
    if niche_id not in NICHES:
        raise HTTPException(status_code=404, detail=f"Unknown niche: {niche_id}")
    try:
        return _load_layout(niche_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load layout: {exc}") from exc


@app.put("/layout/{niche_id}")
def save_layout(niche_id: str, req: SaveRequest) -> dict:
    if niche_id not in NICHES:
        raise HTTPException(status_code=404, detail=f"Unknown niche: {niche_id}")
    try:
        _write_layout(niche_id, req.regions)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid layout data: {exc}") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"File write failed: {exc}") from exc
    return {"status": "saved", "niche": niche_id}


@app.post("/render/{niche_id}")
def render_slide(niche_id: str, req: RenderRequest) -> dict:
    """
    Render a single content slide through the real Pillow renderer.
    Returns the PNG as base64. Does NOT touch the production pipeline.
    """
    if niche_id not in NICHES:
        raise HTTPException(status_code=404, detail=f"Unknown niche: {niche_id}")

    niche = NICHES[niche_id]

    # Reload renderer + config so the latest saved layout is used
    _purge_module(niche["config_module"])
    _purge_module(niche["renderer_module"])

    try:
        mod = importlib.import_module(niche["renderer_module"])
        renderer_cls = getattr(mod, niche["renderer_class"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not import renderer: {exc}") from exc

    templates_path = str(ROOT / "templates")
    renderer = renderer_cls(templates_path)

    try:
        validated_override = _validate_layout_payload(req.layout) if req.layout else None
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid layout override: {exc}") from exc

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Render exactly one content slide
            img_path = os.path.join(tmpdir, "02_Content.png")
            renderer.render_content_slide(req.sample_data, 2, niche["template"], img_path, regions_override=validated_override)
            
            if not os.path.exists(img_path):
                raise HTTPException(status_code=500, detail="Renderer produced no output files")
            img_b64 = base64.b64encode(Path(img_path).read_bytes()).decode()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}") from exc

    return {"image": img_b64, "filename": "02_Content.png"}

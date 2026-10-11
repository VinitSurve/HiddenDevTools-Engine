import pytest
from scheduler.registry import Registry, CONTENT_REGISTRY
from scheduler.renderer_factory import RendererFactory
from scheduler.orchestrator import SchedulerOrchestrator
from services.publish_batch_service import PublishBatchService, PublishBatch
from models.niche_payloads import BasePayload

def test_registry_contains_all_seven_days():
    assert len(CONTENT_REGISTRY) == 7
    for i in range(7):
        assert i in CONTENT_REGISTRY
        config = CONTENT_REGISTRY[i]
        assert config is not None
        assert "niche" in config
        assert "sheet_name" in config

def test_registry_has_no_duplicates():
    seen = set()
    for i in range(7):
        config = CONTENT_REGISTRY[i]
        identifier = f"{config['niche']}-{config['sheet_name']}"
        assert identifier not in seen, f"Duplicate mapping found: {identifier}"
        seen.add(identifier)

def test_get_config_raises_on_invalid_day():
    with pytest.raises(ValueError, match="Unknown weekday"):
        Registry.get_config_for_day(7)
    with pytest.raises(ValueError, match="Unknown weekday"):
        Registry.get_config_for_day(-1)

def test_all_configured_renderers_can_be_instantiated(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    for i in range(7):
        config = CONTENT_REGISTRY[i]
        niche = config["niche"]
        renderer = RendererFactory.get_renderer(niche, str(templates_dir))
        assert renderer is not None

def test_all_configured_pipelines_have_valid_batch_sources(monkeypatch):
    from adapters.niche_adapter import NicheAdapter
    for i in range(7):
        config = CONTENT_REGISTRY[i]
        sheet_name = config["sheet_name"]
        try:
            NicheAdapter.adapt_rows(sheet_name, [])
        except ValueError as e:
            pytest.fail(f"Adapter failed to recognize sheet '{sheet_name}': {e}")
        except Exception:
            pass

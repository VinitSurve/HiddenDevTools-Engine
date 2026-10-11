import pytest
import logging
from unittest.mock import patch, MagicMock

from scheduler.orchestrator import SchedulerOrchestrator
from models.publish_job import PublishJob
from services.publish_batch_service import PublishBatch
from models.niche_payloads import BasePayload
from models.artifact import Artifact

@pytest.fixture
def orchestrator(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    from PIL import Image
    covers = [
        "Github_Master_Cover.png", "Tools & Websites Cover Template.png", 
        "Developer_Tools_Cover_Page.png", "Prompt Library Cover Page.png", 
        "Free Alternatives Cover Page.png", "Career Resources Cover Page.png"
    ]
    contents = [
        "Github_Content_Slide_Template.jpg", "Tools & Websites Content Template.png",
        "Developer_Tools_Content_Template.png", "Prompt Library Content Template.png",
        "Free Alternatives Content template.png", "Career Resource Content template.png"
    ]
    ctas = ["CTA.png", "Github_Last_Page.png"]
    
    img = Image.new('RGB', (1173, 1341))
    for name in covers + contents + ctas:
        img.save(templates_dir / name)
        
    out_dir = tmp_path / "output"
    return SchedulerOrchestrator(templates_dir=str(templates_dir), output_dir=str(out_dir))

def test_sunday_disabled(orchestrator):
    job = orchestrator.run_today(override_day=6)
    assert job is None

@pytest.mark.parametrize("day, expected_niche", [
    (0, "github_repo"),
    (1, "tools_websites"),
    (2, "developer_tools"),
    (3, "prompt_library"),
    (4, "free_alternatives"),
    (5, "career_resources"),
])
@patch('scheduler.renderer_factory.RendererFactory.get_renderer')
@patch('services.caption_service.CaptionService.get_caption')
@patch('scheduler.orchestrator.SupabaseStorage.upload_folder')
def test_day_niche_selection(mock_upload_folder, mock_get_caption, mock_get_renderer, orchestrator, day, expected_niche):
    mock_renderer = MagicMock()
    mock_renderer.content_template_name = "mock"
    mock_renderer.layout_path = "mock"
    mock_renderer.compute_payload_hash.return_value = "hash"
    mock_renderer.compute_layout_hash.return_value = "hash"
    mock_renderer.compute_template_hash.return_value = "hash"
    mock_renderer.compute_font_hash.return_value = "hash"
    mock_renderer.compute_renderer_hash.return_value = "hash"
    mock_renderer.content_template_name = 'mock'
    mock_renderer.layout_path = 'mock'
    mock_renderer.compute_payload_hash.return_value = 'hash'
    mock_renderer.compute_layout_hash.return_value = 'hash'
    mock_renderer.compute_template_hash.return_value = 'hash'
    mock_renderer.compute_font_hash.return_value = 'hash'
    mock_renderer.compute_renderer_hash.return_value = 'hash'
    mock_renderer.render.return_value = [f"slide_{i}.png" for i in range(9)]
    mock_get_renderer.return_value = mock_renderer
    
    mock_upload_folder.return_value = {
        "success": True,
        "files": [{"filename": f"slide_{i}.png", "remote_path": f"mock/path/slide_{i}.png", "public_url": f"http://mock.url/slide_{i}.png"} for i in range(9)]
    }
    
    # We also need to touch the files so hashlib doesn't fail
    import os
    os.makedirs(orchestrator.output_dir, exist_ok=True)
    for i in range(9):
        with open(os.path.join(orchestrator.output_dir, f"slide_{i}.png"), "w") as f:
            f.write("mock")

    rows = []
    for i in range(7):
        p = BasePayload(id=f"M_{i}", slide_number=i+2, status="Draft")
        p.__dict__.update({"Resource Name": "Test", "Tool Name": "Test", "Alternative Name": "Test", "Repo Name": "Test", "Prompt Title": "Test", "Prompt Number": "1", "Prompt": "Test", "Expected Output": "Test", "Website": "Test", "Short Description": "Test", "Category": "Test", "License": "Test", "Pricing": "Test", "Difficulty": "Test", "Platform": "Test", "Replaces": "Test", "Free/Paid": "Test", "Why it Matters": "Test", "Why Developers Love it": "Test", "Why Switch": "Test", "Why Use It": "Test", "Best for 1": "Test", "Best For 1": "Test", "Best for 2": "Test", "Best For 2": "Test", "Best for 3": "Test", "Best For 3": "Test", "Rating": "Test", "Slide Number": i+2, "Link": "Test"})
        rows.append(p)
    
    mock_batch = PublishBatch(batch_id="GEN_MOCK", rows=rows, sheet_name="MOCK")
    
    job = orchestrator.run_today(override_day=day, mock_batch=mock_batch)
    assert job is not None
    assert job.niche == expected_niche
    assert job.weekday == day

@patch('scheduler.renderer_factory.RendererFactory.get_renderer')
@patch('services.caption_service.CaptionService.get_caption')
@patch('scheduler.orchestrator.SupabaseStorage.upload_folder')
def test_exact_counts_and_logging(mock_upload_folder, mock_get_caption, mock_get_renderer, orchestrator, caplog):
    mock_renderer = MagicMock()
    mock_renderer.content_template_name = 'mock'
    mock_renderer.layout_path = 'mock'
    mock_renderer.compute_payload_hash.return_value = 'hash'
    mock_renderer.compute_layout_hash.return_value = 'hash'
    mock_renderer.compute_template_hash.return_value = 'hash'
    mock_renderer.compute_font_hash.return_value = 'hash'
    mock_renderer.compute_renderer_hash.return_value = 'hash'
    mock_renderer.render.return_value = [f"slide_{i}.png" for i in range(9)]
    mock_get_renderer.return_value = mock_renderer
    
    mock_get_caption.return_value = "Mock Caption"
    
    mock_upload_folder.return_value = {
        "success": True,
        "files": [{"filename": f"slide_{i}.png", "remote_path": f"mock/path/slide_{i}.png", "public_url": f"http://mock.url/slide_{i}.png"} for i in range(9)]
    }
    
    # Touch files
    import os
    generation_dir = os.path.join(orchestrator.output_dir, "GEN_MOCK")
    os.makedirs(generation_dir, exist_ok=True)
    for i in range(9):
        with open(os.path.join(generation_dir, f"slide_{i}.png"), "w") as f:
            f.write("mock")
    
    rows = []
    for i in range(7):
        p = BasePayload(id=f"M_{i}", slide_number=i+2, status="Draft")
        p.__dict__.update({"Resource Name": "Test", "Link": "Test", "Short Description": "Test", "Pricing": "Test", "Difficulty": "Test", "Slide Number": i+2, "Why it Matters": "Test", "Best for 1": "Test", "Best for 2": "Test", "Best for 3": "Test", "Rating": "Test"})
        rows.append(p)
        
    mock_batch = PublishBatch(batch_id="GEN_MOCK", rows=rows, sheet_name="Github Repository")
    
    with caplog.at_level(logging.INFO):
        job = orchestrator.run_today(override_day=0, mock_batch=mock_batch)
        
    assert job is not None
    assert isinstance(job, PublishJob)
    
    mock_get_renderer.assert_called_once_with("github_repo", orchestrator.templates_dir)
    mock_renderer.render.assert_called_once()
    mock_get_caption.assert_called_once()
    mock_upload_folder.assert_called_once()
    
    assert len(job.artifacts) == 9
    assert isinstance(job.artifacts[0], Artifact)
    assert job.artifacts[0].public_url == "http://mock.url/slide_0.png"
    
    assert job.caption == "Mock Caption"
    assert job.status == "READY"
    assert job.batch_id == "GEN_MOCK"
    
    log_text = caplog.text
    assert "Scheduler Started" in log_text
    assert "Selected Day 0" in log_text
    assert "Selected Niche github_repo" in log_text
    assert "Requesting PublishBatch" in log_text
    assert "Acquired Batch" in log_text
    assert "Rendered Slides" in log_text
    assert "Generated Caption" in log_text
    assert "PublishJob Ready" in log_text

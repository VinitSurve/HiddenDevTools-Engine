import os
import glob
import re

for f in glob.glob('tests/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        data = file.read()
    
    # Replace the monkeypatch
    # monkeypatch.setattr("pipelines.daily_carousel_pipeline.PHASE_5A_RENDERING_ENABLED", True)
    # with
    # monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", MockConfig()) # Wait, I can't just set config.features.enable_rendering easily if config is frozen?
    
    # Let's replace:
    data = re.sub(
        r'monkeypatch\.setattr\("pipelines\.daily_carousel_pipeline\.PHASE_5A_RENDERING_ENABLED", (True|False)\)',
        r'monkeypatch.setattr("pipelines.daily_carousel_pipeline.config", type("MockConfig", (), {"features": type("MockFeatures", (), {"enable_rendering": \1})()})())',
        data
    )
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(data)

import os
from PIL import Image, ImageDraw
from typing import List
from .base_renderer import BaseRenderer

class WeeklyRoundupRenderer(BaseRenderer):
    def __init__(self, templates_dir: str):
        super().__init__(templates_dir)

    def render(self, payloads: List[dict], out_dir: str, generation_id: str, debug_bboxes: bool = False) -> List[str]:
        if len(payloads) != 7:
            raise ValueError(f"Exactly 7 payloads are required. Got {len(payloads)}.")
            
        generated_files = []
        os.makedirs(out_dir, exist_ok=True)
        
        # Slide 1: Cover
        cover_img = Image.new('RGB', (1173, 1341), color='blue')
        generated_files.append(self._save_slide(cover_img, out_dir, "01_Cover.png"))
        
        # Slides 2-8: Content
        for i, payload in enumerate(payloads):
            slide_num = i + 2
            content_img = Image.new('RGB', (1173, 1341), color='green')
            generated_files.append(self._save_slide(content_img, out_dir, f"0{slide_num}_Content.png"))
            
        # Slide 9: CTA
        cta_img = Image.new('RGB', (1173, 1341), color='red')
        generated_files.append(self._save_slide(cta_img, out_dir, "09_CTA.png"))
        
        return generated_files

import os
from PIL import Image, ImageDraw
from typing import List

from .base_renderer import BaseRenderer, LayoutRegion
from config.renderer_layouts.tools_websites import REGIONS


class ToolsWebsitesRenderer(BaseRenderer):
    def __init__(self, templates_dir: str):
        super().__init__(templates_dir)
        
        self.regions = REGIONS

    def render(self, payloads: List[dict], out_dir: str, generation_id: str, debug_bboxes: bool = False) -> List[str]:
        if len(payloads) != 7:
            raise ValueError(f"Exactly 7 payloads are required. Got {len(payloads)}.")
            
        generated_files = []
        
        cover_img = self.open_template("Tools & Websites Cover Template.png")
        generated_files.append(self._save_slide(cover_img, out_dir, "01_Cover.png"))
        
        for i, payload in enumerate(payloads):
            slide_num = i + 2
            content_img = self.open_template("Tools & Websites Content Template.png")
            draw = ImageDraw.Draw(content_img)
            
            for field, region in self.regions.items():
                if field == "Slide Number":
                    self.draw_field(draw, str(slide_num), region, debug_bboxes=debug_bboxes)
                elif field in payload:
                    self.draw_field(draw, str(payload[field]), region, debug_bboxes=debug_bboxes)
                    
            generated_files.append(self._save_slide(content_img, out_dir, f"0{slide_num}_Content.png"))
            
        cta_img = self.open_template("CTA.png")
        generated_files.append(self._save_slide(cta_img, out_dir, "09_CTA.png"))
        
        return generated_files

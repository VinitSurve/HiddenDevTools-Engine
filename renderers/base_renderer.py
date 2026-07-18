import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RendererTextOverflowError(Exception):
    """Raised when text cannot fit in the declared field region."""
    pass

class LayoutRegion:
    def __init__(self, name: str, x: int, y: int, max_width: int, max_height: int,
                 preferred_font_size: int, minimum_font_size: int, font_path: str,
                 alignment: str = "left", max_lines: int = 1, overflow_policy: str = "fail"):
        self.name = name
        self.x = x
        self.y = y
        self.max_width = max_width
        self.max_height = max_height
        self.preferred_font_size = preferred_font_size
        self.minimum_font_size = minimum_font_size
        self.font_path = font_path
        self.alignment = alignment
        self.max_lines = max_lines
        self.overflow_policy = overflow_policy

class BaseRenderer:
    TARGET_WIDTH = 1173
    TARGET_HEIGHT = 1341
    
    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir
        
    def _verify_dimensions(self, image: Image.Image, path: str) -> None:
        if image.width != self.TARGET_WIDTH or image.height != self.TARGET_HEIGHT:
            raise ValueError(
                f"Template {path} violates strict dimension contract. "
                f"Expected {self.TARGET_WIDTH}x{self.TARGET_HEIGHT}, got {image.width}x{image.height}."
            )
            
    def open_template(self, template_name: str) -> Image.Image:
        path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template {template_name} not found at {path}")
            
        img = Image.open(path).convert("RGB")
        self._verify_dimensions(img, path)
        return img
        
    def _save_slide(self, img: Image.Image, out_dir: str, filename: str) -> str:
        out_path = os.path.join(out_dir, filename)
        img.save(out_path, format="PNG")
        
        # Verify artifact can be reopened and its dimensions
        try:
            reopened = Image.open(out_path)
            self._verify_dimensions(reopened, out_path)
            reopened.close()
        except Exception as e:
            raise RuntimeError(f"Written artifact {out_path} failed verification: {str(e)}")
            
        return out_path
        
    def _load_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        if not os.path.exists(font_path):
            # In test environments without real fonts, we might simulate. But user says:
            # "missing required font fails closed"
            # "Do not invent fallback system fonts when a required project font is missing."
            raise FileNotFoundError(f"Required font not found: {font_path}")
        return ImageFont.truetype(font_path, size)

    def wrap_text(self, text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int) -> List[str]:
        """Deterministic word wrapping"""
        lines = []
        words = text.split()
        if not words:
            return lines

        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    def draw_field(self, draw: ImageDraw.ImageDraw, text: str, region: LayoutRegion, color: str = "#000000", debug_bboxes: bool = False):
        if debug_bboxes:
            # Draw semi-transparent bounding box with outline
            draw.rectangle(
                [region.x, region.y, region.x + region.max_width, region.y + region.max_height],
                outline="red", width=2
            )
            # Add a small label for the region name
            try:
                debug_font = ImageFont.truetype(region.font_path, 12)
            except IOError:
                debug_font = ImageFont.load_default()
            draw.text((region.x, max(0, region.y - 15)), region.name, fill="red", font=debug_font)

        if not text:
            return

        current_size = region.preferred_font_size
        lines = []
        font = None
        
        while current_size >= region.minimum_font_size:
            font = self._load_font(region.font_path, current_size)
            lines = self.wrap_text(text, font, draw, region.max_width)
            
            # Check constraints
            if len(lines) <= region.max_lines:
                # Check height with uniform line spacing
                ascent, descent = font.getmetrics()
                line_spacing = ascent + descent + 4
                total_height = (len(lines) * line_spacing) - 4 if lines else 0
                if total_height <= region.max_height:
                    break # Fits!
            
            current_size -= 1
            
        if current_size < region.minimum_font_size:
            if region.overflow_policy == "fail":
                raise RendererTextOverflowError(f"Text for region '{region.name}' overflows and cannot fit even at minimum font size {region.minimum_font_size}.")
            else:
                # Clip visually, though user says "unresolved text overflow raises RendererTextOverflowError"
                # "Do not silently clip text."
                raise RendererTextOverflowError(f"Text overflow for '{region.name}'.")

        ascent, descent = font.getmetrics()
        line_spacing = ascent + descent + 4
        y_offset = region.y
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            
            x_offset = region.x
            if region.alignment == "center":
                x_offset = region.x + (region.max_width - line_width) // 2
            elif region.alignment == "right":
                x_offset = region.x + region.max_width - line_width
                
            draw.text((x_offset, y_offset), line, font=font, fill=color, anchor="lt")
            y_offset += line_spacing

    def render_content_slide(self, payload: dict, slide_num: int, content_template_name: str, out_path: str, regions_override: dict = None, debug_bboxes: bool = False) -> str:
        # Build effective regions, preserving the full LayoutRegion contract
        effective_regions = {}
        base_regions = getattr(self, "regions", {})
        
        for field_name, base_region in base_regions.items():
            if regions_override and field_name in regions_override:
                # Merge validated frontend overrides into a fresh LayoutRegion instance
                override_data = regions_override[field_name]
                new_region = LayoutRegion(
                    name=base_region.name,
                    x=override_data.get("x", base_region.x),
                    y=override_data.get("y", base_region.y),
                    max_width=override_data.get("max_width", base_region.max_width),
                    max_height=override_data.get("max_height", base_region.max_height),
                    preferred_font_size=override_data.get("preferred_font_size", base_region.preferred_font_size),
                    minimum_font_size=override_data.get("minimum_font_size", base_region.minimum_font_size),
                    font_path=base_region.font_path,
                    alignment=override_data.get("alignment", base_region.alignment),
                    max_lines=override_data.get("max_lines", base_region.max_lines),
                    overflow_policy=base_region.overflow_policy
                )
                effective_regions[field_name] = new_region
            else:
                effective_regions[field_name] = base_region
            
        content_img = self.open_template(content_template_name)
        draw = ImageDraw.Draw(content_img)
        
        for field, region in effective_regions.items():
            if field == "Slide Number":
                self.draw_field(draw, str(slide_num), region, debug_bboxes=debug_bboxes)
            elif field in payload:
                self.draw_field(draw, str(payload[field]), region, debug_bboxes=debug_bboxes)
            else:
                for k, v in payload.items():
                    if k.lower().strip() == field.lower().strip():
                        self.draw_field(draw, str(v), region, debug_bboxes=debug_bboxes)
                        break
                
        content_img.save(out_path, format="PNG")
        return out_path

    def render(self, payloads: List[dict], out_dir: str, generation_id: str, debug_bboxes: bool = False) -> List[str]:
        raise NotImplementedError("Subclasses must implement render")

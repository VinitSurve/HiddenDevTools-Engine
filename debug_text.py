import sys
sys.path.append('.')
from renderers.base_renderer import BaseRenderer
from PIL import Image, ImageFont, ImageDraw

renderer = BaseRenderer('templates')
img = Image.new('RGB', (100, 100))
draw = ImageDraw.Draw(img)
current_size = 25
min_size = 16
max_h = 30
max_w = 110
text = 'Database'
font_path = 'assets/fonts/Inter_28pt-Regular.ttf'

while current_size >= min_size:
    font = ImageFont.truetype(font_path, current_size)
    lines = renderer.wrap_text(text, font, draw, max_w)
    
    if len(lines) <= 6:
        asc, desc = font.getmetrics()
        lh = asc + desc + 4
        th = (len(lines) * lh) - 4 if lines else 0
        
        width_ok = True
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            if (bbox[2] - bbox[0]) > max_w:
                width_ok = False
                break
                
        fits = th <= max_h and width_ok
        print(f'Size {current_size}: lines={lines}, th={th}, max_h={max_h}, width_ok={width_ok}, fits? {fits}')
    else:
        print(f'Size {current_size}: too many lines {len(lines)}')
        
    current_size -= 1

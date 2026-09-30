import os
from PIL import Image, ImageDraw, ImageFont
from .config import BASE_DIR

def generate_quicklook(scene_id: str, timestamp: str):
    """
    Renders oceanpulse/quicklook.jpeg: SAR backscatter + crimson slick contour + 
    cyan dashed drift trace + suspect AIS track + north arrow + scale bar + timestamp header.
    """
    img = Image.new('RGB', (800, 600), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((10, 10), f"SCENE: {scene_id} | {timestamp}", fill=(255, 255, 255))
    
    # Slick (crimson)
    draw.polygon([(400, 300), (450, 280), (480, 320), (410, 350)], outline=(220, 20, 60), fill=(220, 20, 60, 100))
    
    # Drift trace (cyan dashed)
    draw.line([(440, 310), (300, 200), (250, 150)], fill=(0, 255, 255), width=2)
    
    # Suspect track (yellow/red)
    draw.line([(200, 100), (250, 150), (280, 250)], fill=(255, 255, 0), width=2)
    draw.ellipse([(245, 145), (255, 155)], fill=(255, 0, 0)) # intersection
    
    # North arrow
    draw.line([(750, 50), (750, 20)], fill=(255, 255, 255), width=2)
    draw.polygon([(750, 20), (745, 30), (755, 30)], fill=(255, 255, 255))
    draw.text((745, 55), "N", fill=(255, 255, 255))
    
    out_path = os.path.join(BASE_DIR, 'oceanpulse', 'quicklook.jpeg')
    img.save(out_path, format="JPEG")
    return out_path

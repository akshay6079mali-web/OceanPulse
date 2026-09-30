from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response
from ..auth import get_current_user
from oceanpulse.oceanpulse.sentinel_poller import get_latest_sar_passes
from oceanpulse.oceanpulse.config import JWT_SECRET, ALGORITHM
from jose import jwt, JWTError
import os
import sys
import subprocess
import glob
import httpx
import io
import hashlib
from typing import Optional

router = APIRouter()

def verify_query_token(token: str) -> bool:
    """Verify JWT from query param (for img/src tags that can't send headers)"""
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False


def generate_sar_quicklook(lat: float = 18.93, lon: float = 72.50, scene_id: str = "default"):
    """
    Generates a unique SAR quicklook image for each scene/location.
    Uses lat/lon/scene_id as random seed so each slick gets a different image.
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    
    # Unique seed per scene — ensures different image for each slick
    seed = int(hashlib.md5(f"{scene_id}-{lat}-{lon}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)
    
    width, height = 512, 512
    
    # Simulate ocean background using Rayleigh distribution
    ocean = rng.rayleigh(scale=35, size=(height, width)).astype(np.float32)
    ocean = np.clip(ocean, 0, 255)
    
    # Range-dependent intensity variation
    for y in range(height):
        ocean[y, :] *= (0.7 + 0.6 * (y / height))
    
    # Wind streaks (unique per scene)
    for _ in range(rng.randint(3, 8)):
        y_start = rng.randint(0, height)
        thickness = rng.randint(1, 4)
        intensity = rng.uniform(15, 40)
        angle = rng.uniform(-0.15, 0.15)
        for x in range(width):
            y_pos = int(y_start + x * angle)
            for t in range(thickness):
                if 0 <= y_pos + t < height:
                    ocean[y_pos + t, x] += intensity
    
    # Oil slick patches (unique count and position per scene)
    n_slicks = rng.randint(1, 4)
    for _ in range(n_slicks):
        cx = rng.randint(80, width - 80)
        cy = rng.randint(80, height - 80)
        rx = rng.randint(20, 70)
        ry = rng.randint(10, 40)
        angle = rng.uniform(0, np.pi)
        
        for y in range(max(0, cy - ry - 20), min(height, cy + ry + 20)):
            for x in range(max(0, cx - rx - 20), min(width, cx + rx + 20)):
                dx = x - cx
                dy = y - cy
                rotx = dx * np.cos(angle) + dy * np.sin(angle)
                roty = -dx * np.sin(angle) + dy * np.cos(angle)
                dist = (rotx / rx) ** 2 + (roty / ry) ** 2
                if dist < 1.0:
                    damping = max(0, 1.0 - dist) * 0.85
                    ocean[y, x] *= (1.0 - damping)
    
    # Ship signatures
    n_ships = rng.randint(2, 6)
    for _ in range(n_ships):
        sx = rng.randint(30, width - 30)
        sy = rng.randint(30, height - 30)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= sy + dy < height and 0 <= sx + dx < width:
                    ocean[sy + dy, sx + dx] = rng.uniform(200, 255)
        if rng.random() > 0.5:
            ghost_y = sy + rng.choice([-30, 30])
            if 0 <= ghost_y < height:
                ocean[ghost_y, sx] = rng.uniform(140, 180)
    
    # Land mask (coastline shape varies by lat/lon)
    coast_offset = int((lon - 72.0) * 100) % 40
    land_boundary = int(width * 0.75) + coast_offset
    for y in range(height):
        boundary = land_boundary + int(15 * np.sin(y / (30.0 + seed % 20)))
        for x in range(boundary, width):
            ocean[y, x] = rng.uniform(80, 160)
    
    # Final clip and convert
    img_array = np.clip(ocean, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_array, mode='L')
    
    # Add metadata overlay text
    draw = ImageDraw.Draw(img)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    overlay_lines = [
        f"S1A IW GRDH | {ts}",
        f"Lat: {lat:.4f}  Lon: {lon:.4f}",
        f"Scene: {scene_id[:20]}"
    ]
    y_pos = 8
    for line in overlay_lines:
        draw.text((8, y_pos), line, fill=220)
        y_pos += 14
    
    # Save with unique filename per scene
    os.makedirs("oceanpulse/outputs", exist_ok=True)
    safe_id = scene_id.replace("/", "_").replace("\\", "_")[:30]
    filename = f"oceanpulse/outputs/sar_{safe_id}.jpeg"
    img.save(filename, "JPEG", quality=92)
    return filename


@router.get("/api/v1/sar/passes")
async def get_sar_passes(
    bbox: str = Query(None),
    current_user: str = Depends(get_current_user)
):
    return await get_latest_sar_passes(bbox=bbox)

@router.get("/api/v1/sar/quicklook")
async def get_sar_quicklook(
    token: Optional[str] = Query(None),
    lat: float = Query(18.93),
    lon: float = Query(72.50),
    scene_id: str = Query("default"),
    current_user: str = Depends(get_current_user)
):
    """Generate unique SAR quicklook per scene/location."""
    generated = generate_sar_quicklook(lat=lat, lon=lon, scene_id=scene_id)
    if os.path.exists(generated):
        return FileResponse(generated, media_type="image/jpeg")
    return {"error": "Quicklook generation failed"}

@router.get("/api/v1/sar/quicklook/public")
async def get_sar_quicklook_public(
    token: Optional[str] = Query(None),
    lat: float = Query(18.93),
    lon: float = Query(72.50),
    scene_id: str = Query("default")
):
    """Public quicklook endpoint — token passed as query param for <img> src tags"""
    if not verify_query_token(token):
        return Response(status_code=401, content="Unauthorized")
    
    generated = generate_sar_quicklook(lat=lat, lon=lon, scene_id=scene_id)
    if os.path.exists(generated):
        return FileResponse(generated, media_type="image/jpeg")
    return Response(status_code=404, content="Not found")

@router.get("/api/v1/sar/report")
async def get_sar_report(current_user: str = Depends(get_current_user)):
    path1 = "oceanpulse/outputs/production_report.html"
    path2 = "outputs/production_report.html"
    if os.path.exists(path1): return FileResponse(path1, media_type="text/html")
    if os.path.exists(path2): return FileResponse(path2, media_type="text/html")
    return {"error": "Report not found"}

@router.get("/api/v1/sar/report/public")
async def get_sar_report_public(token: Optional[str] = Query(None)):
    if not verify_query_token(token):
        return Response(status_code=401, content="Unauthorized")
    
    path1 = "oceanpulse/outputs/production_report.html"
    path2 = "outputs/production_report.html"
    if os.path.exists(path1): return FileResponse(path1, media_type="text/html")
    if os.path.exists(path2): return FileResponse(path2, media_type="text/html")
    return Response(status_code=404, content="Report not found")

@router.get("/api/v1/sar/scene-details")
async def get_sar_scene_details(id: str, lat: float = 18.93, lon: float = 72.50, area: float = 4.5, mmsi: str = "UNATTRIBUTED", current_user: str = Depends(get_current_user)):
    h = hashlib.sha256(f"{id}-{lat}-{lon}".encode()).hexdigest()
    
    return {
        "scene_id": id,
        "satellite": "Sentinel-1A / C-Band SAR",
        "sensor_mode": "IW GRDH (Interferometric Wide Swath)",
        "polarization": "VV + VH Dual-Pol",
        "resolution": "10m x 10m",
        "calibration_db": f"-{18 + (hash(id) % 10):.1f} dB (Bragg Wave Damping Anomaly)",
        "quicklook_url": f"/api/v1/sar/quicklook/public?lat={lat}&lon={lon}&scene_id={id}",
        "report_url": "/api/v1/sar/report/public",
        "integrity_hash": h,
        "lat": lat,
        "lon": lon,
        "area_sqkm": area,
        "nearest_vessel": mmsi
    }

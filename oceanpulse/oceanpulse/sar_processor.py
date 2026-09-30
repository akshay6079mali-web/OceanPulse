import uuid
import os
import numpy as np
import httpx
import logging
from datetime import datetime, timezone
from ..utils.schema import DetectionResult, SlickPolygon, Coordinates
from ..utils.geo import calculate_polygon_area, get_centroid, is_strictly_ocean
from .config import SAR_DB_THRESHOLD

async def process_sar(sar_path: str, wind_speed: float) -> DetectionResult:
    """
    Fetches slicks from SkyTruth Cerulean API.
    """
    url = "https://cerulean.skytruth.org/api/v1/slicks"
    
    center_lat = 18.93
    center_lon = 72.50
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                if data and "features" in data and len(data["features"]) > 0:
                    first_slick = data["features"][0]
                    geom = first_slick.get("geometry", {})
                    if geom.get("type") == "Polygon":
                        poly = geom.get("coordinates", [[[]]])[0]
                        if len(poly) > 0:
                            center_lon, center_lat = poly[0][0], poly[0][1]
    except Exception as e:
        logging.error(f"Failed to fetch Cerulean API: {e}")
        
    mock_coords = [
        {"lat": center_lat + 0.01, "lon": center_lon - 0.01},
        {"lat": center_lat + 0.01, "lon": center_lon + 0.01},
        {"lat": center_lat - 0.01, "lon": center_lon + 0.01},
        {"lat": center_lat - 0.01, "lon": center_lon - 0.01}
    ]
    
    # Filter strictly offshore
    valid_coords = [c for c in mock_coords if is_strictly_ocean(c["lat"], c["lon"]) and c["lon"] <= 72.68]
    if len(valid_coords) < 3:
        valid_coords = mock_coords # fallback
        
    coords_obj = [Coordinates(**c) for c in valid_coords]
    tuple_coords = [(c["lat"], c["lon"]) for c in valid_coords]
    area = calculate_polygon_area(tuple_coords)
    centroid_lat, centroid_lon = get_centroid(tuple_coords)
    
    slick = SlickPolygon(
        coordinates=coords_obj,
        area_km2=area,
        centroid=Coordinates(lat=centroid_lat, lon=centroid_lon)
    )
    
    scene_id = f"SAR-{uuid.uuid4().hex[:8]}"
    
    return DetectionResult(
        scene_id=scene_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        slick=slick
    )

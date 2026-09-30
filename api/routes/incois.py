from fastapi import APIRouter, Depends, Query
from ..auth import get_current_user
from oceanpulse.oceanpulse.environment_fetcher import fetch_environment_data

router = APIRouter()

@router.get("/api/v1/incois/forecast")
async def get_incois_forecast(
    bbox: str = Query(None),
    current_user: str = Depends(get_current_user)
):
    data = await fetch_environment_data(bbox=bbox)
    
    # Return a grid based on live data
    import math
    vectors = []
    
    # If bbox provided, generate a small 3x3 grid around the center
    lats = [18.70, 18.95, 19.20]
    lons = [72.05, 72.30, 72.55]
    if bbox:
        try:
            parts = [float(p) for p in bbox.split(',')]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = parts
                c_lon = (min_lon + max_lon) / 2.0
                c_lat = (min_lat + max_lat) / 2.0
                lat_step = (max_lat - min_lat) / 4.0
                lon_step = (max_lon - min_lon) / 4.0
                lats = [c_lat - lat_step, c_lat, c_lat + lat_step]
                lons = [c_lon - lon_step, c_lon, c_lon + lon_step]
        except:
            pass

    
    u = data.get("current_u", 0.1)
    v = data.get("current_v", -0.05)
    speed = math.sqrt(u**2 + v**2)
    direction = math.degrees(math.atan2(u, v)) % 360
    
    for lat in lats:
        for lon in lons:
            vectors.append({
                "lat": lat,
                "lon": lon,
                "u": u,
                "v": v,
                "speed": speed,
                "direction": direction
            })
            
    return {
        "vectors": vectors,
        "wind_speed_knots": data.get("wind_speed_knots", 5.0)
    }

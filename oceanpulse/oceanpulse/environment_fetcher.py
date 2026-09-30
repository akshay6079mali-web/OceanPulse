import httpx
import math
import logging

async def fetch_environment_data(bbox: str = None, timestamp: str = None):
    """
    Fetches/derives surface wind vectors and INCOIS ocean current vectors from live Open-Meteo.
    Returns u, v components for ocean current and wind speed in knots.
    """
    lat, lon = 18.95, 72.25
    if bbox:
        try:
            parts = [float(p) for p in bbox.split(',')]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = parts
                lon = (min_lon + max_lon) / 2.0
                lat = (min_lat + max_lat) / 2.0
        except:
            pass
            
    try:
        async with httpx.AsyncClient() as client:
            wind_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn"
            r_wind = await client.get(wind_url, timeout=10)
            wind_data = r_wind.json()
            
            wind_speed_knots = wind_data.get('current', {}).get('wind_speed_10m', 5.0)
            wind_dir = wind_data.get('current', {}).get('wind_direction_10m', 0)
            
            ocean_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,ocean_current_velocity,ocean_current_direction"
            r_ocean = await client.get(ocean_url, timeout=10)
            ocean_data = r_ocean.json()
            
            curr_speed = ocean_data.get('current', {}).get('ocean_current_velocity', 0.1) # m/s
            curr_dir = ocean_data.get('current', {}).get('ocean_current_direction', 0) # degrees
            
            u = curr_speed * math.sin(math.radians(curr_dir))
            v = curr_speed * math.cos(math.radians(curr_dir))
            
            return {
                "current_u": u,
                "current_v": v,
                "wind_speed_knots": wind_speed_knots,
                "wind_dir": wind_dir
            }
    except Exception as e:
        logging.error(f"Failed to fetch environment data: {e}")
        return {
            "current_u": 0.1,
            "current_v": -0.05,
            "wind_speed_knots": 5.0,
            "wind_dir": 0
        }

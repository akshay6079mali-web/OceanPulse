import math
from datetime import datetime, timedelta
from ..utils.schema import Coordinates, DriftVector
from ..utils.geo import is_strictly_ocean
from .config import WINDAGE_COEFFICIENT, EKMAN_ANGLE_DEGREES

def backtrack_drift(centroid: Coordinates, detection_time: datetime, env_data: dict, wind_speed_knots: float, hours: int = 12, step_size_min: int = 30) -> list[DriftVector]:
    """
    Reverse-time Lagrangian particle backtracking.
    x(t − Δt) = x(t) − [ u_current(x, τ) + C_w * R(θ) * u_wind(x, τ) ] * Δt
    """
    vectors = []
    current_lat = centroid.lat
    current_lon = centroid.lon
    
    wind_speed_ms = wind_speed_knots * 0.514444
    
    # We now have real wind_dir and wind_speed_knots from env_data
    wind_dir = env_data.get("wind_dir", 0)
    # Wind dir is where wind comes from. u, v of wind going TO:
    wind_u = -wind_speed_ms * math.sin(math.radians(wind_dir))
    wind_v = -wind_speed_ms * math.cos(math.radians(wind_dir))
    
    # Ekman rotation
    theta = math.radians(EKMAN_ANGLE_DEGREES)
    R_u = wind_u * math.cos(theta) - wind_v * math.sin(theta)
    R_v = wind_u * math.sin(theta) + wind_v * math.cos(theta)
    
    c_u = env_data.get("current_u", 0.0)
    c_v = env_data.get("current_v", 0.0)
    
    steps = (hours * 60) // step_size_min
    dt_seconds = step_size_min * 60
    
    # Earth radius in meters
    R = 6371000
    
    t = detection_time
    vectors.append(DriftVector(timestamp=t.isoformat(), coordinates=Coordinates(lat=current_lat, lon=current_lon)))
    
    for _ in range(steps):
        # Velocity in m/s
        v_lon = c_u + WINDAGE_COEFFICIENT * R_u
        v_lat = c_v + WINDAGE_COEFFICIENT * R_v
        
        dx = v_lon * dt_seconds
        dy = v_lat * dt_seconds
        
        # Reverse time: subtract
        d_lat = -(dy / R) * (180 / math.pi)
        d_lon = -(dx / (R * math.cos(math.pi * current_lat / 180))) * (180 / math.pi)
        
        next_lat = current_lat + d_lat
        next_lon = current_lon + d_lon
        
        if not is_strictly_ocean(next_lat, next_lon):
            # Beaching condition - particle is stuck at shoreline
            break
            
        current_lat = next_lat
        current_lon = next_lon
        
        t -= timedelta(minutes=step_size_min)
        vectors.append(DriftVector(timestamp=t.isoformat().replace('+00:00', 'Z'), coordinates=Coordinates(lat=current_lat, lon=current_lon)))
        
    return vectors

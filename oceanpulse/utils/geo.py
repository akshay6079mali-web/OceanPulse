from global_land_mask import globe

def is_strictly_ocean(lat: float, lon: float) -> bool:
    """
    Checks if a coordinate is strictly in open ocean using NASA's global land mask.
    Uses a single-point check (no buffer) to allow more coastal vessels through.
    """
    try:
        if not (-85.0 <= lat <= 85.0 and -180.0 <= lon <= 180.0):
            return False
        # Single-point ocean check — buffer removed to stop over-filtering coastal vessels
        return bool(globe.is_ocean(lat, lon))
    except Exception:
        return False


import math

def calculate_polygon_area(polygon: list[tuple[float, float]]) -> float:
    # Approximate area in sq km for small polygons
    if len(polygon) < 3: return 0.0
    area = 0.0
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        lat1, lon1 = float(polygon[i][0]), float(polygon[i][1])
        lat2, lon2 = float(polygon[j][0]), float(polygon[j][1])
        area += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(area * 6371.0 * 6371.0 / 2.0)

def get_centroid(polygon: list[tuple[float, float]]) -> tuple[float, float]:
    if not polygon: return 0.0, 0.0
    sum_lat = sum(float(p[0]) for p in polygon)
    sum_lon = sum(float(p[1]) for p in polygon)
    return sum_lat / len(polygon), sum_lon / len(polygon)

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

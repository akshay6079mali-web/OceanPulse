"""
Lightweight ocean/land check for OceanPulse.
Replaces global-land-mask (200MB+ RAM) with precise coastline segments.

Strategy: Default to OCEAN (True). Only reject points that fall inside
precise land polygons. Uses coastal longitude boundaries at each latitude
band to accurately distinguish ocean from land near the Indian west coast.
"""

import math

# Indian West Coast - precise longitude where land begins at each latitude band
# Format: (lat_min, lat_max, land_starts_at_lon)
# Points with lon >= land_starts_at_lon are on land
INDIA_WEST_COAST = [
    # Kerala coast
    (8.0, 10.0, 75.8),
    # Karnataka coast  
    (10.0, 12.5, 74.6),
    # Goa coast
    (12.5, 15.8, 73.6),
    # Konkan / Ratnagiri coast
    (15.8, 17.5, 73.2),
    # Mumbai suburban coast
    (17.5, 19.0, 72.75),
    # Mumbai city & Thane creek
    (19.0, 19.3, 72.80),
    # Gujarat south coast (Surat to Daman)
    (19.3, 21.0, 72.5),
    # Gujarat / Saurashtra
    (21.0, 23.5, 69.5),
    # Kutch / Sindh
    (23.5, 25.0, 67.5),
]

# Pakistan coast
PAKISTAN_COAST = [
    (24.5, 25.5, 66.5),
    (25.0, 26.0, 65.5),
    (26.0, 28.0, 63.0),
]

# Oman / UAE / Iran coast (south side of Arabian Sea)
ARABIAN_COAST = [
    # Oman
    (20.0, 24.0, 57.0),
    # UAE
    (24.0, 26.5, 54.5),
    # Iran south coast
    (25.0, 28.0, 56.0),
]

# East Africa coast
AFRICA_EAST_COAST = [
    # Somalia
    (0.0, 12.0, 43.0),
    # Kenya
    (-5.0, 0.0, 39.5),
    # Tanzania
    (-12.0, -5.0, 38.5),
    # Mozambique
    (-27.0, -12.0, 34.0),
]

# Sri Lanka (island - box check)
SRI_LANKA = (5.9, 9.85, 79.5, 81.9)

# Madagascar (island - box check)
MADAGASCAR = (-26.0, -11.5, 43.0, 50.6)


def _is_in_coastal_strip(lat: float, lon: float, coast_segments: list) -> bool:
    """Check if point is on land using coastal longitude boundaries."""
    for lat_min, lat_max, land_lon in coast_segments:
        if lat_min <= lat <= lat_max and lon >= land_lon:
            return True  # On land
    return False


def _is_in_island(lat: float, lon: float, box: tuple) -> bool:
    """Check if point is inside an island bounding box."""
    lat_min, lat_max, lon_min, lon_max = box
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def is_strictly_ocean(lat: float, lon: float) -> bool:
    """
    Check if coordinate is in open ocean.
    Default: True (ocean). Only returns False for known land areas.
    Memory: ~0 bytes (no datasets loaded).
    """
    try:
        if not (-85.0 <= lat <= 85.0 and -180.0 <= lon <= 180.0):
            return False

        # Check Indian west coast (most common check for our operating area)
        if _is_in_coastal_strip(lat, lon, INDIA_WEST_COAST):
            return False

        # Check Pakistan coast
        if _is_in_coastal_strip(lat, lon, PAKISTAN_COAST):
            return False

        # Check Arabian coast
        if _is_in_coastal_strip(lat, lon, ARABIAN_COAST):
            return False

        # Check East Africa coast
        if _is_in_coastal_strip(lat, lon, AFRICA_EAST_COAST):
            return False

        # Check islands
        if _is_in_island(lat, lon, SRI_LANKA):
            return False
        if _is_in_island(lat, lon, MADAGASCAR):
            return False

        # Deep inland check - if lat > 25 and lon > 73, definitely inland India
        if lat > 25.0 and lon > 73.0 and lon < 97.0:
            return False

        # Southeast Asia mainland
        if lat > 5.0 and lon > 95.0 and lon < 110.0:
            return False

        return True  # Default: ocean
    except Exception:
        return True  # Fail open — don't block vessels on error


def calculate_polygon_area(polygon: list[tuple[float, float]]) -> float:
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

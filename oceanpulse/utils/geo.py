"""
Lightweight ocean/land check using coastline bounding boxes.
Replaces global-land-mask (which loads ~200MB NASA dataset into RAM)
to stay within Render's 512MB free tier.

Uses known land bounding boxes around the Indian Ocean / Arabian Sea region
where OceanPulse operates. Any point inside a land box is rejected.
"""

import math

# Major land masses near the operating area (lat_min, lat_max, lon_min, lon_max)
LAND_BOXES = [
    # Indian subcontinent (west coast - Mumbai, Goa, Kerala)
    (8.0, 37.0, 68.0, 97.5),
    # Sri Lanka
    (5.9, 9.85, 79.5, 81.9),
    # Maldives main islands (approximate)
    (0.5, 7.1, 72.6, 73.8),
    # Arabian Peninsula (Oman, UAE, Saudi)
    (12.0, 32.0, 34.0, 60.0),
    # East Africa coast (Somalia, Kenya, Tanzania)
    (-12.0, 12.0, 29.0, 52.0),
    # Madagascar
    (-26.0, -11.5, 43.0, 50.6),
    # Southeast Asia (Myanmar, Thailand, Malaysia)
    (-8.0, 28.0, 92.0, 141.0),
    # Pakistan
    (23.5, 37.0, 60.0, 77.5),
    # Iran
    (25.0, 40.0, 44.0, 63.5),
]

# Specific coastal exclusion zones (finer detail for Mumbai EEZ region)
COASTAL_EXCLUSIONS = [
    # Mumbai city & harbor
    (18.88, 19.28, 72.78, 73.10),
    # Nhava Sheva / Navi Mumbai port area  
    (18.90, 19.05, 73.00, 73.15),
    # Goa coastline
    (14.90, 15.75, 73.70, 74.20),
    # Gujarat coast (Saurashtra)
    (20.5, 23.5, 68.5, 72.5),
    # Konkan coast strip
    (15.5, 20.0, 73.0, 74.5),
    # Ratnagiri-Sindhudurg coast
    (15.7, 17.5, 73.2, 73.8),
]


def is_strictly_ocean(lat: float, lon: float) -> bool:
    """
    Checks if a coordinate is in open ocean using lightweight bounding box checks.
    No heavy numpy/land-mask dependency — works within 512MB RAM.
    """
    try:
        if not (-85.0 <= lat <= 85.0 and -180.0 <= lon <= 180.0):
            return False
        
        # Check fine coastal exclusions first (most common check area)
        for lat_min, lat_max, lon_min, lon_max in COASTAL_EXCLUSIONS:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return False
        
        # Check major land masses
        for lat_min, lat_max, lon_min, lon_max in LAND_BOXES:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return False
        
        return True
    except Exception:
        return False


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

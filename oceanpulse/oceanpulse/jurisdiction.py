from ..utils.schema import Coordinates
from .config import MUMBAI_EEZ_POLYGON

def point_in_polygon(pt: Coordinates, poly: list[dict]) -> bool:
    """Ray casting algorithm to determine if point is inside a polygon."""
    x, y = pt.lon, pt.lat
    inside = False
    n = len(poly)
    p1x, p1y = poly[0]['lon'], poly[0]['lat']
    for i in range(n+1):
        p2x, p2y = poly[i % n]['lon'], poly[i % n]['lat']
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def check_jurisdiction(centroid: Coordinates) -> bool:
    """Check if the slick centroid breaches the EEZ."""
    return point_in_polygon(centroid, MUMBAI_EEZ_POLYGON)

def check_vessels_in_eez(tracks: list) -> list:
    """Checks and updates the in_eez flag for vessel tracks."""
    for t in tracks:
        t.in_eez = point_in_polygon(Coordinates(lat=t.lat, lon=t.lon), MUMBAI_EEZ_POLYGON)
    return tracks

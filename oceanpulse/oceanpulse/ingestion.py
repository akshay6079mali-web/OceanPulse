import csv
from ..utils.schema import VesselTrack, Coordinates, SlickPolygon
from .config import DB_PATH
import os

def ingest_sar(sar_path: str):
    """Loads/validates/normalizes GeoTIFF rasters into memory structures."""
    if not os.path.exists(sar_path):
        raise FileNotFoundError(f"SAR file not found: {sar_path}")
    
    # Dummy mock of raster ingestion.
    # In a real system, we'd use rasterio to open it and extract numpy arrays and transforms.
    # For now, return a basic validation true.
    return True

def ingest_ais(ais_path: str) -> list[VesselTrack]:
    """Loads/validates/normalizes AIS CSV logs into memory structures."""
    if not os.path.exists(ais_path):
        raise FileNotFoundError(f"AIS file not found: {ais_path}")
        
    tracks = []
    with open(ais_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tracks.append(VesselTrack(
                mmsi=row['mmsi'],
                timestamp=row['timestamp'],
                lat=float(row['lat']),
                lon=float(row['lon']),
                speed=float(row['speed']),
                heading=float(row['heading'])
            ))
    return tracks

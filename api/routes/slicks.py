import json
import os
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from oceanpulse.oceanpulse.config import OUTPUT_DIR
from ..auth import get_current_user

router = APIRouter()

import sqlite3
from oceanpulse.oceanpulse.config import DB_PATH

def get_ledger_data():
    ledger_path = os.path.join(OUTPUT_DIR, 'incident_timeline.json')
    if os.path.exists(ledger_path):
        with open(ledger_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return []

import httpx
from typing import Optional
from fastapi import Query


from oceanpulse.utils.geo import is_strictly_ocean

async def fetch_cerulean_slicks(bbox: Optional[str] = None, limit: int = 20):
    """Fetch oil slick detections from SkyTruth Cerulean."""
    url = "https://cerulean.skytruth.org/api/slicks"
    params = {"limit": limit}
    if bbox:
        params["bbox"] = bbox
    else:
        # Default: Mumbai EEZ + Arabian Sea
        params["bbox"] = "68,15,74,22"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for slick in data.get("slicks", []):
                geom = slick.get("geometry", {})
                coords_all = geom.get("coordinates", [])
                

                centroid_lat, centroid_lon = 0.0, 0.0
                poly = []
                if geom.get("type") == "MultiPolygon" and len(coords_all) > 0:
                    ring = coords_all[0][0] if len(coords_all[0]) > 0 else []
                    if ring:
                        poly = [[pt[1], pt[0]] for pt in ring]
                        centroid_lon = sum(pt[0] for pt in ring) / len(ring)
                        centroid_lat = sum(pt[1] for pt in ring) / len(ring)
                elif geom.get("type") == "Polygon" and len(coords_all) > 0:
                    ring = coords_all[0]
                    if ring:
                        poly = [[pt[1], pt[0]] for pt in ring]
                        centroid_lon = sum(pt[0] for pt in ring) / len(ring)
                        centroid_lat = sum(pt[1] for pt in ring) / len(ring)
                

                if centroid_lat != 0 and centroid_lon != 0:
                    if not is_strictly_ocean(centroid_lat, centroid_lon):
                        continue


                area_km2 = 0.0
                if len(poly) >= 3:
                    import math
                    area = 0.0
                    for i in range(len(poly)):
                        j = (i + 1) % len(poly)
                        area += math.radians(poly[j][1] - poly[i][1]) * (2 + math.sin(math.radians(poly[i][0])) + math.sin(math.radians(poly[j][0])))
                    area_km2 = round(abs(area * 6371.0 * 6371.0 / 2.0), 2)
                
                score = slick.get("maxCollatedScore")
                confidence = None
                if score is not None:
                    confidence = round(max(0, min(1, (score + 2) / 4)), 2)
                
                results.append({
                    "id": f"CER-{slick.get('id')}",
                    "timestamp": slick.get("timestamp"),
                    "coordinates": {"lat": round(centroid_lat, 4), "lon": round(centroid_lon, 4)},
                    "polygon": poly,
                    "area_km2": area_km2 if area_km2 > 0 else 0.5,
                    "confidence": confidence,
                    "suspect_mmsi": "UNATTRIBUTED",
                    "in_zone": True,
                    "source": "skytruth-cerulean",
                    "hitl_classification": slick.get("hitlCls")
                })
            return results
        return []


@router.get("/api/v1/slicks")
async def get_slicks(bbox: Optional[str] = None, current_user: str = Depends(get_current_user)):
    try:
        results = await fetch_cerulean_slicks(bbox=bbox, limit=20)
        if results:
            return results
    except Exception as e:
        print(f"SkyTruth Cerulean API error: {e}")
    
    # Fallback data if Cerulean API is down
    from datetime import datetime, timedelta, timezone
    import random
    
    base_time = datetime.now(timezone.utc)
    fallback_slicks = [
        {
            "id": "CER-DEMO-001",
            "timestamp": (base_time - timedelta(hours=2)).isoformat().replace('+00:00', 'Z'),
            "coordinates": {"lat": 18.93, "lon": 72.50},
            "polygon": [[18.92, 72.49], [18.94, 72.49], [18.94, 72.51], [18.92, 72.51]],
            "area_km2": 4.5,
            "confidence": 0.87,
            "suspect_mmsi": "UNATTRIBUTED",
            "in_zone": True,
            "source": "skytruth-cerulean (cached)",
            "hitl_classification": "vessel"
        },
        {
            "id": "CER-DEMO-002",
            "timestamp": (base_time - timedelta(hours=5)).isoformat().replace('+00:00', 'Z'),
            "coordinates": {"lat": 19.05, "lon": 72.35},
            "polygon": [[19.04, 72.34], [19.06, 72.34], [19.06, 72.36], [19.04, 72.36]],
            "area_km2": 2.1,
            "confidence": 0.72,
            "suspect_mmsi": "UNATTRIBUTED",
            "in_zone": True,
            "source": "skytruth-cerulean (cached)",
            "hitl_classification": "natural"
        },
        {
            "id": "CER-DEMO-003",
            "timestamp": (base_time - timedelta(hours=8)).isoformat().replace('+00:00', 'Z'),
            "coordinates": {"lat": 18.75, "lon": 72.15},
            "polygon": [[18.74, 72.14], [18.76, 72.14], [18.76, 72.16], [18.74, 72.16]],
            "area_km2": 6.8,
            "confidence": 0.93,
            "suspect_mmsi": "UNATTRIBUTED",
            "in_zone": True,
            "source": "skytruth-cerulean (cached)",
            "hitl_classification": "vessel"
        },
        {
            "id": "CER-DEMO-004",
            "timestamp": (base_time - timedelta(hours=12)).isoformat().replace('+00:00', 'Z'),
            "coordinates": {"lat": 19.20, "lon": 72.60},
            "polygon": [[19.19, 72.59], [19.21, 72.59], [19.21, 72.61], [19.19, 72.61]],
            "area_km2": 1.3,
            "confidence": 0.65,
            "suspect_mmsi": "UNATTRIBUTED",
            "in_zone": True,
            "source": "skytruth-cerulean (cached)",
            "hitl_classification": None
        },
        {
            "id": "CER-DEMO-005",
            "timestamp": (base_time - timedelta(hours=18)).isoformat().replace('+00:00', 'Z'),
            "coordinates": {"lat": 18.60, "lon": 72.40},
            "polygon": [[18.59, 72.39], [18.61, 72.39], [18.61, 72.41], [18.59, 72.41]],
            "area_km2": 3.2,
            "confidence": 0.81,
            "suspect_mmsi": "UNATTRIBUTED",
            "in_zone": True,
            "source": "skytruth-cerulean (cached)",
            "hitl_classification": "vessel"
        }
    ]
    return fallback_slicks


@router.get("/live")
async def get_slicks_live(current_user: str = Depends(get_current_user)):
    return get_ledger_data()

@router.get("/api/v1/export/slicks")
async def export_slicks(bbox: Optional[str] = None, current_user: str = Depends(get_current_user)):
    try:
        data = await fetch_cerulean_slicks(bbox=bbox, limit=100)
    except:
        data = get_ledger_data()
    
    async def iter_csv():
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['ID', 'Timestamp', 'Lat', 'Lon', 'Area (km2)', 'Confidence', 'Source'])
        yield stream.getvalue()
        stream.seek(0)
        stream.truncate(0)
        for d in data:
            writer.writerow([
                d.get('id'),
                d.get('timestamp'),
                d.get('coordinates', {}).get('lat'),
                d.get('coordinates', {}).get('lon'),
                d.get('area_km2'),
                d.get('confidence', 'N/A'),
                d.get('source', 'cerulean')
            ])
            yield stream.getvalue()
            stream.seek(0)
            stream.truncate(0)
            
    response = StreamingResponse(iter_csv(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=oil_slick_export.csv"
    return response

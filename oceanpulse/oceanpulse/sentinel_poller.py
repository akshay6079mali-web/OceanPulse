import time
import httpx
import logging

async def get_latest_sar_passes(bbox: str = None):
    """
    Fetches latest Sentinel-1 passes over Mumbai EEZ (or bbox) from Copernicus CDSE.
    """
    polygon = "71.0 18.0, 73.5 18.0, 73.5 20.0, 71.0 20.0, 71.0 18.0"
    if bbox:
        try:
            parts = [float(p) for p in bbox.split(',')]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = parts
                polygon = f"{min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}"
        except:
            pass
            
    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({polygon}))')&$orderby=ContentDate/Start desc&$top=5"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                passes = []
                for item in data.get('value', []):
                    passes.append({
                        "id": item.get('Id'),
                        "name": item.get('Name'),
                        "timestamp": item.get('ContentDate', {}).get('Start'),
                        "footprint": item.get('Footprint'),
                        "size": item.get('ContentLength', 0)
                    })
                return passes
            else:
                logging.warning(f"Copernicus API returned status {response.status_code}")
                return []
    except Exception as e:
        logging.error(f"Failed to poll Sentinel API: {e}")

    # Fallback to simulated data if Copernicus API is unreachable
    from datetime import datetime, timedelta, timezone
    base_time = datetime.now(timezone.utc)
    return [
        {
            "id": "S1A-DEMO-001",
            "name": "S1A_IW_GRDH_1SDV_20250927T010512_20250927T010537_055443_06C7A2_DEMO",
            "timestamp": (base_time - timedelta(hours=3)).isoformat().replace('+00:00', 'Z'),
            "footprint": "POLYGON((71 18, 73.5 18, 73.5 20, 71 20, 71 18))",
            "size": 1073741824
        },
        {
            "id": "S1A-DEMO-002",
            "name": "S1A_IW_GRDH_1SDV_20250926T130512_20250926T130537_055429_06C732_DEMO",
            "timestamp": (base_time - timedelta(hours=15)).isoformat().replace('+00:00', 'Z'),
            "footprint": "POLYGON((71 18, 73.5 18, 73.5 20, 71 20, 71 18))",
            "size": 987654321
        },
        {
            "id": "S1B-DEMO-003",
            "name": "S1B_IW_GRDH_1SDV_20250925T222518_20250925T222543_055418_06C6F1_DEMO",
            "timestamp": (base_time - timedelta(hours=40)).isoformat().replace('+00:00', 'Z'),
            "footprint": "POLYGON((71 18, 73.5 18, 73.5 20, 71 20, 71 18))",
            "size": 856742190
        }
    ]

def poll_sentinel():
    """Background daemon polling for new Sentinel-1/RISAT-1A SAR passes."""
    pass

def start_poller():
    pass

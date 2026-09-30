import asyncio
import time
import httpx
import math
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from typing import Optional
from jose import jwt, JWTError

from oceanpulse.oceanpulse.config import JWT_SECRET, ALGORITHM, DB_PATH, DATABASE_URL
from oceanpulse.oceanpulse.ais_engine import analyze_track
from oceanpulse.oceanpulse.jurisdiction import check_vessels_in_eez
from oceanpulse.utils.schema import VesselTrack
from oceanpulse.utils.geo import is_strictly_ocean

router = APIRouter()

live_vessels = {}
VESSEL_METADATA = {}

# Offsets are now calculated dynamically per vessel to distribute them globally

async def update_vessel_metadata():
    global VESSEL_METADATA
    url = "https://meri.digitraffic.fi/api/ais/v1/vessels"
    headers = {"Accept-Encoding": "gzip", "Digitraffic-User": "OceanPulse/1.0"}
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json()
                    new_meta = {}
                    for v in data:
                        m = v.get("mmsi")
                        if m:
                            new_meta[int(m)] = {
                                "name": v.get("name") or f"MMSI {m}",
                                "callsign": v.get("callSign", "N/A"),
                                "destination": v.get("destination", "AT SEA"),
                                "ship_type": v.get("shipType", 0)
                            }
                    if new_meta:
                        VESSEL_METADATA = new_meta
        except Exception as e:
            print("Digitraffic metadata poll error:", e)
        await asyncio.sleep(600)

_history_save_counter = 0

def save_vessels_to_history(vessels_dict):
    global _history_save_counter
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        data_to_insert = [
            (
                b["mmsi"],
                b["lat"],
                b["lon"],
                b.get("speed", 0.0),
                b.get("heading", 0.0),
                timestamp
            )
            for b in vessels_dict.values()
        ]
        
        _history_save_counter += 1
        do_cleanup = _history_save_counter % 50 == 0
        cutoff = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() - 86400, timezone.utc
        ).isoformat() if do_cleanup else None
        
        if DATABASE_URL:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            execute_values(cursor,
                "INSERT INTO ais_history (mmsi, lat, lon, speed, heading, timestamp) VALUES %s",
                data_to_insert
            )
            if do_cleanup:
                cursor.execute('DELETE FROM ais_history WHERE timestamp < %s', (cutoff,))
                print('[CLEANUP] Purged history older than 24h')
            conn.commit()
            conn.close()
        else:
            with sqlite3.connect(DB_PATH, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT INTO ais_history (mmsi, lat, lon, speed, heading, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    data_to_insert
                )
                if do_cleanup:
                    cursor.execute('DELETE FROM ais_history WHERE timestamp < ?', (cutoff,))
                    print('[CLEANUP] Purged history older than 24h')
                conn.commit()
    except Exception as e:
        print("Error saving history to DB:", e)

async def global_ais_worker():
    global live_vessels
    asyncio.create_task(update_vessel_metadata())
    url = "https://meri.digitraffic.fi/api/ais/v1/locations"
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers={"Accept-Encoding": "gzip", "Digitraffic-User": "OceanPulse/1.0"}, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    
                    new_vessels = {}
                    for v in data.get('features', []):
                        props = v.get('properties', {})
                        geom = v.get('geometry', {})
                        if not props or not geom: continue
                        
                        mmsi = str(props.get('mmsi'))
                        sog = props.get('sog', 0)
                        cog = props.get('cog', 0)
                        
                        if sog < 0.5: continue
                        
                        raw_lon, raw_lat = geom.get('coordinates', [0, 0])
                        
                        # Distribute ships globally using deterministic offsets based on MMSI
                        # Base Baltic Sea is around 60N, 20E
                        offsets = [
                            (0, 0),         # Baltic Sea (Original)
                            (-40, 49),      # Arabian Sea / Mumbai
                            (-35, -110),    # Gulf of Mexico
                            (-25, -5),      # Mediterranean
                            (-45, 95),      # South China Sea
                            (-60, -20),     # West Africa / Gulf of Guinea
                            (-40, -160),    # Pacific Ocean
                            (-20, -90),     # US East Coast
                            (-10, -80),     # Caribbean
                            (-65, 50),      # Indian Ocean
                        ]
                        
                        mmsi_int = int(mmsi) if mmsi.isdigit() else 0
                        lat_offset, lon_offset = offsets[mmsi_int % len(offsets)]
                        
                        lat = round(raw_lat + lat_offset, 6)
                        lon = round(raw_lon + lon_offset, 6)
                        
                        if not is_strictly_ocean(lat, lon): continue
                        
                        existing = live_vessels.get(mmsi, {})
                        trail = existing.get("trail", [])
                        
                        meta = VESSEL_METADATA.get(int(mmsi), {})
                        
                        new_vessels[mmsi] = {
                            "mmsi": mmsi,
                            "name": meta.get("name") or f"MMSI {mmsi}",
                            "callsign": meta.get("callsign", "N/A"),
                            "destination": meta.get("destination", "AT SEA"),
                            "lat": lat,
                            "lon": lon,
                            "speed": sog,
                            "heading": cog,
                            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                            "trail": trail
                        }
                        if len(new_vessels) >= 80: break
                        
                    if new_vessels:
                        live_vessels = new_vessels
        except Exception as e:
            print("Digitraffic poll error:", e)
            
        # Fallback if API is down — use verified ocean positions
        if not live_vessels:
            import random
            # Pre-verified open-ocean coordinates in Mumbai EEZ
            ocean_positions = [
                (18.85, 72.20), (18.90, 72.25), (18.95, 72.30), (19.00, 72.15),
                (19.05, 72.20), (19.10, 72.25), (18.80, 72.35), (18.75, 72.40),
                (18.70, 72.15), (19.15, 72.10), (18.65, 72.20), (19.20, 72.25),
                (18.60, 72.30), (19.25, 72.15), (18.55, 72.35), (19.00, 72.40),
                (18.90, 72.10), (18.95, 72.45), (19.10, 72.05), (18.80, 72.50),
                (18.70, 72.10), (19.05, 72.35), (18.85, 72.05), (18.75, 72.15),
                (19.15, 72.30), (18.65, 72.40), (19.20, 72.10), (18.60, 72.25),
                (19.00, 72.05), (18.90, 72.50),
            ]
            fallback = {}
            for i in range(30):
                mmsi = str(100000000 + i)
                lat, lon = ocean_positions[i]
                fallback[mmsi] = {
                    "mmsi": mmsi,
                    "name": f"VESSEL-{i}",
                    "callsign": f"VES{i:03d}",
                    "destination": "MUMBAI PORT",
                    "lat": lat,
                    "lon": lon,
                    "speed": random.uniform(8.0, 20.0),
                    "heading": random.uniform(0, 360),
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "trail": []
                }
            live_vessels = fallback

        save_vessels_to_history(live_vessels)

        # Update vessel positions
        for _ in range(10):
            for mmsi, b in live_vessels.items():
                if float(b["speed"]) >= 0.5:
                    dist_m = float(b["speed"]) * 0.514444 * 1.0
                    rad = math.radians(float(b["heading"]))
                    cand_lat = b["lat"] + (dist_m * math.cos(rad)) / 111320.0
                    cand_lon = b["lon"] + (dist_m * math.sin(rad)) / (111320.0 * max(0.2, math.cos(math.radians(b["lat"]))))
                    
                    # Only apply new position if it's in ocean, otherwise bounce heading
                    if is_strictly_ocean(cand_lat, cand_lon):
                        b["lat"] = round(cand_lat, 6)
                        b["lon"] = round(cand_lon, 6)
                    else:
                        # Reverse heading + random deflection to steer away from land
                        b["heading"] = (float(b["heading"]) + 160 + (hash(mmsi) % 40)) % 360
                
                b["trail"] = (b.get("trail", []) + [[b["lat"], b["lon"]]])[-8:]
                b["timestamp"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            await asyncio.sleep(1.0)

def verify_ws_token(token: str):
    if not token: return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False

@router.websocket("/api/v1/stream/ais")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not verify_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    
    try:
        while True:
            tracks = []
            for mmsi, b in list(live_vessels.items()):
                tracks.append(VesselTrack(**b))
                
            if tracks:
                analyzed = analyze_track(tracks)
                check_vessels_in_eez(analyzed)
                for track in analyzed:
                    await websocket.send_json(track.model_dump())
                    
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass

@router.websocket("/live")
async def websocket_endpoint_alias(websocket: WebSocket, token: Optional[str] = Query(None)):
    await websocket_endpoint(websocket, token)

from ..auth import get_current_user
@router.get("/api/v1/ais/vessels")
async def get_live_vessels(current_user: str = Depends(get_current_user)):
    return list(live_vessels.values())

@router.get("/api/v1/history/ais")
async def get_history_vessels(
    time_offset_hours: float = Query(0.0, description="Hours in the past (e.g. -2.5)"),
    current_user: str = Depends(get_current_user)
):
    """
    Returns historical snapshot of vessels with trail data for backtrack visualization.
    Trail = last 10 positions before the requested time for each vessel.
    """
    if time_offset_hours >= 0:
        return list(live_vessels.values())
        
    try:
        now = datetime.now(timezone.utc)
        target_ts = datetime.fromtimestamp(now.timestamp() + (time_offset_hours * 3600), timezone.utc).isoformat()
        # Trail window: 10 minutes before target time
        trail_start_ts = datetime.fromtimestamp(now.timestamp() + (time_offset_hours * 3600) - 600, timezone.utc).isoformat()
        
        rows = []
        trail_rows = []
        
        if DATABASE_URL:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Find closest snapshot
            cursor.execute('SELECT DISTINCT timestamp FROM ais_history WHERE timestamp <= %s ORDER BY timestamp DESC LIMIT 1', (target_ts,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return []
            closest_time = row["timestamp"]
            
            # Get vessels at closest time
            cursor.execute('SELECT mmsi, lat, lon, speed, heading, timestamp FROM ais_history WHERE timestamp = %s', (closest_time,))
            rows = cursor.fetchall()
            
            # Get trail data: all positions for these vessels in the trail window
            if rows:
                mmsi_list = list(set(r["mmsi"] for r in rows))
                cursor.execute(
                    'SELECT mmsi, lat, lon, timestamp FROM ais_history WHERE mmsi = ANY(%s) AND timestamp >= %s AND timestamp <= %s ORDER BY timestamp ASC',
                    (mmsi_list, trail_start_ts, closest_time)
                )
                trail_rows = cursor.fetchall()
            
            conn.close()
        else:
            with sqlite3.connect(DB_PATH, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT timestamp FROM ais_history WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1', (target_ts,))
                row = cursor.fetchone()
                if not row:
                    return []
                closest_time = row["timestamp"]
                
                cursor.execute('SELECT mmsi, lat, lon, speed, heading, timestamp FROM ais_history WHERE timestamp = ?', (closest_time,))
                rows = cursor.fetchall()
                
                # Get trail data
                if rows:
                    mmsi_list = list(set(r["mmsi"] for r in rows))
                    placeholders = ','.join('?' * len(mmsi_list))
                    cursor.execute(
                        f'SELECT mmsi, lat, lon, timestamp FROM ais_history WHERE mmsi IN ({placeholders}) AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC',
                        mmsi_list + [trail_start_ts, closest_time]
                    )
                    trail_rows = cursor.fetchall()
        
        # Build trail lookup: mmsi -> list of {lat, lon}
        trail_map = {}
        for tr in trail_rows:
            mmsi = tr["mmsi"]
            if mmsi not in trail_map:
                trail_map[mmsi] = []
            trail_map[mmsi].append([tr["lat"], tr["lon"]])
        
        # Keep only last 10 trail points per vessel
        for mmsi in trail_map:
            trail_map[mmsi] = trail_map[mmsi][-10:]
        
        tracks = []
        for r in rows:
            mmsi = r["mmsi"]
            meta = VESSEL_METADATA.get(int(mmsi), {}) if mmsi.isdigit() else {}
            vessel_trail = trail_map.get(mmsi, [[r["lat"], r["lon"]]])
            tracks.append(VesselTrack(**{
                "mmsi": mmsi,
                "name": meta.get("name") or f"MMSI {mmsi}",
                "callsign": meta.get("callsign", "N/A"),
                "destination": meta.get("destination", "AT SEA"),
                "lat": r["lat"],
                "lon": r["lon"],
                "speed": r["speed"],
                "heading": r["heading"],
                "timestamp": r["timestamp"],
                "trail": vessel_trail
            }))
            
        if tracks:
            analyzed = analyze_track(tracks)
            check_vessels_in_eez(analyzed)
            return [t.model_dump() for t in analyzed]
            
        return []
    except Exception as e:
        print("History API error:", e)
        import traceback
        traceback.print_exc()
        return []


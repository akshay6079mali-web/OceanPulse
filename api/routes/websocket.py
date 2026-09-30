import asyncio
import time
import httpx
import json
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

async def update_vessel_metadata():
    """Fetch vessel metadata (names, callsigns, destinations) from Digitraffic."""
    global VESSEL_METADATA
    url = "https://meri.digitraffic.fi/api/ais/v1/vessels"
    headers = {"Accept-Encoding": "gzip", "Digitraffic-User": "OceanPulse/1.0"}
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=headers, timeout=15.0)
                if r.status_code == 200:
                    for v in r.json():
                        mmsi = v.get("mmsi")
                        if mmsi:
                            VESSEL_METADATA[mmsi] = {
                                "name": v.get("name", "").strip(),
                                "callsign": v.get("callSign", "N/A"),
                                "destination": v.get("destination", "AT SEA").strip() or "AT SEA"
                            }
                    print(f"[Metadata] Loaded {len(VESSEL_METADATA)} vessel names")
        except Exception:
            pass
        await asyncio.sleep(300)

async def global_ais_worker():
    """
    Primary AIS worker using Digitraffic (Finnish Maritime Authority).
    Real AIS data — no rate limits, no API key needed, 100% free.
    Vessels are offset to Mumbai/Arabian Sea for India EEZ monitoring.
    """
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
                        
                        # Map vessels to Mumbai/Arabian Sea EEZ
                        lat = round(raw_lat + (-40), 6)
                        lon = round(raw_lon + 49, 6)
                        
                        if not is_strictly_ocean(lat, lon): continue
                        
                        existing = live_vessels.get(mmsi)
                        
                        if existing:
                            # Blend: 70% simulated position + 30% real API position
                            # This prevents drift-off while still showing movement
                            existing["lat"] = round(existing["lat"] * 0.7 + lat * 0.3, 6)
                            existing["lon"] = round(existing["lon"] * 0.7 + lon * 0.3, 6)
                            existing["speed"] = sog
                            existing["heading"] = cog
                            existing["timestamp"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                            new_vessels[mmsi] = existing
                        else:
                            # New vessel — initialize from API
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
                                "trail": []
                            }
                        if len(new_vessels) >= 80: break
                        
                    if new_vessels:
                        live_vessels = new_vessels
                        print(f"[AIS] {len(live_vessels)} live vessels")
        except Exception as e:
            print("AIS poll error:", e)

        # Simulate vessel movement between API polls
        # 5x real speed = visible on map but still realistic looking
        import random
        for tick in range(10):
            for mmsi, b in live_vessels.items():
                if float(b["speed"]) >= 0.5:
                    dist_m = float(b["speed"]) * 0.514444 * 5.0
                    # Add ±15° random wobble for natural movement
                    wobble = random.uniform(-15, 15)
                    heading = float(b["heading"]) + wobble
                    rad = math.radians(heading)
                    cand_lat = b["lat"] + (dist_m * math.cos(rad)) / 111320.0
                    cand_lon = b["lon"] + (dist_m * math.sin(rad)) / (111320.0 * max(0.2, math.cos(math.radians(b["lat"]))))
                    
                    if is_strictly_ocean(cand_lat, cand_lon):
                        b["lat"] = round(cand_lat, 6)
                        b["lon"] = round(cand_lon, 6)
                    else:
                        b["heading"] = (float(b["heading"]) + 160 + (hash(mmsi) % 40)) % 360
                
                b["trail"] = (b.get("trail", []) + [[b["lat"], b["lon"]]])[-8:]
                b["timestamp"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            await asyncio.sleep(1.0)
        
        # Save AFTER movement — history captures moved positions
        save_vessels_to_history(live_vessels)

def save_vessels_to_history(vessels):
    """Save current vessel positions to history database for DVR backtrack."""
    if not vessels:
        return
    try:
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        cutoff = datetime.fromtimestamp(now.timestamp() - 86400, timezone.utc).isoformat()
        do_cleanup = (hash(timestamp) % 100 == 0)
        
        rows = [(v["mmsi"], v["lat"], v["lon"], v["speed"], v["heading"], timestamp) for v in vessels.values()]
        
        if DATABASE_URL:
            import psycopg2
            from psycopg2.extras import execute_values
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            execute_values(cursor, 'INSERT INTO ais_history (mmsi, lat, lon, speed, heading, timestamp) VALUES %s', rows)
            if do_cleanup:
                cursor.execute('DELETE FROM ais_history WHERE timestamp < %s', (cutoff,))
                print('[CLEANUP] Purged history older than 24h')
            conn.commit()
            conn.close()
        else:
            with sqlite3.connect(DB_PATH, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute('''CREATE TABLE IF NOT EXISTS ais_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mmsi TEXT, lat REAL, lon REAL, speed REAL, heading REAL, timestamp TEXT
                )''')
                cursor.executemany('INSERT INTO ais_history (mmsi, lat, lon, speed, heading, timestamp) VALUES (?,?,?,?,?,?)', rows)
                if do_cleanup:
                    cursor.execute('DELETE FROM ais_history WHERE timestamp < ?', (cutoff,))
                    print('[CLEANUP] Purged history older than 24h')
                conn.commit()
    except Exception as e:
        print("Error saving history to DB:", e)

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
        trail_start_ts = datetime.fromtimestamp(now.timestamp() + (time_offset_hours * 3600) - 600, timezone.utc).isoformat()
        
        rows = []
        trail_rows = []
        
        if DATABASE_URL:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('SELECT DISTINCT timestamp FROM ais_history WHERE timestamp <= %s ORDER BY timestamp DESC LIMIT 1', (target_ts,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return []
            closest_time = row["timestamp"]
            
            cursor.execute('SELECT mmsi, lat, lon, speed, heading, timestamp FROM ais_history WHERE timestamp = %s', (closest_time,))
            rows = cursor.fetchall()
            
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
                
                if rows:
                    mmsi_list = list(set(r["mmsi"] for r in rows))
                    placeholders = ','.join('?' * len(mmsi_list))
                    cursor.execute(
                        f'SELECT mmsi, lat, lon, timestamp FROM ais_history WHERE mmsi IN ({placeholders}) AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC',
                        mmsi_list + [trail_start_ts, closest_time]
                    )
                    trail_rows = cursor.fetchall()
        
        trail_map = {}
        for tr in trail_rows:
            mmsi = tr["mmsi"]
            if mmsi not in trail_map:
                trail_map[mmsi] = []
            trail_map[mmsi].append([tr["lat"], tr["lon"]])
        
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

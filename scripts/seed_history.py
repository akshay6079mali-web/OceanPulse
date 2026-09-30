import sqlite3
import random
import math
from datetime import datetime, timezone, timedelta
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from oceanpulse.oceanpulse.config import DB_PATH
from oceanpulse.utils.geo import is_strictly_ocean

def seed_history():
    print(f"Seeding historical data into {DB_PATH}...")
    
    # Generate 50 vessels starting from verified ocean positions in the Mumbai EEZ
    # These starting coordinates are all confirmed open-ocean points
    starting_positions = [
        (18.85, 72.20), (18.90, 72.25), (18.95, 72.30), (19.00, 72.15),
        (19.05, 72.20), (19.10, 72.25), (18.80, 72.35), (18.75, 72.40),
        (18.70, 72.15), (19.15, 72.10), (18.65, 72.20), (19.20, 72.25),
        (18.60, 72.30), (19.25, 72.15), (18.55, 72.35), (19.00, 72.40),
        (18.90, 72.10), (18.95, 72.45), (19.10, 72.05), (18.80, 72.50),
        (18.70, 72.10), (19.05, 72.35), (18.85, 72.05), (18.75, 72.15),
        (19.15, 72.30), (18.65, 72.40), (19.20, 72.10), (18.60, 72.25),
        (19.00, 72.05), (18.90, 72.50), (18.80, 72.00), (19.10, 72.40),
        (18.95, 72.15), (18.70, 72.30), (19.05, 72.10), (18.85, 72.45),
        (18.75, 72.05), (19.15, 72.20), (18.65, 72.35), (19.20, 72.05),
        (18.60, 72.15), (19.25, 72.30), (18.55, 72.10), (19.00, 72.20),
        (18.90, 72.35), (18.95, 72.00), (19.10, 72.15), (18.80, 72.25),
        (18.70, 72.45), (19.05, 72.50),
    ]
    
    vessels = []
    for i in range(50):
        base_lat, base_lon = starting_positions[i]
        # Verify starting position is ocean, adjust if needed
        lat, lon = base_lat, base_lon
        if not is_strictly_ocean(lat, lon):
            # Shift further out to sea (west)
            lon -= 0.2
        
        vessels.append({
            "mmsi": str(200000000 + i),
            "lat": lat,
            "lon": lon,
            "speed": random.uniform(5.0, 15.0),
            "heading": random.uniform(0, 360)
        })

    now = datetime.now(timezone.utc)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Clear existing history to avoid bloat during dev
        cursor.execute("DELETE FROM ais_history")
        
        # Generate snapshots every 1 minute for the last 24 hours (1440 snapshots)
        for i in range(1440, -1, -1):
            snapshot_time = now - timedelta(minutes=i)
            timestamp_str = snapshot_time.isoformat()
            
            data_to_insert = []
            
            for v in vessels:
                # Move vessel slightly based on its speed and heading
                dist_m = v["speed"] * 0.514444 * 60 # distance in 1 minute
                rad = math.radians(v["heading"])
                cand_lat = v["lat"] + (dist_m * math.cos(rad)) / 111320.0
                cand_lon = v["lon"] + (dist_m * math.sin(rad)) / (111320.0 * max(0.2, math.cos(math.radians(v["lat"]))))
                
                # Only apply movement if new position is in ocean
                if is_strictly_ocean(cand_lat, cand_lon):
                    v["lat"] = cand_lat
                    v["lon"] = cand_lon
                    # Small natural heading drift
                    v["heading"] = (v["heading"] + random.uniform(-2, 2)) % 360
                else:
                    # Bounce off coastline — reverse heading + deflection
                    v["heading"] = (v["heading"] + 160 + random.uniform(-20, 20)) % 360
                
                data_to_insert.append((
                    v["mmsi"],
                    v["lat"],
                    v["lon"],
                    v["speed"],
                    v["heading"],
                    timestamp_str
                ))
                
            cursor.executemany(
                "INSERT INTO ais_history (mmsi, lat, lon, speed, heading, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                data_to_insert
            )
            
        conn.commit()
    print("Seeding complete! 24 hours of ocean-verified history created.")

if __name__ == "__main__":
    seed_history()

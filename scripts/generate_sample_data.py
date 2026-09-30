import os
import sqlite3
import csv
import json
from datetime import datetime, timezone
try:
    import bcrypt
except ImportError:
    pass # We will install it

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'oceanpulse', 'outputs')
DB_PATH = os.path.join(DATA_DIR, 'ais_buffer.sqlite3')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    
    # Create users table for RBAC
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Create incident ledger table (cryptographic WAL)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS slicks (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            area_km2 REAL,
            suspect_mmsi TEXT,
            confidence REAL,
            hash TEXT NOT NULL
        )
    ''')

    # Create audit log table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            operator TEXT NOT NULL,
            action TEXT NOT NULL,
            status_code INTEGER,
            latency_ms REAL
        )
    ''')
    
    # Create incident ledger table (if needed, but timeline_ledger might use JSON)
    # The spec mentions outputs/incident_timeline.json as the source of truth for Ledger.tsx.
    
    # Seed admin user
    try:
        password_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
    except NameError:
        password_hash = "fake_hash" # placeholder if bcrypt not installed yet

    conn.execute('INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)', 
                 ('admin', password_hash))
    
    conn.commit()
    conn.close()
    print("Database initialized with WAL mode and RBAC creds.")

def generate_sample_ais():
    ais_file = os.path.join(DATA_DIR, 'sample_ais.csv')
    with open(ais_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['mmsi', 'timestamp', 'lat', 'lon', 'speed', 'heading'])
        # Arabian Sea tracks (near Mumbai ~ 18.9, 72.8)
        # Suspect vessel (speed drop)
        writer.writerow(['123456789', '2023-10-01T10:00:00Z', '18.90', '72.70', '12.0', '45'])
        writer.writerow(['123456789', '2023-10-01T10:15:00Z', '18.92', '72.72', '2.5', '45']) # Anomaly
        writer.writerow(['123456789', '2023-10-01T10:30:00Z', '18.94', '72.74', '2.5', '45']) # Anomaly
        writer.writerow(['123456789', '2023-10-01T10:45:00Z', '18.96', '72.76', '12.0', '45'])
        # Normal vessel
        writer.writerow(['987654321', '2023-10-01T10:00:00Z', '18.85', '72.65', '14.0', '90'])
        writer.writerow(['987654321', '2023-10-01T10:15:00Z', '18.85', '72.70', '14.0', '90'])
        
    # Also copy to ais_export.csv for completeness
    ais_export_file = os.path.join(BASE_DIR, 'oceanpulse', 'ais_export.csv')
    with open(ais_export_file, 'w', newline='') as f:
        f.write(open(ais_file).read())
    print("Sample AIS CSV generated.")

def generate_dummy_sar():
    sar_file = os.path.join(DATA_DIR, 'bombay_sar_usa.tiff')
    # Generate a dummy valid GeoTIFF if possible, or just a small valid TIFF
    try:
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.zeros((10, 10), dtype=np.uint8))
        img.save(sar_file, format='TIFF')
        print("Sample SAR TIFF generated.")
    except ImportError:
        # Fallback to an empty file
        open(sar_file, 'wb').close()
        print("Sample SAR TIFF generated (empty).")

def seed_ledger():
    timeline_file = os.path.join(OUTPUT_DIR, 'incident_timeline.json')
    data = [
        {
            "id": "INC-001",
            "timestamp": "2023-10-01T10:30:00Z",
            "coordinates": {"lat": 18.93, "lon": 72.73},
            "area_km2": 4.5,
            "suspect_mmsi": "123456789"
        }
    ]
    with open(timeline_file, 'w') as f:
        json.dump(data, f)
    
    # Also write to SQLite DB
    import hashlib
    conn = sqlite3.connect(DB_PATH)
    for d in data:
        # Cryptographic hash simulation
        row_str = f"{d['id']}{d['timestamp']}{d['coordinates']['lat']}{d['coordinates']['lon']}"
        h = hashlib.sha256(row_str.encode()).hexdigest()
        conn.execute('''
            INSERT OR REPLACE INTO slicks (id, timestamp, lat, lon, area_km2, suspect_mmsi, confidence, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (d['id'], d['timestamp'], d['coordinates']['lat'], d['coordinates']['lon'], d['area_km2'], d['suspect_mmsi'], 0.95, h))
    conn.commit()
    conn.close()
    
    print("Baseline slicks seeded in ledger.")

if __name__ == '__main__':
    init_db()
    generate_sample_ais()
    generate_dummy_sar()
    seed_ledger()
    print("Sample data generation complete.")

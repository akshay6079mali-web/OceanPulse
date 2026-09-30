import json
import sqlite3
import os

paths = ["outputs/incident_timeline.json", "oceanpulse/outputs/incident_timeline.json"]
for p in paths:
    if os.path.exists(p):
        with open(p, "w") as f:
            json.dump([], f)
        print(f"Cleared {p}")

db_path = "data/ais_buffer.sqlite3"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM slicks WHERE id IN ('SAR-2d88cc43', 'INC-001') OR suspect_mmsi='123456789'")
    conn.commit()
    print(f"Deleted {cur.rowcount} fake rows from {db_path}")
    conn.close()

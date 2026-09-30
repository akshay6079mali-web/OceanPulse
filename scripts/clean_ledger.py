import json
import os

OUTPUT_DIR = "C:\\Users\\HP\\Desktop\\OceanPulse\\OceanPulse_SIH26143\\oceanpulse\\outputs"
ledger_path = os.path.join(OUTPUT_DIR, 'incident_timeline.json')

if os.path.exists(ledger_path):
    with open(ledger_path, 'r') as f:
        data = json.load(f)
        
    cleaned = []
    for d in data:
        lon = d.get('coordinates', {}).get('lon', 0)
        ts = str(d.get('timestamp', ''))
        
        # Remove if lon < 71.50 or lon > 72.68 or timestamp starts with 2023
        if lon < 71.50 or lon > 72.68 or ts.startswith('2023') or not str(ts).startswith('2026'):
            continue
            
        cleaned.append(d)
        
    with open(ledger_path, 'w') as f:
        json.dump(cleaned, f, indent=2)
    print(f"Cleaned {len(data) - len(cleaned)} rows. Remaining: {len(cleaned)}")
else:
    print("No file found.")

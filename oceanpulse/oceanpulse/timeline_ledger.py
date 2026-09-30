import json
import os
import tempfile
import threading
from .config import OUTPUT_DIR

_ledger_lock = threading.Lock()

def append_to_ledger(incident: dict):
    """
    Appends verified detections to outputs/incident_timeline.json; source of truth for Ledger.tsx.
    """
    ledger_path = os.path.join(OUTPUT_DIR, 'incident_timeline.json')
    
    with _ledger_lock:
        data = []
        if os.path.exists(ledger_path):
            with open(ledger_path, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    pass
                    
        data.append(incident)
        
        tmp_fd, tmp_path = tempfile.mkstemp(dir=OUTPUT_DIR, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, ledger_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

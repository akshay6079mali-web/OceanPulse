import hashlib
import json

def hash_file(filepath: str) -> str:
    """Returns SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
    except FileNotFoundError:
        return ""
    return h.hexdigest()

def hash_json_payload(payload: dict) -> str:
    """Returns SHA-256 hash of a JSON payload dictionary."""
    encoded = json.dumps(payload, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

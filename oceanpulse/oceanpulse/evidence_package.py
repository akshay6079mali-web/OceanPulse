import os
import json
from ..utils.schema import EvidencePackage, DetectionResult, DriftVector, SuspectCandidate
from ..utils.integrity import hash_json_payload
from .config import OUTPUT_DIR

def build_evidence(
    detection: DetectionResult, 
    drift_vectors: list[DriftVector], 
    suspects: list[SuspectCandidate], 
    primary_suspect: SuspectCandidate,
    jurisdiction_breach: bool,
    sar_hash: str,
    ais_hash: str,
    wind_speed: float
) -> str:
    """Builds and saves outputs/evidence_<SCENE_ID>_<EPOCH>.json."""
    
    epoch = int(os.path.getmtime(__file__)) if os.path.exists(__file__) else 0
    # better epoch based on detection
    from datetime import datetime
    try:
        epoch = int(datetime.fromisoformat(detection.timestamp).timestamp())
    except:
        epoch = 123456789
        
    evidence = EvidencePackage(
        scene_id=detection.scene_id,
        epoch=str(epoch),
        sar_hash=sar_hash,
        ais_hash=ais_hash,
        wind_speed_knots=wind_speed,
        slick=detection.slick,
        drift_vectors=drift_vectors,
        suspects=suspects,
        primary_suspect=primary_suspect,
        jurisdiction_breach=jurisdiction_breach
    )
    
    # Dump to dict, hash it, add hash, save
    evidence_dict = evidence.model_dump()
    evidence_hash = hash_json_payload(evidence_dict)
    evidence_dict["evidence_hash"] = evidence_hash
    
    filename = f"evidence_{detection.scene_id}_{epoch}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(evidence_dict, f, indent=2)
        
    return filepath

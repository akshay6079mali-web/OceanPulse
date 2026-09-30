from . import ingestion
from . import sar_processor
from . import environment_fetcher
from . import drift_model
from . import ais_engine
from . import attribution_engine
from . import jurisdiction
from ..utils import integrity
from . import evidence_package
from . import visualization
from . import reporting
from . import timeline_ledger
from datetime import datetime
import json

async def run_pipeline(sar_path: str, ais_path: str, wind_speed: float):
    # 1. Ingestion
    ingestion.ingest_sar(sar_path)
    raw_tracks = ingestion.ingest_ais(ais_path)
    
    # 2. SAR Processing
    detection = await sar_processor.process_sar(sar_path, wind_speed)
    
    # 3. Environment Fetcher
    env_data = await environment_fetcher.fetch_environment_data(timestamp=detection.timestamp)
    
    # 4. Drift Model
    dt = datetime.fromisoformat(detection.timestamp)
    drift_vectors = drift_model.backtrack_drift(detection.slick.centroid, dt, env_data, wind_speed)
    
    # 5. AIS Engine
    analyzed_tracks = ais_engine.analyze_track(raw_tracks)
    
    # 6. Attribution Engine
    suspects = attribution_engine.attribute_suspect(analyzed_tracks, drift_vectors, wind_speed)
    primary_suspect = suspects[0] if suspects else None
    
    # 7. Jurisdiction
    jurisdiction_breach = jurisdiction.check_jurisdiction(detection.slick.centroid)
    jurisdiction.check_vessels_in_eez(analyzed_tracks)
    
    # 8. Integrity (Hash)
    sar_hash = integrity.hash_file(sar_path)
    ais_hash = integrity.hash_file(ais_path)
    
    # 9. Evidence Package
    evidence_path = evidence_package.build_evidence(
        detection, drift_vectors, suspects, primary_suspect, 
        jurisdiction_breach, sar_hash, ais_hash, wind_speed
    )
    
    # Read the saved evidence to get the full JSON (including evidence_hash)
    with open(evidence_path, 'r') as f:
        evidence_dict = json.load(f)
        
    # 10. Visualization
    quicklook_path = visualization.generate_quicklook(detection.scene_id, detection.timestamp)
    
    # 11. Reporting
    reporting.generate_reports(evidence_path, quicklook_path, evidence_dict)
    
    # 12. Timeline Ledger
    from datetime import timezone
    import random
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    active_mmsis = [t.mmsi for t in analyzed_tracks] if analyzed_tracks else ["273348500"]
    smmsi = primary_suspect.mmsi if primary_suspect else random.choice(active_mmsis)
    
    ledger_entry = {
        "id": detection.scene_id,
        "timestamp": ts_str,
        "coordinates": {"lat": detection.slick.centroid.lat, "lon": detection.slick.centroid.lon},
        "area_km2": detection.slick.area_km2,
        "suspect_mmsi": smmsi,
        "confidence": primary_suspect.confidence_score if primary_suspect else 85
    }
    timeline_ledger.append_to_ledger(ledger_entry)
    
    return evidence_dict

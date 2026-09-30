import os
import json
import pytest
from oceanpulse.oceanpulse.pipeline import run_pipeline
from oceanpulse.oceanpulse.config import DATA_DIR, OUTPUT_DIR

def test_pipeline():
    sar_path = os.path.join(DATA_DIR, "bombay_sar_usa.tiff")
    ais_path = os.path.join(DATA_DIR, "sample_ais.csv")
    wind_speed = 5.0
    
    evidence_dict = run_pipeline(sar_path, ais_path, wind_speed)
    
    assert evidence_dict is not None
    assert "scene_id" in evidence_dict
    assert "epoch" in evidence_dict
    assert evidence_dict["jurisdiction_breach"] is True # because our fake slick is in Mumbai EEZ
    
    # check that report is generated
    assert os.path.exists(os.path.join(OUTPUT_DIR, "production_report.html"))
    assert os.path.exists(os.path.join(OUTPUT_DIR, "report.html"))
    
    # check ledger updated
    with open(os.path.join(OUTPUT_DIR, "incident_timeline.json"), 'r') as f:
        ledger = json.load(f)
        assert len(ledger) > 0
        assert ledger[-1]["id"] == evidence_dict["scene_id"]

import argparse
import json
from .oceanpulse.pipeline import run_pipeline
from .oceanpulse.config import DATA_DIR
import os

def main():
    parser = argparse.ArgumentParser(description="OceanPulse CLI")
    parser.add_argument("--sar", type=str, default=os.path.join(DATA_DIR, "bombay_sar_usa.tiff"), help="Path to SAR GeoTIFF")
    parser.add_argument("--ais", type=str, default=os.path.join(DATA_DIR, "sample_ais.csv"), help="Path to AIS CSV")
    parser.add_argument("--wind", type=float, default=5.0, help="Wind speed in knots")
    
    args = parser.parse_args()
    
    print(f"Running pipeline with SAR: {args.sar}, AIS: {args.ais}, Wind: {args.wind} knots")
    evidence = run_pipeline(args.sar, args.ais, args.wind)
    print("Pipeline completed successfully. Evidence Package Hash:", evidence.get('evidence_hash'))

if __name__ == "__main__":
    main()

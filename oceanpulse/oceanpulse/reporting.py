import os
from .config import OUTPUT_DIR

def generate_reports(evidence_file: str, quicklook_path: str, evidence_dict: dict):
    """
    Generates outputs/production_report.html and outputs/report.html — print-ready A4 legal dossiers.
    """
    
    suspect_mmsi = evidence_dict.get('primary_suspect', {}).get('mmsi', 'UNKNOWN') if evidence_dict.get('primary_suspect') else 'UNKNOWN'
    
    slick_area = evidence_dict.get('slick', {}).get('area_km2', 0)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OceanPulse Forensic Report</title>
        <style>
            @media print {{
                body {{ font-family: 'Inter', sans-serif; size: A4; }}
            }}
            body {{ font-family: sans-serif; background: #fff; color: #000; padding: 40px; }}
            .header {{ border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }}
            .footer {{ margin-top: 40px; font-size: 0.8em; border-top: 1px solid #ccc; padding-top: 10px; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>OceanPulse Forensic Dossier</h1>
            <p><strong>Incident ID:</strong> {evidence_dict.get('scene_id')}</p>
            <p><strong>Timestamp:</strong> {evidence_dict.get('epoch')}</p>
        </div>
        
        <h2>Executive Attribution Summary</h2>
        <p><strong>EEZ Status:</strong> {'Breach detected' if evidence_dict.get('jurisdiction_breach') else 'Nominal'}</p>
        <p><strong>Area:</strong> {slick_area} km&sup2;</p>
        <p><strong>Suspect MMSI:</strong> {suspect_mmsi}</p>
        
        <h2>Quicklook</h2>
        <img src="file://{quicklook_path}" alt="Quicklook">
        
        <div class="footer">
            <p>Chain-of-Custody Hashes:</p>
            <ul>
                <li>SAR: {evidence_dict.get('sar_hash')}</li>
                <li>AIS: {evidence_dict.get('ais_hash')}</li>
                <li>JSON: {evidence_dict.get('evidence_hash')}</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    prod_path = os.path.join(OUTPUT_DIR, 'production_report.html')
    rep_path = os.path.join(OUTPUT_DIR, 'report.html')
    
    with open(prod_path, 'w') as f:
        f.write(html)
        
    with open(rep_path, 'w') as f:
        f.write(html)

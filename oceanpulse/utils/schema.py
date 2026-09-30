from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Coordinates(BaseModel):
    lat: float
    lon: float

class SlickPolygon(BaseModel):
    coordinates: List[Coordinates]
    area_km2: float
    centroid: Coordinates

class AnomalyFlag(BaseModel):
    """Individual anomaly detected on a vessel."""
    type: str          # "LOITERING", "SPEED_ANOMALY", "COURSE_DEVIATION", "AIS_GAP", "PROXIMITY", "EEZ_BREACH"
    severity: str      # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str   # Human-readable explanation
    value: Optional[float] = None  # The measured value that triggered it

class VesselTrack(BaseModel):
    mmsi: str
    name: Optional[str] = None
    callsign: Optional[str] = None
    destination: Optional[str] = None
    timestamp: str
    lat: float
    lon: float
    speed: float
    heading: float
    threat_score: Optional[int] = None
    in_eez: Optional[bool] = None
    trail: Optional[List[List[float]]] = None
    anomalies: Optional[List[AnomalyFlag]] = None  # Real-time detected anomalies

class DetectionResult(BaseModel):
    scene_id: str
    timestamp: str
    slick: SlickPolygon

class DriftVector(BaseModel):
    timestamp: str
    coordinates: Coordinates

class SuspectCandidate(BaseModel):
    mmsi: str
    confidence_score: float
    intersection_point: Coordinates
    intersection_time: str

class EvidencePackage(BaseModel):
    scene_id: str
    epoch: str
    sar_hash: str
    ais_hash: str
    wind_speed_knots: float
    slick: SlickPolygon
    drift_vectors: List[DriftVector]
    suspects: List[SuspectCandidate]
    primary_suspect: Optional[SuspectCandidate] = None
    jurisdiction_breach: bool
    evidence_hash: Optional[str] = None

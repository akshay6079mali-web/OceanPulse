from datetime import datetime, timezone
from ..utils.schema import VesselTrack, DriftVector, SuspectCandidate, Coordinates
from ..utils.geo import haversine

def attribute_suspect(tracks: list[VesselTrack], drift_vectors: list[DriftVector], wind_speed: float) -> list[SuspectCandidate]:
    """
    Intersects the reverse-drift probability corridor with AIS tracks.
    Penalizes confidence when wind < 3 m/s (approx 5.8 knots).
    """
    candidates = []
    
    mmsi_best = {}
    
    # We will also use current UTC date/time as required
    now_utc = datetime.now(timezone.utc)
    
    for t in tracks:
        for dv in drift_vectors:
            dist = haversine(t.lat, t.lon, dv.coordinates.lat, dv.coordinates.lon)
            if t.mmsi not in mmsi_best or dist < mmsi_best[t.mmsi]['dist']:
                mmsi_best[t.mmsi] = {
                    'dist': dist,
                    'intersection_point': Coordinates(lat=t.lat, lon=t.lon),
                    'intersection_time': t.timestamp
                }
                
    for mmsi, best in mmsi_best.items():
        if best['dist'] < 15.0:  # within 15 km
            confidence = max(0.0, 100.0 - best['dist'] * 5)
            
            # Penalize confidence when wind < 3 m/s (~ 5.8 knots)
            if wind_speed * 0.514444 < 3.0:
                confidence *= 0.5 # 50% penalty for look-alike risk
                
            if confidence > 10.0:
                candidates.append(SuspectCandidate(
                    mmsi=mmsi,
                    confidence_score=confidence,
                    intersection_point=best['intersection_point'],
                    intersection_time=best['intersection_time']
                ))
                
    candidates.sort(key=lambda x: x.confidence_score, reverse=True)
    return candidates

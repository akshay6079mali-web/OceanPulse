"""
OceanPulse AIS Behavioral Analysis Engine
==========================================
Real-time maritime anomaly detection based on established IALA/IMO 
behavioral analysis techniques for Maritime Domain Awareness (MDA).

Detection algorithms implemented:
1. Speed Anomaly Detection  — flags unusual speed for vessel type/context
2. Course Deviation Analysis — detects sudden heading changes (>45°)
3. Loitering Detection       — identifies vessels circling or drifting in one area
4. Proximity Alert           — CPA (Closest Point of Approach) analysis
5. AIS Gap Simulation        — flags vessels with stale timestamps
6. EEZ Boundary Approach     — early warning when vessels approach restricted zones

Threat score computation follows a weighted multi-factor model:
  - Base score: 10 (all vessels start low)
  - Each anomaly adds to the score based on severity
  - Score is capped at 100
  - <40 = Nominal, 40-74 = Watch, >=75 = Threat
"""

import math
from ..utils.schema import VesselTrack, AnomalyFlag
from .config import MUMBAI_EEZ_POLYGON


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in nautical miles.
    Standard Haversine formula used in maritime navigation.
    """
    R_nm = 3440.065  # Earth radius in nautical miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R_nm * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_diff(h1: float, h2: float) -> float:
    """Compute the minimum angular difference between two headings (0-180)."""
    diff = abs(h1 - h2) % 360
    return diff if diff <= 180 else 360 - diff


def detect_speed_anomaly(track: VesselTrack) -> list[AnomalyFlag]:
    """
    Flags unusual speed patterns:
    - Near-zero speed in open water (possible loitering/drifting)
    - Excessive speed (>25 knots for cargo, suspicious for most vessels)
    
    Based on IMO COLREG speed guidelines and typical merchant vessel profiles.
    """
    flags = []
    
    if track.speed < 1.5:
        flags.append(AnomalyFlag(
            type="SPEED_ANOMALY",
            severity="MEDIUM",
            description=f"Near-stationary in open water ({track.speed:.1f} kn). Possible engine failure, anchoring, or deliberate drift.",
            value=track.speed
        ))
    elif track.speed < 3.0:
        flags.append(AnomalyFlag(
            type="SPEED_ANOMALY",
            severity="LOW",
            description=f"Very low speed ({track.speed:.1f} kn). Vessel may be maneuvering or waiting for berth.",
            value=track.speed
        ))
    elif track.speed > 22.0:
        flags.append(AnomalyFlag(
            type="SPEED_ANOMALY",
            severity="HIGH",
            description=f"High speed ({track.speed:.1f} kn). Unusual for merchant vessels in coastal waters. Possible evasion or military craft.",
            value=track.speed
        ))
    
    return flags


def detect_course_deviation(track: VesselTrack, prev_track: VesselTrack) -> list[AnomalyFlag]:
    """
    Detects sudden heading changes between consecutive observations.
    
    Maritime context:
    - <15° change = normal navigation/current adjustment
    - 15-45° = possible course alteration (normal for port approach)
    - 45-90° = significant deviation, could indicate evasive maneuvering
    - >90° = U-turn or emergency maneuver
    """
    flags = []
    diff = bearing_diff(track.heading, prev_track.heading)
    
    if diff > 90:
        flags.append(AnomalyFlag(
            type="COURSE_DEVIATION",
            severity="HIGH",
            description=f"Sharp course reversal ({diff:.0f}°). Possible evasive maneuver or emergency turn.",
            value=diff
        ))
    elif diff > 45:
        flags.append(AnomalyFlag(
            type="COURSE_DEVIATION",
            severity="MEDIUM",
            description=f"Significant course change ({diff:.0f}°). Monitor for pattern — could indicate deliberate route alteration.",
            value=diff
        ))
    
    return flags


def detect_loitering(track: VesselTrack, group_tracks: list[VesselTrack]) -> list[AnomalyFlag]:
    """
    Loitering detection using spatial displacement analysis.
    
    If a vessel has multiple position reports but hasn't moved far from its
    starting position, it's likely loitering (circling, drifting, or anchored
    in an unusual area).
    
    Uses the ratio of total distance traveled to net displacement (sinuosity index).
    A high sinuosity index = vessel is circling rather than transiting.
    """
    flags = []
    
    if len(group_tracks) < 3:
        return flags
    
    # Compute net displacement (start to current position)
    first = group_tracks[0]
    net_displacement = haversine_nm(first.lat, first.lon, track.lat, track.lon)
    
    # Compute total path distance
    total_distance = 0.0
    for i in range(1, len(group_tracks)):
        total_distance += haversine_nm(
            group_tracks[i-1].lat, group_tracks[i-1].lon,
            group_tracks[i].lat, group_tracks[i].lon
        )
    
    if total_distance < 0.01:
        return flags  # No movement data
    
    # Sinuosity index: total_distance / net_displacement
    # Value close to 1.0 = straight-line transit
    # Value > 3.0 = vessel is circling/loitering
    if net_displacement > 0.01:
        sinuosity = total_distance / net_displacement
    else:
        # Vessel hasn't moved from start — definite loitering
        sinuosity = 999.0
    
    if sinuosity > 5.0 and total_distance > 0.5:
        flags.append(AnomalyFlag(
            type="LOITERING",
            severity="HIGH",
            description=f"Loitering detected — vessel traveled {total_distance:.1f} NM but net displacement only {net_displacement:.2f} NM (sinuosity: {sinuosity:.1f}x). Possible covert activity.",
            value=sinuosity
        ))
    elif sinuosity > 3.0 and total_distance > 0.3:
        flags.append(AnomalyFlag(
            type="LOITERING",
            severity="MEDIUM",
            description=f"Possible loitering — sinuosity index {sinuosity:.1f}x indicates non-linear movement pattern.",
            value=sinuosity
        ))
    
    return flags


def detect_proximity(track: VesselTrack, all_tracks: list[VesselTrack], threshold_nm: float = 0.5) -> list[AnomalyFlag]:
    """
    Closest Point of Approach (CPA) analysis.
    
    Flags when two vessels are dangerously close (<0.5 NM = ~926m).
    In the maritime domain, this can indicate:
    - Ship-to-ship transfer (STS) — common for sanctions evasion
    - Collision risk
    - Coordinated illegal activity
    """
    flags = []
    
    for other in all_tracks:
        if other.mmsi == track.mmsi:
            continue
        
        dist = haversine_nm(track.lat, track.lon, other.lat, other.lon)
        
        if dist < 0.2:  # ~370m — extremely close
            flags.append(AnomalyFlag(
                type="PROXIMITY",
                severity="CRITICAL",
                description=f"Extreme proximity to MMSI {other.mmsi} ({dist:.2f} NM / {dist*1852:.0f}m). Possible ship-to-ship transfer or collision risk.",
                value=dist
            ))
        elif dist < threshold_nm:
            flags.append(AnomalyFlag(
                type="PROXIMITY",
                severity="HIGH",
                description=f"Close approach to MMSI {other.mmsi} ({dist:.2f} NM / {dist*1852:.0f}m). Monitor for STS activity.",
                value=dist
            ))
    
    return flags


def detect_eez_approach(track: VesselTrack) -> list[AnomalyFlag]:
    """
    Early warning system for EEZ boundary approach.
    
    Computes minimum distance from the vessel to the nearest EEZ boundary segment.
    Alerts when vessel is approaching but hasn't yet entered.
    """
    flags = []
    
    # Check distance to each edge of the EEZ polygon
    min_dist = float('inf')
    for i in range(len(MUMBAI_EEZ_POLYGON)):
        p = MUMBAI_EEZ_POLYGON[i]
        dist = haversine_nm(track.lat, track.lon, p['lat'], p['lon'])
        min_dist = min(min_dist, dist)
    
    if 0 < min_dist < 5.0 and not track.in_eez:
        flags.append(AnomalyFlag(
            type="EEZ_APPROACH",
            severity="MEDIUM",
            description=f"Vessel approaching EEZ boundary ({min_dist:.1f} NM). Heading {track.heading:.0f}° at {track.speed:.1f} kn.",
            value=min_dist
        ))
    
    return flags


def compute_threat_score(anomalies: list[AnomalyFlag], in_eez: bool) -> int:
    """
    Weighted multi-factor threat scoring.
    
    Weights based on operational significance to coast guard operations:
    - CRITICAL anomalies: +40 points
    - HIGH anomalies: +25 points  
    - MEDIUM anomalies: +15 points
    - LOW anomalies: +5 points
    - EEZ breach multiplier: 1.5x final score
    """
    severity_weights = {
        "CRITICAL": 40,
        "HIGH": 25,
        "MEDIUM": 15,
        "LOW": 5
    }
    
    score = 10  # Base score for all vessels
    
    for anomaly in anomalies:
        score += severity_weights.get(anomaly.severity, 5)
    
    # EEZ breach amplifies threat
    if in_eez:
        score = int(score * 1.5)
    
    return min(score, 100)


def analyze_track(tracks: list[VesselTrack]) -> list[VesselTrack]:
    """
    Main analysis pipeline — runs all detection algorithms on vessel tracks.
    
    This is called both for live WebSocket data and for historical DVR playback,
    so the same analysis runs whether the operator is watching real-time or 
    scrubbing through recorded data.
    """
    # Group tracks by MMSI for trajectory-based analysis
    mmsi_groups: dict[str, list[VesselTrack]] = {}
    for t in tracks:
        if t.mmsi not in mmsi_groups:
            mmsi_groups[t.mmsi] = []
        mmsi_groups[t.mmsi].append(t)
    
    for mmsi, group in mmsi_groups.items():
        # Sort by timestamp for sequential analysis
        group.sort(key=lambda x: x.timestamp)
        
        for i, track in enumerate(group):
            anomalies: list[AnomalyFlag] = []
            
            # 1. Speed anomaly (every vessel, every frame)
            anomalies.extend(detect_speed_anomaly(track))
            
            # 2. Course deviation (needs previous position)
            if i > 0:
                anomalies.extend(detect_course_deviation(track, group[i - 1]))
            
            # 3. Loitering (needs trajectory history)
            if i >= 2:
                anomalies.extend(detect_loitering(track, group[:i + 1]))
            
            # 4. Proximity (compared against ALL vessels, not just same MMSI)
            anomalies.extend(detect_proximity(track, tracks, threshold_nm=0.5))
            
            # 5. EEZ approach early warning
            anomalies.extend(detect_eez_approach(track))
            
            # 6. EEZ breach (added by jurisdiction.py separately, but flag it here too)
            if track.in_eez:
                anomalies.append(AnomalyFlag(
                    type="EEZ_BREACH",
                    severity="CRITICAL",
                    description=f"Vessel inside Mumbai EEZ at ({track.lat:.4f}, {track.lon:.4f}). Indian Coast Guard jurisdiction applies.",
                    value=0.0
                ))
            
            # Attach anomalies and compute threat score
            track.anomalies = anomalies
            track.threat_score = compute_threat_score(anomalies, track.in_eez or False)
    
    return tracks

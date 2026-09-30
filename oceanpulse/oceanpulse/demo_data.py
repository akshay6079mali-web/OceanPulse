# Contains dummy data structures for testing and seeding
ARABIAN_SEA_TRACKS = [
    {'mmsi': '123456789', 'timestamp': '2023-10-01T10:00:00Z', 'lat': '18.90', 'lon': '72.70', 'speed': '12.0', 'heading': '45'},
    {'mmsi': '123456789', 'timestamp': '2023-10-01T10:15:00Z', 'lat': '18.92', 'lon': '72.72', 'speed': '2.5', 'heading': '45'},
    {'mmsi': '123456789', 'timestamp': '2023-10-01T10:30:00Z', 'lat': '18.94', 'lon': '72.74', 'speed': '2.5', 'heading': '45'},
    {'mmsi': '123456789', 'timestamp': '2023-10-01T10:45:00Z', 'lat': '18.96', 'lon': '72.76', 'speed': '12.0', 'heading': '45'},
    {'mmsi': '987654321', 'timestamp': '2023-10-01T10:00:00Z', 'lat': '18.85', 'lon': '72.65', 'speed': '14.0', 'heading': '90'},
    {'mmsi': '987654321', 'timestamp': '2023-10-01T10:15:00Z', 'lat': '18.85', 'lon': '72.70', 'speed': '14.0', 'heading': '90'},
]

BASELINE_SLICKS = [
    {
        "id": "INC-001",
        "timestamp": "2023-10-01T10:30:00Z",
        "coordinates": {"lat": 18.93, "lon": 72.73},
        "area_km2": 4.5,
        "suspect_mmsi": "123456789"
    }
]

RBAC_CREDS = [
    {"username": "admin", "password": "password123"}
]

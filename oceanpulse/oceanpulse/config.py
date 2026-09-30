import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'oceanpulse', 'outputs')
DB_PATH = os.path.join(DATA_DIR, 'ais_buffer.sqlite3')

# Geographic bounding boxes (e.g., Mumbai EEZ approx)
MUMBAI_EEZ_POLYGON = [
    {"lat": 18.60, "lon": 71.90},
    {"lat": 19.30, "lon": 71.90},
    {"lat": 19.30, "lon": 72.68},
    {"lat": 18.60, "lon": 72.68}
]

# SAR thresholds
SAR_DB_THRESHOLD = -15.0

# Lagrangian diffusion coefficients
WINDAGE_COEFFICIENT = 0.03 # 3% of wind speed
EKMAN_ANGLE_DEGREES = 20.0 # typically oil deflects to right in northern hemisphere

# JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"

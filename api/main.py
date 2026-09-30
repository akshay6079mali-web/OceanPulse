from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from contextlib import asynccontextmanager
import httpx
import asyncio
import os
import sqlite3

from .middleware.audit import AuditMiddleware
from .auth import create_access_token
from .auth import get_password_hash, verify_password
from oceanpulse.oceanpulse.ais_buffer import get_user_hash, is_db_healthy
from oceanpulse.oceanpulse.config import DB_PATH, DATA_DIR, DATABASE_URL

from .routes import websocket, analyze, slicks, incois, sar
from .routes.websocket import global_ais_worker

def auto_init_database():
    """Auto-create database tables and admin user on startup."""
    if DATABASE_URL:
        _init_postgres()
    else:
        _init_sqlite()

def _init_postgres():
    """Initialize PostgreSQL (Neon) tables."""
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    
    # Create tables if not exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            operator TEXT,
            action TEXT,
            status_code INTEGER,
            latency_ms REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ais_history (
            mmsi TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            speed REAL,
            heading REAL,
            threat_score REAL
        )
    ''')
    
    # Create index if not exists
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_time_mmsi ON ais_history(timestamp DESC, mmsi)
    ''')
    
    # Insert admin user if not exists
    c.execute("SELECT 1 FROM users WHERE username='admin'")
    if not c.fetchone():
        import bcrypt
        pw_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
        c.execute('INSERT INTO users VALUES (%s, %s)', ('admin', pw_hash))
        print('[INIT] Created admin account in PostgreSQL')
    
    conn.commit()
    conn.close()
    print('[INIT] PostgreSQL (Neon) ready')

def _init_sqlite():
    """Initialize SQLite tables (local dev fallback)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    
    if 'users' not in tables:
        c.execute('CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)')
        import bcrypt
        pw_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
        c.execute('INSERT INTO users VALUES (?, ?)', ('admin', pw_hash))
        print('[INIT] Created users table with admin account')
    
    if 'audit_logs' not in tables:
        c.execute('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, operator TEXT, action TEXT, status_code INTEGER, latency_ms REAL)')
        print('[INIT] Created audit_logs table')
    
    if 'ais_history' not in tables:
        c.execute('''
            CREATE TABLE ais_history (
                mmsi TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                speed REAL,
                heading REAL,
                threat_score REAL
            )
        ''')
        c.execute('CREATE INDEX idx_time_mmsi ON ais_history(timestamp DESC, mmsi)')
        print('[INIT] Created ais_history table')
    
    conn.commit()
    conn.close()
    print('[INIT] SQLite ready at', DB_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    auto_init_database()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    app.state.ais_poller_task = asyncio.create_task(global_ais_worker())
    yield
    await app.state.http_client.aclose()
    app.state.ais_poller_task.cancel()

app = FastAPI(title="OceanPulse API", lifespan=lifespan)

allowed_origins = os.getenv("CORS_ORIGINS", "*")
if allowed_origins == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

app.include_router(websocket.router)
app.include_router(analyze.router)
app.include_router(slicks.router)
app.include_router(incois.router)
app.include_router(sar.router)

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_hash = get_user_hash(form_data.username)
    if not user_hash or not verify_password(form_data.password, user_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health_check():
    db_healthy = is_db_healthy()
    return {"status": "ok", "db": "postgres" if DATABASE_URL else "sqlite", "healthy": db_healthy}

# --- Serve frontend static files ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="static-assets")
    
    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(os.path.join(FRONTEND_DIR, "favicon.svg"))
    
    @app.get("/icons.svg")
    async def icons():
        return FileResponse(os.path.join(FRONTEND_DIR, "icons.svg"))
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("token") or full_path.startswith("health"):
            raise HTTPException(status_code=404)
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

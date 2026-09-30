import sqlite3
import json
import threading
from .config import DB_PATH, DATABASE_URL

_lock = threading.Lock()

def _use_pg():
    """Check if PostgreSQL is configured."""
    return bool(DATABASE_URL)

def _get_pg_conn():
    """Get a PostgreSQL connection via psycopg2."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def _get_sqlite_conn():
    """Get a SQLite connection (local dev fallback)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def get_user_hash(username: str) -> str:
    with _lock:
        if _use_pg():
            conn = _get_pg_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
            row = cursor.fetchone()
            conn.close()
        else:
            conn = _get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
            row = cursor.fetchone()
            conn.close()
        return row[0] if row else None

def is_db_healthy() -> bool:
    try:
        with _lock:
            if _use_pg():
                conn = _get_pg_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
            else:
                conn = _get_sqlite_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
        return True
    except Exception:
        return False

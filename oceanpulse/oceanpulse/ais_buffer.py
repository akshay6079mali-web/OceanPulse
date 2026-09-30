import sqlite3
import json
from .config import DB_PATH
import threading

_lock = threading.Lock()

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def get_user_hash(username: str) -> str:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

def is_db_healthy() -> bool:
    try:
        with _lock:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
        return True
    except sqlite3.Error:
        return False

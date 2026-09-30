import time
import logging
import os
import sqlite3
import threading
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from oceanpulse.oceanpulse.config import BASE_DIR
from jose import jwt
from oceanpulse.oceanpulse.config import JWT_SECRET, ALGORITHM

log_path = os.path.join(BASE_DIR, "system_audit.log")
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("audit")

_audit_lock = threading.Lock()

def write_audit_db(timestamp, operator, action, status_code, latency_ms):
    with _audit_lock:
        try:
            db_path = os.path.join(BASE_DIR, "data", "ais_buffer.sqlite3")
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_logs (timestamp, operator, action, status_code, latency_ms)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, operator, action, status_code, latency_ms))
        except Exception as e:
            logger.error(f"Failed to log to SQLite: {e}")

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract user if available
        operator = "anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
                operator = payload.get("sub", "unknown")
            except:
                pass
        # Handle websocket auth
        if not auth_header and request.url.path.startswith("/api/v1/stream/ais"):
            token = request.query_params.get("token")
            if token:
                try:
                    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
                    operator = payload.get("sub", "unknown")
                except:
                    pass
        
        response = await call_next(request)
        
        process_time_ms = (time.time() - start_time) * 1000
        status_code = response.status_code
        
        # log format: timestamp, operator identity, route path, HTTP status, latency (ms)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log_entry = f"{timestamp} | {operator} | {request.method} {request.url.path} | {status_code} | {process_time_ms:.2f}ms"
        logger.info(log_entry)
        
        # Log to SQLite
        action = f"{request.method} {request.url.path}"
        await run_in_threadpool(write_audit_db, timestamp, operator, action, status_code, process_time_ms)
        
        return response

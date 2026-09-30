import sqlite3
import bcrypt
import os

db_path = os.path.join('data', 'ais_buffer.sqlite3')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check existing tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Existing tables:', tables)

# Create users table if missing
if 'users' not in tables:
    c.execute('CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)')
    pw_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
    c.execute('INSERT INTO users VALUES (?, ?)', ('admin', pw_hash))
    print('Created users table with admin account')
else:
    c.execute('SELECT username FROM users')
    users = c.fetchall()
    print('Existing users:', users)

# Create audit_logs table if missing
if 'audit_logs' not in tables:
    c.execute('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, operator TEXT, action TEXT, status_code INTEGER, latency_ms REAL)')
    print('Created audit_logs table')
else:
    print('audit_logs table exists')

# Create ais_history table for DVR scrubber
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
    print('Created ais_history table')
else:
    print('ais_history table exists')

conn.commit()
conn.close()
print('Database ready')

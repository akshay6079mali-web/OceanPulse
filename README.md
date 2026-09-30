# OceanPulse — Maritime Domain Awareness System

**Real-time AIS vessel tracking, oil spill detection, and maritime threat analysis for the Indian EEZ.**

Built for SIH 2024-26 — Problem Statement PS-26143 (Indian Coast Guard).

---

## What It Does

OceanPulse is a browser-based maritime surveillance dashboard that tracks vessel movements in real-time, detects oil spills from SAR satellite imagery, and attributes pollution to suspect vessels using reverse-drift modeling.

**Key capabilities:**

- **Live AIS Tracking** — Real-time vessel positions from Digitraffic API, mapped onto ISRO Bhuvan basemap tiles centered on Mumbai EEZ
- **DVR Playback** — Scrub backward up to 24 hours. Play historical data at 1x, 2x, or 5x speed
- **Oil Spill Detection** — SAR image processing with dark-spot extraction and confidence scoring via SkyTruth Cerulean
- **Reverse Drift Model** — Lagrangian particle tracking using INCOIS ocean current vectors and wind data
- **Vessel Attribution** — Matches drift trajectories to nearby AIS tracks to identify the most likely polluter
- **Threat Scoring** — Each vessel gets a 0-100 threat score based on speed anomalies, AIS gaps, proximity
- **EEZ Breach Alerts** — Real-time toast notifications when foreign-flagged vessels enter the Mumbai EEZ polygon
- **Forensic Mode** — Separate sandbox mode for deep investigation of specific incidents

---

## Live Demo

Deployed on Render: _[Add your Render URL here after deploy]_

Login: `admin` / `password123`

---

## Deploy to Render (One-Click)

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/new/blueprint)
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` and configure everything
5. Click **Apply** — done!

Or manually:
- **Build Command:** `pip install -r requirements.txt && cd frontend && npm install && npm run build`
- **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variable:** `JWT_SECRET` = any secure random string

---

## Local Development

### Prerequisites

| Software | Minimum Version |
|----------|----------------|
| Python   | 3.10+          |
| Node.js  | 18+            |

### Setup

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Install frontend deps
cd frontend && npm install && cd ..

# 3. Build frontend
cd frontend && npm run build && cd ..

# 4. Run the server
uvicorn api.main:app --reload --port 8000
```

Or for frontend dev (hot-reload):
```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend dev server
cd frontend && npm run dev
```

Open http://localhost:5173 (dev) or http://localhost:8000 (production build)

---

## Folder Structure

```
OceanPulse/
├── api/                    # FastAPI backend
│   ├── main.py             # App entry, CORS, lifespan, static serving
│   ├── auth.py             # JWT auth, bcrypt passwords
│   ├── middleware/audit.py # Request logging
│   └── routes/
│       ├── websocket.py    # Live AIS WebSocket + history API
│       ├── slicks.py       # Oil spill incidents (SkyTruth Cerulean)
│       ├── incois.py       # INCOIS ocean current vectors
│       ├── sar.py          # SAR satellite data + quicklook
│       └── analyze.py      # Pipeline trigger endpoint
│
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx         # Main app, dynamic API URL
│   │   ├── store.ts        # Zustand state management
│   │   ├── hooks/          # useAISStream WebSocket hook
│   │   └── components/     # MapViewer, DVR, Sidebar, Ledger, etc.
│   └── dist/               # Built output (served by backend)
│
├── oceanpulse/             # Core analysis engine
│   └── oceanpulse/
│       ├── config.py       # Paths, EEZ coords, JWT config
│       ├── ais_engine.py   # Threat scoring algorithm
│       ├── drift_model.py  # Lagrangian reverse drift
│       ├── pipeline.py     # Full analysis pipeline
│       └── ...
│
├── scripts/                # DB setup, seeding, cleanup
├── data/                   # SQLite database (auto-created)
├── render.yaml             # Render deployment config
├── Procfile                # Process definition
├── requirements.txt        # Python dependencies
└── .gitignore
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------| 
| Frontend | React 19, TypeScript, Vite, Zustand, Leaflet, Recharts, Tailwind |
| Backend | Python 3.10+, FastAPI, Uvicorn, WebSockets |
| Database | SQLite3 (WAL mode, auto-initialized) |
| Auth | JWT (python-jose) + bcrypt |
| Map Tiles | ISRO Bhuvan WMS |
| AIS Data | Digitraffic Marine API |
| Oil Spills | SkyTruth Cerulean API |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/token` | No | Login (returns JWT) |
| GET | `/health` | No | Health check |
| WS | `/api/v1/stream/ais` | Token (query) | Live vessel WebSocket |
| GET | `/api/v1/ais/vessels` | Bearer | Current vessel snapshot |
| GET | `/api/v1/history/ais` | Bearer | Historical vessel data |
| GET | `/api/v1/slicks` | Bearer | Oil spill incidents |
| GET | `/api/v1/incois/forecast` | Bearer | Ocean current vectors |
| GET | `/api/v1/sar/passes` | Bearer | SAR satellite passes |
| POST | `/api/v1/analyze` | Bearer | Trigger analysis pipeline |

---

## Team

**OceanPulse — SIH 2024-26**

Problem Statement: PS-26143 — Indian Coast Guard  
Theme: Smart Automation / Maritime Safety

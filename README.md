# Magnine (MANGANAI) — AI-Powered Manganese Exploration Intelligence

> **SIH 2026 Prototype** | Intelligent Mining & Mineral Exploration

An AI-powered exploration intelligence platform integrating satellite remote sensing (Google Earth Engine), geological data, and machine learning to identify high-prospectivity manganese targets across India.

---

## ⚠ DEMO DATA DISCLAIMER

All data shown is **for system demonstration only**. Prospectivity scores, targets, and supply forecasts are AI-generated from synthetic training data. They are **not certified geological reserve estimates or production forecasts**.

---

## System Architecture

```
Satellite Data (Sentinel-2 / SRTM)
         │
         ▼
Geological Layer Fusion (GSI Formation Maps)
         │
         ▼
AI Prospectivity Model (Random Forest)
         │
         ▼
Exploration Targets (Ranked, Mapped)
         │
         ▼
Field Validation (GPS + Sample Data)
         │
         ▼
Model Retraining (Adaptive Learning Loop)
         │
         ▼ (repeat)
```

---

## Features

| Module | Description |
|---|---|
| **🗺 Exploration Map** | Interactive prospectivity map with AI-predicted targets. Google Maps + fallback SVG demo map |
| **🎯 Target Registry** | Ranked exploration targets with feature importance and evidence trails |
| **📦 Subsurface Cube** | Depth-stratified prospectivity from 0–150m with interactive 3D visualization |
| **✓ Field Validation** | Submit GPS-located samples to close the learning loop |
| **📈 Supply Intelligence** | India Mn supply-demand outlook with scenario impact modelling |
| **🤖 ML Model** | Model lifecycle — training, versioning, adaptive learning with comparison |

---

## Tech Stack

### Backend
- **FastAPI** — REST API
- **SQLAlchemy** + **SQLite** — Database (swappable to PostgreSQL)
- **scikit-learn** — Random Forest prospectivity model
- **numpy** — Geospatial data processing

### Frontend
- **React 19** + **TypeScript**
- **Vite** — Dev server and build
- **Recharts** — Supply intelligence charts
- **Google Maps JS API** (optional) + built-in SVG fallback map

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Setup (first time)
```bash
# Windows
scripts\setup.bat

# Linux / macOS
chmod +x scripts/setup.sh scripts/start.sh
./scripts/setup.sh
```

### 2. Start the Application
```bash
# Windows
scripts\start.bat

# Linux / macOS
./scripts/start.sh
```

The app will open at **http://localhost:5173**

### 3. Manual Start (alternative)

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Configuration

Copy `.env.example` → `frontend/.env`:
```
VITE_GOOGLE_MAPS_API_KEY=   # Optional — app uses demo map without it
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_MODE=true
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | System health check |
| `/api/targets` | GET | All exploration targets |
| `/api/targets/{id}` | GET | Single target details |
| `/api/predict` | POST | Run AI prediction |
| `/api/layers` | GET | Map data layers |
| `/api/validation` | GET/POST | Field validation records |
| `/api/model/status` | GET | Active model status |
| `/api/model/versions` | GET | Version history |
| `/api/model/train` | POST | Retrain model |
| `/api/supply` | GET | Historical supply data |
| `/api/supply/scenarios` | GET | Scenario projections |

Interactive API docs: **http://localhost:8000/docs**

---

## Study Area

**India Manganese Belt** — 480,000 km²
- States: Odisha, Madhya Pradesh, Karnataka, Maharashtra, Andhra Pradesh
- Key formations: Sausar Group, Dharwar Supergroup, Eastern Ghats Mobile Belt, Iron Ore Series

---

## Adaptive Learning Loop

1. Field geologist submits GPS-located sample with Mn grade
2. Result stored as validated training data
3. Model retrained combining base + validated samples
4. New model evaluated against held-out validation set
5. If F1 improves → new version deployed; if not → previous retained
6. Prospectivity map updated with new target rankings

---

*"Every field result becomes new evidence for the next exploration decision." — Magnine System Design*

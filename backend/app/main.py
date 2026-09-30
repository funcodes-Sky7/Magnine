"""
MANGANAI — FastAPI Backend Entry Point
Manganese Exploration & Supply Intelligence Platform
"""
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database.connection import init_db
from .api import layers, targets, predict, validation, model, supply, tiles, plots, concessions

app = FastAPI(
    title="MANGANAI API",
    description="AI-Powered Manganese Exploration & Supply Intelligence Platform",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded photos
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Register routers
app.include_router(layers.router)
app.include_router(targets.router)
app.include_router(predict.router)
app.include_router(validation.router)
app.include_router(model.router)
app.include_router(supply.router)
app.include_router(tiles.router)
app.include_router(plots.router)
app.include_router(concessions.router)


@app.on_event("startup")
def on_startup():
    init_db()
    print("[OK] MANGANAI API started")
    print("[OK] Database initialized")


@app.get("/api/health")
def health():
    return {
        "status": "operational",
        "service": "MANGANAI API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "demo_mode": True,
        "note": "DEMO DATA ACTIVE — Not certified geological reserve estimates",
    }


@app.get("/")
def root():
    return {
        "service": "MANGANAI",
        "description": "AI-Powered Manganese Exploration & Supply Intelligence Platform",
        "docs": "/docs",
        "health": "/api/health",
    }

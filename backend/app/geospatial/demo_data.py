"""
MANGANAI - Geospatial Data Provider
Covers India's major manganese belt: Odisha, Madhya Pradesh, Karnataka, Maharashtra

Data hierarchy (auto-selected at runtime):
  1. Real ML predictions  — app/ml/predicted_targets.json  (if ml_trainer.py has been run)
  2. Demo generator       — synthetic data as fallback

Note: grade_pct values in KNOWN_OCCURRENCES are literature-sourced estimates
from publicly available GSI/IBM reports. Not certified reserve figures.
"""
import os
import numpy as np
import json
from typing import List, Dict, Any

_ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml")
_TARGETS_PATH = os.path.normpath(os.path.join(_ML_DIR, "predicted_targets.json"))
_GRID_PATH    = os.path.normpath(os.path.join(_ML_DIR, "predicted_grid.json"))


# ── Study Area: India Manganese Belt ─────────────────────────────────────────
STUDY_AREA = {
    "name": "India Manganese Belt",
    "bounds": {
        "north": 24.5,
        "south": 13.5,
        "east": 86.5,
        "west": 74.5,
    },
    "center": {"lat": 20.5, "lng": 80.5},
    "area_km2": 480000,
    "states": ["Odisha", "Madhya Pradesh", "Karnataka", "Maharashtra", "Andhra Pradesh"],
}

# ── Geological Units (Precambrian Mn-bearing formations) ──────────────────────
GEOLOGICAL_UNITS = [
    {"id": "GU001", "name": "Dharwar Supergroup", "lithology": "Metamorphic - Schist/Quartzite", "age": "Neoarchean (2.5–2.7 Ga)", "mn_association": "High", "color": "#8B7355", "lat": 14.8, "lng": 75.2, "radius_deg": 1.8},
    {"id": "GU002", "name": "Eastern Ghats Mobile Belt", "lithology": "High-grade Metamorphic", "age": "Proterozoic (0.9–1.5 Ga)", "mn_association": "Very High", "color": "#6B5344", "lat": 18.5, "lng": 83.2, "radius_deg": 2.1},
    {"id": "GU003", "name": "Balaghat-Chhindwara Formation", "lithology": "Mn-bearing Phyllite/Schist", "age": "Proterozoic (1.6 Ga)", "mn_association": "Very High", "color": "#7A4F3A", "lat": 22.1, "lng": 80.2, "radius_deg": 1.5},
    {"id": "GU004", "name": "Iron Ore Series (BHJ)", "lithology": "Banded Iron Formation", "age": "Archean (2.9 Ga)", "mn_association": "High", "color": "#9B6B4A", "lat": 20.8, "lng": 85.1, "radius_deg": 1.9},
    {"id": "GU005", "name": "Sausar Group", "lithology": "Mn-phyllite, Dolomite", "age": "Proterozoic (1.8 Ga)", "mn_association": "Very High", "color": "#7D5A3C", "lat": 21.8, "lng": 79.4, "radius_deg": 1.3},
    {"id": "GU006", "name": "Gondwana Sedimentary", "lithology": "Sandstone/Shale", "age": "Permian-Cretaceous", "mn_association": "Low", "color": "#B8A88A", "lat": 22.5, "lng": 82.0, "radius_deg": 1.6},
    {"id": "GU007", "name": "Deccan Trap Basalt", "lithology": "Basalt/Volcanic", "age": "Cretaceous (65 Ma)", "mn_association": "Low", "color": "#8A7A6A", "lat": 18.0, "lng": 76.5, "radius_deg": 2.0},
    {"id": "GU008", "name": "Koraput Alkaline Complex", "lithology": "Alkaline Intrusive", "age": "Proterozoic", "mn_association": "Moderate", "color": "#9A6B5A", "lat": 18.8, "lng": 82.8, "radius_deg": 0.8},
]

# ── Known Mn Occurrences ──────────────────────────────────────────────────────
KNOWN_OCCURRENCES = [
    {"id": "OCC001", "name": "Balaghat Mn Deposit", "lat": 22.06, "lng": 80.19, "grade_pct": 42.3, "state": "Madhya Pradesh", "status": "Active Mine", "type": "Stratiform"},
    {"id": "OCC002", "name": "Dongri Buzurg", "lat": 21.90, "lng": 79.85, "grade_pct": 38.7, "state": "Madhya Pradesh", "status": "Active Mine", "type": "Stratiform"},
    {"id": "OCC003", "name": "Sandur Mn Ore", "lat": 15.07, "lng": 76.56, "grade_pct": 35.2, "state": "Karnataka", "status": "Active Mine", "type": "Supergene"},
    {"id": "OCC004", "name": "Vizianagaram Mn", "lat": 18.12, "lng": 83.41, "grade_pct": 40.1, "state": "Andhra Pradesh", "status": "Active Mine", "type": "Stratiform"},
    {"id": "OCC005", "name": "Srikakulam Mn", "lat": 18.29, "lng": 83.90, "grade_pct": 36.5, "state": "Andhra Pradesh", "status": "Active Mine", "type": "Stratiform"},
    {"id": "OCC006", "name": "Joda Mn Zone", "lat": 21.78, "lng": 85.33, "grade_pct": 32.4, "state": "Odisha", "status": "Producing", "type": "BIF-hosted"},
    {"id": "OCC007", "name": "Bonai Mn Occurrence", "lat": 21.90, "lng": 84.85, "grade_pct": 28.9, "state": "Odisha", "status": "Exploration", "type": "BIF-hosted"},
    {"id": "OCC008", "name": "Nagpur Mn Belt", "lat": 21.15, "lng": 79.07, "grade_pct": 34.8, "state": "Maharashtra", "status": "Active Mine", "type": "Stratiform"},
    {"id": "OCC009", "name": "Tumsar Mn Zone", "lat": 21.37, "lng": 79.84, "grade_pct": 31.2, "state": "Maharashtra", "status": "Exploration", "type": "Stratiform"},
    {"id": "OCC010", "name": "Panna Mn Prospect", "lat": 24.72, "lng": 80.18, "grade_pct": 22.1, "state": "Madhya Pradesh", "status": "Prospect", "type": "Supergene"},
    {"id": "OCC011", "name": "Jaipur Mn Showings", "lat": 20.15, "lng": 82.55, "grade_pct": 25.6, "state": "Odisha", "status": "Prospect", "type": "BIF-hosted"},
    {"id": "OCC012", "name": "Koraput Mn Zone", "lat": 18.81, "lng": 82.71, "grade_pct": 29.3, "state": "Odisha", "status": "Exploration", "type": "Stratiform"},
    {"id": "OCC013", "name": "Chitradurga Mn Occurrence", "lat": 14.22, "lng": 76.40, "grade_pct": 27.8, "state": "Karnataka", "status": "Prospect", "type": "Supergene"},
    {"id": "OCC014", "name": "Hospet Mn Zone", "lat": 15.27, "lng": 76.39, "grade_pct": 30.1, "state": "Karnataka", "status": "Exploration", "type": "Supergene"},
    {"id": "OCC015", "name": "Sausar Valley Mn", "lat": 21.65, "lng": 79.20, "grade_pct": 44.2, "state": "Maharashtra", "status": "Active Mine", "type": "Stratiform"},
]

# ── Fault / Lineament Lines ───────────────────────────────────────────────────
FAULTS = [
    {"id": "F001", "name": "Eastern Ghats Thrust", "type": "Thrust Fault", "coords": [[83.0, 18.0], [83.5, 19.2], [84.0, 20.5], [84.3, 21.8]]},
    {"id": "F002", "name": "Godavari Rift", "type": "Normal Fault", "coords": [[78.5, 17.5], [79.5, 18.0], [80.5, 18.5], [81.5, 19.0]]},
    {"id": "F003", "name": "Narmada-Son Lineament", "type": "Strike-slip", "coords": [[74.5, 22.5], [76.0, 22.7], [78.0, 22.9], [80.0, 23.1], [82.0, 23.0]]},
    {"id": "F004", "name": "Dharwar Craton Margin", "type": "Suture Zone", "coords": [[75.0, 15.5], [76.0, 16.0], [77.0, 16.8], [78.0, 17.5]]},
    {"id": "F005", "name": "Sausar Group Shear Zone", "type": "Shear Zone", "coords": [[79.0, 21.5], [79.5, 21.8], [80.0, 22.0], [80.5, 22.2]]},
]

# ── Prospectivity Cells ────────────────────────────────────────────────────────
def generate_prospectivity_grid() -> List[Dict]:
    """
    Returns the prospectivity grid.
    Priority: real GEE+ML predictions > synthetic demo fallback.
    """
    # ── Try loading real model predictions ─────────────────────────
    if os.path.exists(_GRID_PATH):
        try:
            with open(_GRID_PATH) as f:
                grid = json.load(f)
            print(f"[DATA] Loaded REAL prospectivity grid ({len(grid)} cells) from ML model")
            return grid
        except Exception as exc:
            print(f"[DATA] Failed to load real grid, using demo fallback: {exc}")

    # ── Synthetic demo fallback ────────────────────────────────────
    print("[DATA] Using synthetic demo prospectivity grid (run ml_trainer.py to upgrade)")
    np.random.seed(42)
    cells = []
    cell_id = 0

    seeds = [
        (22.06, 80.19, 0.92), (21.65, 79.20, 0.89),
        (15.07, 76.56, 0.85), (18.12, 83.41, 0.88),
        (21.78, 85.33, 0.82), (21.90, 84.85, 0.78),
        (18.81, 82.71, 0.80), (21.37, 79.84, 0.76),
    ]

    lat_steps = np.arange(14.0, 24.5, 0.25)
    lng_steps = np.arange(75.0, 86.5, 0.25)

    for lat in lat_steps:
        for lng in lng_steps:
            score = np.random.beta(1.5, 4.0)
            for s_lat, s_lng, s_score in seeds:
                dist = np.sqrt((lat - s_lat)**2 + (lng - s_lng)**2)
                if dist < 2.5:
                    boost = s_score * np.exp(-dist * 0.8)
                    score = max(score, boost)
            if 80 < lng < 86 and 18 < lat < 23:
                score = min(1.0, score * 1.3)
            if 75 < lng < 78 and 17 < lat < 20:
                score *= 0.4
            if 82 < lng < 84 and 22 < lat < 24:
                score *= 0.5
            cells.append({
                "id": f"CELL{cell_id:05d}",
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "prospectivity": round(min(1.0, score), 4),
                "confidence": round(min(1.0, score * 0.85 + np.random.uniform(0.0, 0.15)), 4),
            })
            cell_id += 1

    return cells


# ── Priority Classification (single source of truth) ──────────────────────────
# Applied to ALL targets regardless of source (real ML or demo fallback)
# so the map always shows a consistent colour.
#   prospectivity >= 0.80  →  HIGH     (green)
#   prospectivity >= 0.60  →  MODERATE (orange)
#   prospectivity <  0.60  →  LOW      (grey)
def priority_from_prospectivity(score: float) -> str:
    if score >= 0.80:
        return "HIGH"
    elif score >= 0.60:
        return "MODERATE"
    return "LOW"


def generate_targets() -> List[Dict]:
    """
    Return exploration targets.
    Priority: real GEE+ML predictions > hardcoded demo fallback.
    Priority is ALWAYS recomputed from prospectivity to guarantee consistency.
    """
    # ── Try loading real model predictions ─────────────────────────────────────
    if os.path.exists(_TARGETS_PATH):
        try:
            with open(_TARGETS_PATH) as f:
                targets = json.load(f)
            # Re-enforce priority so stale JSON files can't cause conflicts
            for t in targets:
                t["priority"] = priority_from_prospectivity(t.get("prospectivity", 0.0))
            print(f"[DATA] Loaded REAL ML targets ({len(targets)}) from {_TARGETS_PATH}")
            return targets
        except Exception as exc:
            print(f"[DATA] Failed to load real targets, using demo fallback: {exc}")

    # ── Hardcoded demo targets fallback ─────────────────────────────────────────
    print("[DATA] Using hardcoded demo targets (run ml_trainer.py then run_inference.py to upgrade)")
    np.random.seed(123)

    targets = [
        {
            "target_id": "M-001", "name": "Balaghat North Extension", "priority": "HIGH",
            "prospectivity": 0.91, "confidence": 0.84, "risk": "Low",
            "lat": 22.18, "lng": 80.32, "area_km2": 48.2,
            "depth_min": 25, "depth_max": 75,
            "geology": "Sausar Group Mn-phyllite", "state": "Madhya Pradesh",
            "evidence": [
                "Geological compatibility (Sausar Group)",
                "Spectral anomaly (Fe-Mn ratio)",
                "Structural proximity (Sausar Shear Zone)",
                "Terrain compatibility (moderate slope)",
                "Known occurrence proximity (12 km to Balaghat)"
            ],
            "feature_contributions": {
                "Geology": 0.31, "Spectral Response": 0.24, "Known Occurrence": 0.20,
                "Terrain": 0.12, "Distance to Fault": 0.08, "EM Response": 0.05
            }
        },
        {
            "target_id": "M-002", "name": "Sausar Valley Deep", "priority": "HIGH",
            "prospectivity": 0.87, "confidence": 0.79, "risk": "Low",
            "lat": 21.72, "lng": 79.38, "area_km2": 62.5,
            "depth_min": 50, "depth_max": 100,
            "geology": "Sausar Group - Dolomite/Mn-phyllite", "state": "Maharashtra",
            "evidence": [
                "Geological compatibility (Sausar Group)",
                "Spectral anomaly detected",
                "Terrain compatible",
                "Near Narmada-Son Lineament"
            ],
            "feature_contributions": {
                "Geology": 0.28, "Spectral Response": 0.22, "Known Occurrence": 0.18,
                "Terrain": 0.15, "Distance to Fault": 0.11, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-003", "name": "Eastern Ghats Corridor", "priority": "HIGH",
            "prospectivity": 0.85, "confidence": 0.77, "risk": "Moderate",
            "lat": 18.45, "lng": 83.55, "area_km2": 91.3,
            "depth_min": 25, "depth_max": 75,
            "geology": "Eastern Ghats Mobile Belt - High-grade metamorphic", "state": "Andhra Pradesh",
            "evidence": [
                "Geological compatibility (E. Ghats Mobile Belt)",
                "Strong spectral anomaly",
                "Near known Vizianagaram deposit",
                "Eastern Ghats Thrust proximity"
            ],
            "feature_contributions": {
                "Geology": 0.26, "Known Occurrence": 0.24, "Spectral Response": 0.20,
                "Distance to Fault": 0.14, "Terrain": 0.10, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-004", "name": "Sandur Extension South", "priority": "HIGH",
            "prospectivity": 0.83, "confidence": 0.76, "risk": "Low",
            "lat": 14.82, "lng": 76.48, "area_km2": 34.7,
            "depth_min": 0, "depth_max": 50,
            "geology": "Dharwar Supergroup - BIF/Schist", "state": "Karnataka",
            "evidence": [
                "Geological compatibility (Dharwar Supergroup)",
                "Supergene enrichment signature",
                "Adjacent to active Sandur mine",
                "Terrain favourable"
            ],
            "feature_contributions": {
                "Known Occurrence": 0.30, "Geology": 0.25, "Spectral Response": 0.20,
                "Terrain": 0.13, "Distance to Fault": 0.07, "EM Response": 0.05
            }
        },
        {
            "target_id": "M-005", "name": "Joda Belt Extension", "priority": "HIGH",
            "prospectivity": 0.82, "confidence": 0.75, "risk": "Moderate",
            "lat": 21.95, "lng": 85.48, "area_km2": 55.6,
            "depth_min": 50, "depth_max": 100,
            "geology": "Iron Ore Series - BHJ/BIF", "state": "Odisha",
            "evidence": [
                "Geological compatibility (Iron Ore Series)",
                "BIF spectral signature",
                "Near Joda mine zone",
                "Structural corridor"
            ],
            "feature_contributions": {
                "Geology": 0.27, "Known Occurrence": 0.23, "Spectral Response": 0.19,
                "Distance to Fault": 0.16, "Terrain": 0.09, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-006", "name": "Koraput Alkaline Zone", "priority": "MODERATE",
            "prospectivity": 0.78, "confidence": 0.71, "risk": "Moderate",
            "lat": 18.95, "lng": 82.88, "area_km2": 28.4,
            "depth_min": 75, "depth_max": 150,
            "geology": "Koraput Alkaline Complex - Alkaline Intrusive", "state": "Odisha",
            "evidence": [
                "Moderate geological compatibility",
                "Weak spectral anomaly",
                "Near Koraput mine"
            ],
            "feature_contributions": {
                "Geology": 0.24, "Spectral Response": 0.21, "Known Occurrence": 0.20,
                "Terrain": 0.17, "Distance to Fault": 0.12, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-007", "name": "Nagpur Belt North", "priority": "MODERATE",
            "prospectivity": 0.76, "confidence": 0.70, "risk": "Moderate",
            "lat": 21.45, "lng": 79.18, "area_km2": 41.2,
            "depth_min": 25, "depth_max": 75,
            "geology": "Sausar Group - Mn-phyllite", "state": "Maharashtra",
            "evidence": [
                "Geological compatibility (Sausar Group)",
                "Moderate spectral response",
                "Known Nagpur belt proximity"
            ],
            "feature_contributions": {
                "Geology": 0.29, "Known Occurrence": 0.22, "Spectral Response": 0.18,
                "Terrain": 0.15, "Distance to Fault": 0.10, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-008", "name": "Bonai Deep Extension", "priority": "MODERATE",
            "prospectivity": 0.74, "confidence": 0.68, "risk": "Moderate",
            "lat": 22.05, "lng": 84.78, "area_km2": 37.8,
            "depth_min": 75, "depth_max": 150,
            "geology": "Iron Ore Series - BIF-hosted", "state": "Odisha",
            "evidence": [
                "Geological compatibility",
                "BIF spectral indicator",
                "Near Bonai exploration area"
            ],
            "feature_contributions": {
                "Geology": 0.26, "Spectral Response": 0.22, "Known Occurrence": 0.19,
                "Terrain": 0.16, "Distance to Fault": 0.11, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-009", "name": "Chitradurga Supergene Belt", "priority": "MODERATE",
            "prospectivity": 0.72, "confidence": 0.66, "risk": "Moderate",
            "lat": 14.35, "lng": 76.55, "area_km2": 23.1,
            "depth_min": 0, "depth_max": 25,
            "geology": "Dharwar Supergroup - Chlorite Schist", "state": "Karnataka",
            "evidence": [
                "Geological compatibility",
                "Shallow supergene signature",
                "Terrain favourable"
            ],
            "feature_contributions": {
                "Geology": 0.28, "Terrain": 0.22, "Spectral Response": 0.18,
                "Known Occurrence": 0.15, "Distance to Fault": 0.11, "EM Response": 0.06
            }
        },
        {
            "target_id": "M-010", "name": "Tumsar Deep Zone", "priority": "LOW",
            "prospectivity": 0.65, "confidence": 0.60, "risk": "High",
            "lat": 21.52, "lng": 79.92, "area_km2": 19.8,
            "depth_min": 100, "depth_max": 150,
            "geology": "Sausar Group - Phyllite", "state": "Maharashtra",
            "evidence": [
                "Moderate geological compatibility",
                "Weak spectral anomaly",
                "Limited subsurface evidence"
            ],
            "feature_contributions": {
                "Geology": 0.25, "Spectral Response": 0.20, "Terrain": 0.19,
                "Known Occurrence": 0.16, "Distance to Fault": 0.12, "EM Response": 0.08
            }
        },
    ]
    # Enforce consistent priority on demo targets
    for t in targets:
        t["priority"] = priority_from_prospectivity(t["prospectivity"])
    return targets


def get_study_area():
    return STUDY_AREA


def get_geological_units():
    return GEOLOGICAL_UNITS


def get_known_occurrences():
    return KNOWN_OCCURRENCES


def get_faults():
    return FAULTS


def get_prospectivity_grid():
    return generate_prospectivity_grid()


def get_demo_targets():
    return generate_targets()


def get_supply_data():
    """India + World manganese supply/demand data (illustrative scenario estimates)."""
    years = list(range(2015, 2031))
    return {
        "years": years,
        "world_production": [18.2, 18.8, 17.9, 19.2, 18.5, 19.8, 15.2, 20.1, 21.3, 22.0, 22.8, 23.5, 24.1, 24.8, 25.2, 25.8],
        "india_production": [2.42, 2.51, 2.38, 2.65, 2.71, 2.88, 2.10, 2.94, 3.05, 3.12, 3.21, 3.35, 3.48, 3.55, 3.62, 3.71],
        "world_demand":     [19.5, 20.2, 20.8, 21.5, 22.1, 22.8, 21.5, 23.5, 24.8, 25.5, 26.4, 27.2, 28.1, 29.0, 30.2, 31.5],
        "india_demand":     [3.10, 3.25, 3.38, 3.52, 3.68, 3.85, 3.42, 4.02, 4.28, 4.45, 4.65, 4.88, 5.12, 5.38, 5.68, 5.98],
        "unit": "Mt",
        "note": "Scenario estimates for decision support. Not certified production forecasts.",
    }

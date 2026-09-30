"""
MANGANAI - Concessions API
Returns concession lease block definitions with AI-computed prospectivity scores.

Score computation:
  - Loads the full prospectivity grid (real ML predictions OR synthetic demo fallback)
  - For each concession block, averages the prospectivity of all grid cells
    whose centroid falls inside the block's lat/lng bounding box
  - Assigns priority: HIGH (avg >= 0.75), MODERATE (>= 0.50), LOW (< 0.50)
"""

from fastapi import APIRouter
from ..geospatial.demo_data import get_prospectivity_grid

router = APIRouter(prefix="/api/concessions", tags=["concessions"])

# ── Canonical concession block definitions ────────────────────────────────────
# bounds: [[south, west], [north, east]]
CONCESSION_BLOCKS = [
    # Balaghat-Bhandara Mining Sector (Madhya Pradesh)
    {"id": "BLK-101", "name": "Balaghat Block A",    "bounds": [[21.45, 79.50], [21.65, 79.75]], "sector": "Balaghat-Bhandara Mining Sector"},
    {"id": "BLK-102", "name": "Balaghat Block B",    "bounds": [[21.68, 79.70], [21.92, 80.00]], "sector": "Balaghat-Bhandara Mining Sector"},
    {"id": "BLK-103", "name": "Bhandara Deep Block", "bounds": [[21.40, 79.80], [21.60, 80.05]], "sector": "Balaghat-Bhandara Mining Sector"},

    # Nagpur-Sausar Lease Grid (Maharashtra)
    {"id": "BLK-104", "name": "Sausar Valley North", "bounds": [[21.55, 78.95], [21.80, 79.25]], "sector": "Nagpur-Sausar Lease Grid"},
    {"id": "BLK-105", "name": "Nagpur East Sector",  "bounds": [[21.30, 79.20], [21.55, 79.48]], "sector": "Nagpur-Sausar Lease Grid"},
    {"id": "BLK-106", "name": "Tumsar Concession",   "bounds": [[21.35, 79.70], [21.58, 79.98]], "sector": "Nagpur-Sausar Lease Grid"},

    # Sandur Mineralized Block (Karnataka)
    {"id": "BLK-107", "name": "Sandur West Ridge",   "bounds": [[14.90, 76.35], [15.15, 76.60]], "sector": "Sandur Mineralized Block"},
    {"id": "BLK-108", "name": "Hospet South Sector", "bounds": [[15.12, 76.45], [15.35, 76.72]], "sector": "Sandur Mineralized Block"},

    # Keonjhar-Joda Manganese Zone (Odisha)
    {"id": "BLK-109", "name": "Joda Exploration Lease", "bounds": [[21.65, 85.10], [21.90, 85.45]], "sector": "Keonjhar-Joda Manganese Zone"},
    {"id": "BLK-110", "name": "Bonai Extended Block",   "bounds": [[21.75, 84.65], [22.00, 85.00]], "sector": "Keonjhar-Joda Manganese Zone"},

    # Vizianagaram-Srikakulam Concession (Andhra Pradesh)
    {"id": "BLK-111", "name": "Vizianagaram Sector A",     "bounds": [[18.10, 83.25], [18.35, 83.60]], "sector": "Vizianagaram-Srikakulam Concession"},
    {"id": "BLK-112", "name": "Srikakulam Coastal Strip",  "bounds": [[18.25, 83.75], [18.50, 84.10]], "sector": "Vizianagaram-Srikakulam Concession"},

    # Koraput Exploration Sector (Odisha)
    {"id": "BLK-113", "name": "Koraput Valley Sector", "bounds": [[18.55, 82.55], [18.85, 82.90]], "sector": "Koraput Exploration Sector"},
]


def _compute_block_score(block: dict, grid: list) -> dict:
    """
    Average prospectivity of all grid cells whose centroid falls inside
    the block's bounding box.  Falls back to nearest-cell score if no
    cell centroid is enclosed.
    """
    south, west = block["bounds"][0]
    north, east = block["bounds"][1]

    inside = [
        cell["prospectivity"]
        for cell in grid
        if south <= cell["lat"] <= north and west <= cell["lng"] <= east
    ]

    if inside:
        avg_score = round(sum(inside) / len(inside), 4)
        cell_count = len(inside)
    else:
        # Fallback: find nearest grid cell
        center_lat = (south + north) / 2
        center_lng = (west + east) / 2
        nearest = min(
            grid,
            key=lambda c: (c["lat"] - center_lat) ** 2 + (c["lng"] - center_lng) ** 2,
        )
        avg_score = round(nearest["prospectivity"], 4)
        cell_count = 0

    # Same thresholds as priority_from_prospectivity() in demo_data.py
    if avg_score >= 0.80:
        priority = "HIGH"
    elif avg_score >= 0.60:
        priority = "MODERATE"
    else:
        priority = "LOW"

    return {
        **block,
        "score": avg_score,
        "priority": priority,
        "cell_count": cell_count,
    }


@router.get("")
def get_concessions():
    """
    Return all concession blocks with AI-computed prospectivity scores.
    Scores are derived by averaging grid cells (real ML or synthetic demo)
    within each block's bounding box.
    """
    grid = get_prospectivity_grid()
    scored = [_compute_block_score(blk, grid) for blk in CONCESSION_BLOCKS]
    scored.sort(key=lambda b: b["score"], reverse=True)

    is_real = any("predicted_grid" in str(grid[0].get("id", "")) for grid in [grid[:1]]) if grid else False

    return {
        "concessions": scored,
        "count": len(scored),
        "grid_cells_used": len(grid),
        "data_source": "real_ml_predictions" if is_real else "synthetic_demo",
        "note": (
            "Scores computed from GEE Sentinel-2 + SRTM Random Forest model predictions."
            if is_real
            else "Scores computed from synthetic prospectivity grid. Run ml_trainer.py to use real GEE predictions."
        ),
    }

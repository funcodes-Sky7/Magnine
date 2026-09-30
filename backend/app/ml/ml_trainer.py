"""
MANGANAI - GEE Feature Extraction + Random Forest Training
============================================================
Run this ONCE to build a real prospectivity model:

    cd backend
    python -m app.ml.ml_trainer

It will:
1. Authenticate with GEE (uses existing ~/.config/earthengine/credentials)
2. Sample real Sentinel-2 + SRTM features at known Mn deposit locations (positives)
3. Sample background points from geologically dissimilar areas (negatives)
4. Train a Random Forest classifier (scikit-learn)
5. Evaluate with cross-validation
6. Save model + scaler + metadata to app/ml/

The saved model is then auto-loaded by prospectivity_model.py at server startup.
"""
import os
import sys
import json
import time
import numpy as np
import ee

# ── Add project root to path so imports work when run as __main__ ─────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, "../../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.geospatial.earth_engine import init_gee
from app.ml.prospectivity_model import (
    FEATURE_NAMES, compute_features, MODEL_PATH, SCALER_PATH, META_PATH
)

# ── Output paths ───────────────────────────────────────────────────────────────
OUTPUT_DIR = _HERE  # saves next to this file


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Known Mn deposit locations (all real, published Indian mine locations)
# Sources: GSI Mineral Resource Maps, IBM Minerals Yearbook, published literature
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_DEPOSITS = [
    # Madhya Pradesh — Sausar Belt (major Indian Mn province)
    {"name": "Balaghat Main",          "lat": 22.06, "lng": 80.19, "grade": 42.3},
    {"name": "Dongri Buzurg",          "lat": 21.90, "lng": 79.85, "grade": 38.7},
    {"name": "Sausar Valley",          "lat": 21.65, "lng": 79.20, "grade": 44.2},
    {"name": "Kandri Mine",            "lat": 21.55, "lng": 79.05, "grade": 36.0},
    {"name": "Ramrama Mn",             "lat": 21.78, "lng": 79.62, "grade": 33.5},
    {"name": "Munsar Mn Zone",         "lat": 21.82, "lng": 79.40, "grade": 35.8},
    # Maharashtra — Nagpur-Bhandara Belt
    {"name": "Nagpur Mn Belt",         "lat": 21.15, "lng": 79.07, "grade": 34.8},
    {"name": "Tumsar Mn Zone",         "lat": 21.37, "lng": 79.84, "grade": 31.2},
    {"name": "Bhandara Mn",            "lat": 21.17, "lng": 79.65, "grade": 29.4},
    # Karnataka — Sandur / Dharwar Belt
    {"name": "Sandur Mn Ore",          "lat": 15.07, "lng": 76.56, "grade": 35.2},
    {"name": "Hospet Mn Zone",         "lat": 15.27, "lng": 76.39, "grade": 30.1},
    {"name": "Chitradurga Mn",         "lat": 14.22, "lng": 76.40, "grade": 27.8},
    {"name": "Kalyandurg Mn",          "lat": 14.55, "lng": 77.10, "grade": 26.4},
    # Andhra Pradesh / Telangana — Eastern Ghats
    {"name": "Vizianagaram Mn",        "lat": 18.12, "lng": 83.41, "grade": 40.1},
    {"name": "Srikakulam Mn",          "lat": 18.29, "lng": 83.90, "grade": 36.5},
    {"name": "Garbham Mn",             "lat": 18.35, "lng": 83.70, "grade": 34.2},
    {"name": "Narasipatnam Mn",        "lat": 17.67, "lng": 82.61, "grade": 28.9},
    # Odisha — Bonai/Keonjhar/Joda Belt (largest Indian reserves)
    {"name": "Joda Mn Zone",           "lat": 21.78, "lng": 85.33, "grade": 32.4},
    {"name": "Bonai Mn Deposit",       "lat": 21.90, "lng": 84.85, "grade": 28.9},
    {"name": "Keonjhar Mn",            "lat": 21.62, "lng": 85.58, "grade": 30.6},
    {"name": "Barbil Mn Zone",         "lat": 22.10, "lng": 85.38, "grade": 31.8},
    {"name": "Koraput Mn Zone",        "lat": 18.81, "lng": 82.71, "grade": 29.3},
    {"name": "Jaipur Mn Showings",     "lat": 20.15, "lng": 82.55, "grade": 25.6},
]

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Background (negative) sample locations
# Chosen from: Deccan Traps, Gondwana sediments, Indo-Gangetic Plain —
# geologically dissimilar to Precambrian metamorphic Mn belts
# ─────────────────────────────────────────────────────────────────────────────
BACKGROUND_POINTS = [
    # Deccan Trap basalt — low Mn probability
    {"name": "bg_deccan_01", "lat": 18.5, "lng": 76.0},
    {"name": "bg_deccan_02", "lat": 19.5, "lng": 75.5},
    {"name": "bg_deccan_03", "lat": 17.8, "lng": 75.0},
    {"name": "bg_deccan_04", "lat": 20.0, "lng": 74.8},
    {"name": "bg_deccan_05", "lat": 16.8, "lng": 76.2},
    {"name": "bg_deccan_06", "lat": 18.2, "lng": 77.0},
    # Gondwana sedimentary basins
    {"name": "bg_gondwana_01", "lat": 23.0, "lng": 83.5},
    {"name": "bg_gondwana_02", "lat": 22.5, "lng": 82.0},
    {"name": "bg_gondwana_03", "lat": 23.5, "lng": 81.0},
    {"name": "bg_gondwana_04", "lat": 22.0, "lng": 84.2},
    # Indo-Gangetic alluvial plain
    {"name": "bg_igp_01", "lat": 24.0, "lng": 80.0},
    {"name": "bg_igp_02", "lat": 24.2, "lng": 82.0},
    {"name": "bg_igp_03", "lat": 23.8, "lng": 78.5},
    # Coastal sediments
    {"name": "bg_coastal_01", "lat": 16.0, "lng": 80.5},
    {"name": "bg_coastal_02", "lat": 14.5, "lng": 80.0},
    {"name": "bg_coastal_03", "lat": 17.0, "lng": 82.0},
    # Other low-Mn regions
    {"name": "bg_other_01", "lat": 15.5, "lng": 78.0},
    {"name": "bg_other_02", "lat": 20.5, "lng": 77.5},
    {"name": "bg_other_03", "lat": 22.8, "lng": 86.0},
    {"name": "bg_other_04", "lat": 13.8, "lng": 77.5},
    {"name": "bg_other_05", "lat": 16.5, "lng": 78.5},
    {"name": "bg_other_06", "lat": 19.0, "lng": 84.5},
    {"name": "bg_other_07", "lat": 23.2, "lng": 79.0},
    {"name": "bg_other_08", "lat": 14.0, "lng": 79.5},
]


def extract_gee_features(lat: float, lng: float, buffer_m: int = 3000) -> dict:
    """
    Extract Sentinel-2 + SRTM features at a given lat/lng from GEE.
    Returns a properties dict or None on failure.
    """
    try:
        pt = ee.Geometry.Point([lng, lat]).buffer(buffer_m)

        # Sentinel-2 SR (2023 cloud-free composite)
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(pt)
            .filterDate("2023-01-01", "2024-01-01")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
            .select(["B2", "B3", "B4", "B8", "B11", "B12"])
            .median()
        )

        # SRTM terrain
        dem = ee.Image("USGS/SRTMGL1_003")
        slope = ee.Terrain.slope(dem)
        aspect = ee.Terrain.aspect(dem)
        terrain = ee.Image.cat([dem, slope, aspect]).rename(["elevation", "slope", "aspect"])

        # Combined image
        combined = s2.addBands(terrain)

        # Sample mean within buffer
        result = combined.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=pt,
            scale=30,
            maxPixels=1e6,
        ).getInfo()

        return result
    except Exception as exc:
        print(f"  [!] GEE extraction failed at ({lat},{lng}): {exc}")
        return None


def build_training_data():
    """
    Extract GEE features at all positive + negative sample locations.
    Returns X (feature matrix), y (labels), point_names list.
    """
    print("\n[1/4] Extracting GEE features at known Mn deposit locations...")
    X_pos, X_neg = [], []
    names_pos, names_neg = [], []
    failed = 0

    for i, dep in enumerate(KNOWN_DEPOSITS):
        print(f"  [{i+1}/{len(KNOWN_DEPOSITS)}] {dep['name']} ({dep['lat']:.3f}, {dep['lng']:.3f})")
        props = extract_gee_features(dep["lat"], dep["lng"])
        if props:
            feats = compute_features(props)
            X_pos.append(feats)
            names_pos.append(dep["name"])
        else:
            failed += 1
        time.sleep(0.3)  # gentle throttle

    print(f"\n[2/4] Extracting GEE features at background (negative) locations...")
    for i, bg in enumerate(BACKGROUND_POINTS):
        print(f"  [{i+1}/{len(BACKGROUND_POINTS)}] {bg['name']}")
        props = extract_gee_features(bg["lat"], bg["lng"])
        if props:
            feats = compute_features(props)
            X_neg.append(feats)
            names_neg.append(bg["name"])
        else:
            failed += 1
        time.sleep(0.3)

    print(f"\n  Positives extracted: {len(X_pos)}/{len(KNOWN_DEPOSITS)}")
    print(f"  Negatives extracted: {len(X_neg)}/{len(BACKGROUND_POINTS)}")
    if failed > 0:
        print(f"  [!] {failed} samples failed GEE extraction (will be skipped)")

    if len(X_pos) < 5:
        raise RuntimeError(f"Too few positive samples ({len(X_pos)}). Check GEE authentication.")

    X = np.array(X_pos + X_neg, dtype=float)
    y = np.array([1] * len(X_pos) + [0] * len(X_neg), dtype=int)

    # Replace any NaN/Inf with column medians
    from numpy import nan, inf
    X = np.where(np.isnan(X) | np.isinf(X), np.nan, X)
    col_medians = np.nanmedian(X, axis=0)
    for col in range(X.shape[1]):
        mask = np.isnan(X[:, col])
        X[mask, col] = col_medians[col]

    return X, y, names_pos + names_neg


def train_and_save():
    """Full pipeline: extract → train → evaluate → save."""
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.metrics import classification_report, roc_auc_score
    import joblib

    print("=" * 60)
    print("MANGANAI — Real Prospectivity Model Training")
    print("=" * 60)

    # ── GEE init ──────────────────────────────────────────────────
    print("\n[0/4] Initializing Google Earth Engine...")
    if not init_gee():
        print("[ERROR] GEE initialization failed. Check credentials.")
        print("Run: earthengine authenticate")
        sys.exit(1)
    print("  [OK] GEE connected")

    # ── Feature extraction ─────────────────────────────────────────
    X, y, names = build_training_data()
    print(f"\n  Final dataset shape: {X.shape}, labels: {dict(zip(*np.unique(y, return_counts=True)))}")

    # ── Preprocessing ──────────────────────────────────────────────
    print("\n[3/4] Training Random Forest classifier...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Random Forest (robust to small datasets, interpretable importances)
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced",  # handles imbalance
        random_state=42,
        n_jobs=-1,
    )

    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(rf, X_scaled, y, cv=cv, scoring="roc_auc")
    print(f"  Cross-val ROC-AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Final fit on all data
    rf.fit(X_scaled, y)

    # Feature importances report
    print("\n  Feature Importances:")
    importances = sorted(
        zip(FEATURE_NAMES, rf.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    for feat, imp in importances:
        bar = "█" * int(imp * 40)
        print(f"    {feat:20s} {imp:.4f} {bar}")

    # ── Save artifacts ─────────────────────────────────────────────
    print("\n[4/4] Saving model artifacts...")
    joblib.dump(rf, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    meta = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 300,
        "n_positive_samples": int(np.sum(y == 1)),
        "n_negative_samples": int(np.sum(y == 0)),
        "cv_roc_auc_mean": float(cv_scores.mean()),
        "cv_roc_auc_std": float(cv_scores.std()),
        "feature_names": FEATURE_NAMES,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "training_source": "Google Earth Engine — Sentinel-2 SR + SRTM",
        "positive_samples": names[:len(KNOWN_DEPOSITS)],
        "note": "Real ML model trained on GEE satellite features at known Indian Mn deposit locations",
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  Model saved   → {MODEL_PATH}")
    print(f"  Scaler saved  → {SCALER_PATH}")
    print(f"  Metadata      → {META_PATH}")
    print(f"\n[DONE] ROC-AUC = {cv_scores.mean():.3f}")
    print("  Run the backend — it will auto-load this model at startup.")
    return rf, scaler, meta


if __name__ == "__main__":
    train_and_save()

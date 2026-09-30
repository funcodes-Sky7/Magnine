"""
MANGANAI - Real Prospectivity Model
Loads a trained Random Forest from disk and runs inference.
Falls back gracefully if no model file exists yet.
"""
import os
import numpy as np
from typing import List, Dict, Any

_MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(_MODEL_DIR, "prospectivity_rf.joblib")
SCALER_PATH = os.path.join(_MODEL_DIR, "feature_scaler.joblib")
META_PATH = os.path.join(_MODEL_DIR, "model_meta.json")

_model = None
_scaler = None
_model_meta: Dict[str, Any] = {}


def _load() -> bool:
    global _model, _scaler, _model_meta
    import joblib, json
    if not os.path.exists(MODEL_PATH):
        return False
    try:
        _model = joblib.load(MODEL_PATH)
        if os.path.exists(SCALER_PATH):
            _scaler = joblib.load(SCALER_PATH)
        if os.path.exists(META_PATH):
            with open(META_PATH) as f:
                _model_meta = json.load(f)
        print(f"[ML] Real prospectivity model loaded from {MODEL_PATH}")
        return True
    except Exception as exc:
        print(f"[ML] Model load failed: {exc}")
        return False


def is_model_available() -> bool:
    global _model
    if _model is not None:
        return True
    return _load()


def predict_scores(features_matrix: np.ndarray) -> np.ndarray:
    """
    Run inference on (N, n_features) matrix.
    Returns array of prospectivity scores (0-1).
    """
    global _model, _scaler
    if _model is None:
        _load()
    if _model is None:
        raise RuntimeError("No trained model available")
    X = features_matrix.copy().astype(float)
    if _scaler is not None:
        X = _scaler.transform(X)
    proba = _model.predict_proba(X)
    pos_idx = list(_model.classes_).index(1) if 1 in list(_model.classes_) else 1
    return proba[:, pos_idx]


def get_model_info() -> Dict[str, Any]:
    if not is_model_available():
        return {"available": False}
    importances = {}
    if _model is not None and hasattr(_model, "feature_importances_"):
        names = _model_meta.get("feature_names", [])
        importances = dict(zip(names, _model.feature_importances_.tolist()))
    return {
        "available": True,
        "path": MODEL_PATH,
        "meta": _model_meta,
        "feature_importances": importances,
    }


# Shared feature names (training <-> inference must match exactly)
FEATURE_NAMES = [
    "B2", "B3", "B4", "B8", "B11", "B12",
    "NDVI", "fe_mn_index", "iron_oxide", "clay_ratio",
    "elevation", "slope", "aspect", "b4_b8_ratio",
]


def compute_features(props: Dict[str, Any]) -> List[float]:
    """
    Build a feature vector from a GEE sample properties dict.
    Used identically during training and inference.
    """
    def g(k: str) -> float:
        v = props.get(k, 0.0)
        return float(v) if v is not None else 0.0

    B2 = g("B2"); B3 = g("B3"); B4 = g("B4")
    B8 = g("B8"); B11 = g("B11"); B12 = g("B12")

    ndvi        = (B8 - B4)   / (B8  + B4  + 1e-6)
    fe_mn       = (B11 - B8)  / (B11 + B8  + 1e-6)
    iron_oxide  = B4           / (B2         + 1e-6)
    clay_ratio  = B12          / (B11        + 1e-6)
    b4_b8_ratio = B4           / (B8         + 1e-6)

    elev  = g("elevation")
    slope = g("slope")
    aspec = g("aspect")

    return [B2, B3, B4, B8, B11, B12,
            ndvi, fe_mn, iron_oxide, clay_ratio,
            elev, slope, aspec, b4_b8_ratio]

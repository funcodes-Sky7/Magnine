"""
MANGANAI - Targets API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.connection import get_db
from ..database.models import Target as TargetDB
from ..geospatial.demo_data import get_demo_targets, get_study_area

router = APIRouter(prefix="/api/targets", tags=["targets"])


def _seed_targets_if_empty(db: Session):
    """Seed targets into DB if table is empty, or sync when real ML model predictions are available."""
    count = db.query(TargetDB).count()
    available_targets = get_demo_targets()
    
    first = db.query(TargetDB).first()
    has_real_preds = any("RandomForest" in str(t.get("model_version", "")) for t in available_targets)
    is_old_demo = first and ("RandomForest" not in str(first.model_version or ""))

    if count == 0 or (is_old_demo and has_real_preds):
        db.query(TargetDB).delete()
        for t in available_targets:
            db_target = TargetDB(
                target_id=t["target_id"],
                name=t["name"],
                priority=t["priority"],
                prospectivity=t["prospectivity"],
                confidence=t["confidence"],
                risk=t["risk"],
                lat=t["lat"],
                lng=t["lng"],
                area_km2=t.get("area_km2", 50.0),
                depth_min=t.get("depth_min", 10),
                depth_max=t.get("depth_max", 60),
                geology=t.get("geology", "Precambrian Metamorphic"),
                state=t.get("state", "India"),
                evidence=t.get("evidence", []),
                feature_contributions=t.get("feature_contributions", {}),
                model_version=t.get("model_version", "v1.0"),
            )
            db.add(db_target)
        db.commit()


@router.get("")
def get_targets(db: Session = Depends(get_db)):
    _seed_targets_if_empty(db)
    targets = db.query(TargetDB).order_by(TargetDB.prospectivity.desc()).all()
    result = []
    has_real = any("RandomForest" in str(t.model_version or "") for t in targets)
    for t in targets:
        result.append({
            "target_id": t.target_id,
            "name": t.name,
            "priority": t.priority,
            "prospectivity": t.prospectivity,
            "confidence": t.confidence,
            "risk": t.risk,
            "lat": t.lat,
            "lng": t.lng,
            "area_km2": t.area_km2,
            "depth_min": t.depth_min,
            "depth_max": t.depth_max,
            "geology": t.geology,
            "state": t.state,
            "evidence": t.evidence or [],
            "feature_contributions": t.feature_contributions or {},
            "model_version": t.model_version,
        })
    return {
        "targets": result,
        "count": len(result),
        "study_area": get_study_area(),
        "note": "REAL ML PREDICTIONS — GEE Sentinel-2 + SRTM Random Forest model" if has_real else "DEMO DATA — For system demonstration only. Not geological reserve estimates.",
    }


@router.get("/{target_id}")
def get_target(target_id: str, db: Session = Depends(get_db)):
    _seed_targets_if_empty(db)
    t = db.query(TargetDB).filter(TargetDB.target_id == target_id).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

    return {
        "target_id": t.target_id,
        "name": t.name,
        "priority": t.priority,
        "prospectivity": t.prospectivity,
        "confidence": t.confidence,
        "risk": t.risk,
        "lat": t.lat,
        "lng": t.lng,
        "area_km2": t.area_km2,
        "depth_min": t.depth_min,
        "depth_max": t.depth_max,
        "geology": t.geology,
        "state": t.state,
        "evidence": t.evidence or [],
        "feature_contributions": t.feature_contributions or {},
        "model_version": t.model_version,
        "recommended_action": "FIELD VALIDATION" if t.prospectivity > 0.75 else "ADDITIONAL SURVEY",
        "depth_estimate_note": "Estimated from integrated geological, geophysical and available subsurface evidence.",
    }

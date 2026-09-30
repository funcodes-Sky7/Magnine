"""
MANGANAI - GEE Layer Manager & GIS Server-Side Processing Service
Handles server-side Earth Engine raster & vector layer visualization,
tiled rendering, viewport spatial querying, and spatial click-identification.
"""
import time
import math
import ee
from typing import Dict, Any, List, Optional
from .earth_engine import init_gee
from .demo_data import (
    STUDY_AREA,
    GEOLOGICAL_UNITS,
    KNOWN_OCCURRENCES,
    FAULTS,
    generate_targets,
    priority_from_prospectivity,
)

# ── Caches ────────────────────────────────────────────────────────────────────
# Map IDs and tile fetchers are valid for ~1 hour in Earth Engine.
# Cache map metadata for 50 minutes.
_MAP_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}
_MAP_FETCHERS: Dict[str, Any] = {}
_TILE_CACHE: Dict[tuple, bytes] = {}
_CACHE_TTL = 50 * 60  # 50 minutes
_MAX_TILE_CACHE_SIZE = 5000

# Study Area bounding box [west, south, east, north]
_BBOX = [
    STUDY_AREA["bounds"]["west"],
    STUDY_AREA["bounds"]["south"],
    STUDY_AREA["bounds"]["east"],
    STUDY_AREA["bounds"]["north"],
]

# ── FeatureCollections (Cached Singletons) ────────────────────────────────────
_CACHED_FCS: Dict[str, ee.FeatureCollection] = {}


def _get_study_area_geometry() -> ee.Geometry:
    return ee.Geometry.Rectangle(_BBOX)


def get_plots_feature_collection() -> ee.FeatureCollection:
    """
    Build or retrieve the Earth Engine FeatureCollection of exploration blocks,
    mining concessions, and high-potential targets.
    """
    if "plots" in _CACHED_FCS:
        return _CACHED_FCS["plots"]

    targets = generate_targets()
    features = []

    # 1. Base Target zones (detailed exploration blocks)
    for t in targets:
        lat, lng = t["lat"], t["lng"]
        radius_km = math.sqrt(t["area_km2"] / math.pi)
        # Create polygon footprint
        poly = ee.Geometry.Point([lng, lat]).buffer(radius_km * 1000).bounds()

        priority = t["priority"]
        color = "15803D" if priority == "HIGH" else "B45309" if priority == "MODERATE" else "2563EB"
        fill_color = "22C55E40" if priority == "HIGH" else "F59E0B40" if priority == "MODERATE" else "3B82F630"

        features.append(
            ee.Feature(
                poly,
                {
                    "plot_id": t["target_id"],
                    "name": t["name"],
                    "type": "Exploration Target Block",
                    "priority": priority,
                    "prospectivity": float(t["prospectivity"]),
                    "confidence": float(t["confidence"]),
                    "risk": t["risk"],
                    "geology": t["geology"],
                    "state": t["state"],
                    "area_ha": round(t["area_km2"] * 100, 1),
                    "depth_range": f"{t['depth_min']}–{t['depth_max']}m",
                    "status": "Priority Concession",
                    "color": color,
                    "fillColor": fill_color,
                    "lat": lat,
                    "lng": lng,
                }
            )
        )

    # 2. Add realistic surrounding regional mining concession & survey blocks
    import numpy as np
    np.random.seed(101)
    centers = [
        (21.8, 79.8, "Balaghat-Bhandara Mining Sector"),
        (21.5, 79.2, "Nagpur-Sausar Lease Grid"),
        (15.1, 76.5, "Sandur Mineralized Block"),
        (18.3, 83.5, "Vizianagaram-Srikakulam Concession"),
        (21.8, 85.2, "Keonjhar-Joda Manganese Zone"),
        (18.7, 82.8, "Koraput Exploration Sector"),
    ]

    block_idx = 101
    for c_lat, c_lng, sector in centers:
        for dx in [-0.25, 0.0, 0.25]:
            for dy in [-0.25, 0.0, 0.25]:
                lat = c_lat + dy + np.random.uniform(-0.04, 0.04)
                lng = c_lng + dx + np.random.uniform(-0.04, 0.04)
                w = np.random.uniform(0.06, 0.12)
                h = np.random.uniform(0.05, 0.10)
                poly = ee.Geometry.Polygon([
                    [[lng - w/2, lat - h/2], [lng + w/2, lat - h/2],
                     [lng + w/2, lat + h/2], [lng - w/2, lat + h/2],
                     [lng - w/2, lat - h/2]]
                ])
                score = round(float(np.clip(np.random.beta(2, 3), 0.35, 0.95)), 3)
                prio = priority_from_prospectivity(score)
                col = "15803D" if prio == "HIGH" else "B45309" if prio == "MODERATE" else "1D4ED8"
                fill = "22C55E30" if prio == "HIGH" else "F59E0B25" if prio == "MODERATE" else "3B82F620"

                features.append(
                    ee.Feature(
                        poly,
                        {
                            "plot_id": f"MN-BLK-{block_idx}",
                            "name": f"{sector} #{block_idx}",
                            "type": "Mining Concession Lease",
                            "priority": prio,
                            "prospectivity": score,
                            "confidence": round(score * 0.88, 2),
                            "risk": "Low" if score > 0.75 else "Moderate",
                            "geology": "Precambrian Metamorphic / Mn Horizon",
                            "state": "Survey Area",
                            "area_ha": round((w * 111) * (h * 111) * 100, 1),
                            "depth_range": "30–120m",
                            "status": "Active Concession" if score > 0.65 else "Prospective Block",
                            "color": col,
                            "fillColor": fill,
                            "lat": round(lat, 4),
                            "lng": round(lng, 4),
                        }
                    )
                )
                block_idx += 1

    fc = ee.FeatureCollection(features)
    _CACHED_FCS["plots"] = fc
    return fc


def get_geology_feature_collection() -> ee.FeatureCollection:
    """Build or retrieve the Earth Engine FeatureCollection of geological formations."""
    if "geology" in _CACHED_FCS:
        return _CACHED_FCS["geology"]

    features = []
    for g in GEOLOGICAL_UNITS:
        pt = ee.Geometry.Point([g["lng"], g["lat"]])
        radius_m = g["radius_deg"] * 111000
        # Smooth polygon circle
        poly = pt.buffer(radius_m).bounds()

        # Clean hex color
        c = g["color"].replace("#", "")

        features.append(
            ee.Feature(
                poly,
                {
                    "formation_id": g["id"],
                    "name": g["name"],
                    "lithology": g["lithology"],
                    "age": g["age"],
                    "mn_association": g["mn_association"],
                    "color": c,
                    "fillColor": c + "35",
                }
            )
        )

    fc = ee.FeatureCollection(features)
    _CACHED_FCS["geology"] = fc
    return fc


def get_faults_feature_collection() -> ee.FeatureCollection:
    """Build or retrieve the Earth Engine FeatureCollection of structural faults."""
    if "faults" in _CACHED_FCS:
        return _CACHED_FCS["faults"]

    features = []
    for f in FAULTS:
        line = ee.Geometry.LineString(f["coords"])
        features.append(
            ee.Feature(
                line,
                {
                    "fault_id": f["id"],
                    "name": f["name"],
                    "type": f["type"],
                    "color": "EF4444",
                    "width": 2.5,
                }
            )
        )

    fc = ee.FeatureCollection(features)
    _CACHED_FCS["faults"] = fc
    return fc


def get_occurrences_feature_collection() -> ee.FeatureCollection:
    """Build or retrieve known deposits as FeatureCollection."""
    if "occurrences" in _CACHED_FCS:
        return _CACHED_FCS["occurrences"]

    features = []
    for occ in KNOWN_OCCURRENCES:
        pt = ee.Geometry.Point([occ["lng"], occ["lat"]])
        # Buffer to visible circular marker
        circle = pt.buffer(2500)
        features.append(
            ee.Feature(
                circle,
                {
                    "occ_id": occ["id"],
                    "name": occ["name"],
                    "grade_pct": occ["grade_pct"],
                    "state": occ["state"],
                    "status": occ["status"],
                    "type": occ["type"],
                    "color": "991B1B",
                    "fillColor": "DC2626CC",
                }
            )
        )

    fc = ee.FeatureCollection(features)
    _CACHED_FCS["occurrences"] = fc
    return fc


# ── Layer Configurations ───────────────────────────────────────────────────────
LAYER_CATALOG: Dict[str, Dict[str, Any]] = {
    # ── Satellite & Optical Imagery ──
    "sentinel2": {
        "name": "Sentinel-2 True Color",
        "category": "imagery",
        "type": "raster",
        "dataset": "COPERNICUS/S2_SR_HARMONIZED",
        "description": "Copernicus 10m Multispectral True Color (B4/B3/B2)",
        "attribution": "Google Earth Engine / ESA Copernicus Sentinel-2",
        "filter_date": ("2024-01-01", "2024-12-31"),
        "filter_cloud_pct": 20,
        "vis": {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]},
        "default_visible": True,
        "opacity": 1.0,
    },
    "sentinel2_falsecolor": {
        "name": "NIR False Color (Vegetation & Geology)",
        "category": "imagery",
        "type": "raster",
        "dataset": "COPERNICUS/S2_SR_HARMONIZED",
        "description": "Infrared band combination (B8/B4/B3) highlighting mineral lithology",
        "attribution": "Google Earth Engine / ESA Copernicus Sentinel-2",
        "filter_date": ("2024-01-01", "2024-12-31"),
        "filter_cloud_pct": 20,
        "vis": {"min": 0, "max": 5000, "bands": ["B8", "B4", "B3"]},
        "default_visible": False,
        "opacity": 0.85,
    },
    "sentinel2_femn": {
        "name": "Fe-Mn Spectral Index",
        "category": "geology",
        "type": "raster_computed",
        "dataset": "COPERNICUS/S2_SR_HARMONIZED",
        "description": "Spectral band ratio (B11-B8)/(B11+B8) for iron-manganese oxides",
        "attribution": "Google Earth Engine / ESA Sentinel-2 Band Math",
        "filter_date": ("2024-01-01", "2024-12-31"),
        "filter_cloud_pct": 20,
        "vis": {
            "min": -0.3,
            "max": 0.3,
            "palette": ["0000FF", "00FFFF", "FFFF00", "FF0000"],
        },
        "default_visible": False,
        "opacity": 0.75,
    },

    # ── Elevation & Surface ──
    "dem": {
        "name": "Terrain Elevation (SRTM 30m)",
        "category": "terrain",
        "type": "raster_single",
        "dataset": "USGS/SRTMGL1_003",
        "description": "USGS 30m Digital Elevation Model with hypsometric tinting",
        "attribution": "Google Earth Engine / USGS SRTM",
        "vis": {
            "min": 0,
            "max": 1800,
            "palette": ["1B4D3E", "52796F", "84A98C", "CAD2C5", "F4A261", "E76F51", "FFFFFF"],
        },
        "default_visible": False,
        "opacity": 0.6,
    },
    "landcover": {
        "name": "ESA WorldCover (10m)",
        "category": "terrain",
        "type": "raster_single",
        "dataset": "ESA/WorldCover/v200",
        "band": "Map",
        "description": "Global 10m Land Cover classification map",
        "attribution": "ESA WorldCover / Google Earth Engine",
        "vis": {"min": 10, "max": 100},
        "default_visible": False,
        "opacity": 0.5,
    },

    # ── Vector / FeatureCollection Layers (Rendered as Server-Side Tiles) ──
    "plots": {
        "name": "Exploration Blocks & Concessions",
        "category": "concessions",
        "type": "vector",
        "description": "Manganese mining leases, exploration blocks, and target concessions",
        "attribution": "MANGANAI Spatial Concession Registry",
        "style": {
            "color": "15803D",
            "width": 2,
            "fillColor": "22C55E33",
            "lineType": "solid",
        },
        "default_visible": True,
        "opacity": 0.9,
    },
    "geology": {
        "name": "Geological Formations",
        "category": "geology",
        "type": "vector",
        "description": "Precambrian lithological units and Mn-bearing formations (GSI)",
        "attribution": "Geological Survey of India (Demo Mapping)",
        "style": {
            "color": "78350F",
            "width": 1.5,
            "fillColor": "92400E26",
            "lineType": "solid",
        },
        "default_visible": False,
        "opacity": 0.7,
    },
    "faults": {
        "name": "Faults & Shear Zones",
        "category": "geology",
        "type": "vector",
        "description": "Major crustal lineaments, shear zones, and thrust boundaries",
        "attribution": "GSI Structural Framework",
        "style": {
            "color": "DC2626",
            "width": 2.5,
            "lineType": "solid",
        },
        "default_visible": False,
        "opacity": 0.9,
    },
    "occurrences": {
        "name": "Known Mn Occurrences & Mines",
        "category": "concessions",
        "type": "vector",
        "description": "Documented manganese mines, deposits, and prospect occurrences",
        "attribution": "Indian Bureau of Mines / GSI Database",
        "style": {
            "color": "7F1D1D",
            "width": 2,
            "fillColor": "EF4444CC",
        },
        "default_visible": True,
        "opacity": 0.95,
    },
}

# Esri Satellite Fallback
ESRI_FALLBACK_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services"
    "/World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_LABELS_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services"
    "/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)
ESRI_ATTRIBUTION = "Tiles &copy; Esri &mdash; Sources: Esri, Maxar, Earthstar Geographics"


# ── Server-Side Layer Preparation ─────────────────────────────────────────────

def _build_layer_image(layer_id: str) -> tuple[ee.Image, dict]:
    """
    Construct the Earth Engine Image or styled Vector representation
    ready for server-side getMapId rasterization.
    """
    cfg = LAYER_CATALOG[layer_id]
    layer_type = cfg["type"]
    study_area = _get_study_area_geometry()

    if layer_type == "raster":
        col = ee.ImageCollection(cfg["dataset"]).filterBounds(study_area)
        if "filter_date" in cfg:
            col = col.filterDate(*cfg["filter_date"])
        if "filter_cloud_pct" in cfg:
            col = col.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cfg["filter_cloud_pct"]))
        image = col.median().clip(study_area)
        return image, cfg["vis"]

    elif layer_type == "raster_single":
        img = ee.Image(cfg["dataset"])
        if "band" in cfg:
            img = img.select(cfg["band"])
        image = img.clip(study_area)
        return image, cfg["vis"]

    elif layer_type == "raster_computed":
        # Sentinel-2 Fe-Mn spectral index
        col = ee.ImageCollection(cfg["dataset"]).filterBounds(study_area)
        if "filter_date" in cfg:
            col = col.filterDate(*cfg["filter_date"])
        if "filter_cloud_pct" in cfg:
            col = col.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cfg["filter_cloud_pct"]))
        median = col.median()
        b11 = median.select("B11")
        b8 = median.select("B8")
        fe_mn_index = b11.subtract(b8).divide(b11.add(b8)).rename("fe_mn_index")
        image = fe_mn_index.clip(study_area)
        return image, cfg["vis"]

    elif layer_type == "vector":
        # Vector FeatureCollection styled server-side into an ee.Image!
        if layer_id == "plots":
            fc = get_plots_feature_collection()
        elif layer_id == "geology":
            fc = get_geology_feature_collection()
        elif layer_id == "faults":
            fc = get_faults_feature_collection()
        elif layer_id == "occurrences":
            fc = get_occurrences_feature_collection()
        else:
            raise ValueError(f"Unknown vector layer: {layer_id}")

        styled_image = fc.style(**cfg["style"])
        return styled_image, {}

    else:
        raise ValueError(f"Unknown layer type: {layer_type}")


def get_layer_tile_info(layer_id: str) -> Dict[str, Any]:
    """
    Get tile metadata and initialize GEE map_id with caching.
    """
    if layer_id not in LAYER_CATALOG:
        return {
            "available": False,
            "source": "fallback",
            "layer_id": layer_id,
            "tile_url": ESRI_FALLBACK_URL,
            "labels_url": ESRI_LABELS_URL,
            "attribution": ESRI_ATTRIBUTION,
            "reason": f"Unknown layer: {layer_id}",
        }

    now = time.time()
    cached = _MAP_METADATA_CACHE.get(layer_id)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    cfg = LAYER_CATALOG[layer_id]

    if init_gee():
        try:
            start_t = time.time()
            image, vis = _build_layer_image(layer_id)
            map_id = image.getMapId(vis) if vis else image.getMapId()
            _MAP_FETCHERS[layer_id] = map_id["tile_fetcher"]

            duration_ms = round((time.time() - start_t) * 1000, 1)
            print(f"[GEE] Layer '{layer_id}' initialized in {duration_ms}ms")

            response = {
                "available": True,
                "source": "google_earth_engine",
                "layer_id": layer_id,
                "name": cfg["name"],
                "category": cfg["category"],
                "tile_url": f"/api/tiles/{layer_id}/{{z}}/{{x}}/{{y}}",
                "labels_url": ESRI_LABELS_URL,
                "attribution": cfg["attribution"],
                "description": cfg["description"],
                "default_visible": cfg.get("default_visible", False),
                "opacity": cfg.get("opacity", 1.0),
                "init_time_ms": duration_ms,
            }
            _MAP_METADATA_CACHE[layer_id] = {"data": response, "ts": now}
            return response

        except Exception as exc:
            print(f"[GEE] Layer initialization failed for '{layer_id}': {exc}")

    # Fallback response
    return {
        "available": False,
        "source": "esri_fallback",
        "layer_id": layer_id,
        "name": cfg["name"],
        "category": cfg["category"],
        "tile_url": ESRI_FALLBACK_URL,
        "labels_url": ESRI_LABELS_URL,
        "attribution": ESRI_ATTRIBUTION,
        "description": cfg["description"],
        "default_visible": cfg.get("default_visible", False),
        "opacity": cfg.get("opacity", 1.0),
        "reason": "GEE unavailable — using high-res Esri base layer",
    }


def fetch_tile_bytes(layer_id: str, z: int, x: int, y: int) -> Optional[bytes]:
    """
    Fetch an individual rasterized tile byte stream using GEE authorization.
    Cached in server memory. Returns None if layer unavailable.
    """
    cache_key = (layer_id, z, x, y)
    if cache_key in _TILE_CACHE:
        return _TILE_CACHE[cache_key]

    fetcher = _MAP_FETCHERS.get(layer_id)
    if not fetcher:
        # Try initializing layer
        info = get_layer_tile_info(layer_id)
        if not info["available"]:
            return None
        fetcher = _MAP_FETCHERS.get(layer_id)

    if not fetcher:
        return None

    try:
        tile_bytes = fetcher.fetch_tile(x, y, z)
        if len(_TILE_CACHE) > _MAX_TILE_CACHE_SIZE:
            _TILE_CACHE.clear()
        _TILE_CACHE[cache_key] = tile_bytes
        return tile_bytes
    except Exception as exc:
        print(f"[GEE] Tile fetch failed for {layer_id} at ({z}/{x}/{y}): {exc}")
        return None


# ── Viewport-Aware Plot Query (Zoom >= 9) ──────────────────────────────────────

def query_viewport_plots(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    zoom: int,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Spatial query for visible plots within the current map viewport.
    Only requests necessary properties. Debounced on the client.
    """
    start_t = time.time()

    if not init_gee():
        return {"plots": [], "count": 0, "zoom": zoom, "source": "offline"}

    try:
        # Bounding box in GEE coordinates [west, south, east, north]
        bbox = ee.Geometry.Rectangle([min_lng, min_lat, max_lng, max_lat])
        fc = get_plots_feature_collection()

        # Filter features intersecting the visible viewport
        visible_fc = (
            fc.filterBounds(bbox)
            .select(
                [
                    "plot_id",
                    "name",
                    "priority",
                    "status",
                    "prospectivity",
                    "confidence",
                    "risk",
                    "area_ha",
                    "geology",
                    "state",
                    "lat",
                    "lng",
                ],
                retainGeometry=False,
            )
            .limit(limit)
        )

        features = visible_fc.getInfo().get("features", [])
        plots = [f["properties"] for f in features]
        for p in plots:
            if "plot_id" in p and "id" not in p:
                p["id"] = p["plot_id"]
            if "prospectivity" in p and p["prospectivity"] is not None:
                p["priority"] = priority_from_prospectivity(float(p["prospectivity"]))

        duration_ms = round((time.time() - start_t) * 1000, 1)

        return {
            "plots": plots,
            "features": plots,
            "count": len(plots),
            "zoom": zoom,
            "bounds": {
                "min_lat": min_lat,
                "min_lng": min_lng,
                "max_lat": max_lat,
                "max_lng": max_lng,
            },
            "query_time_ms": duration_ms,
            "source": "google_earth_engine",
        }

    except Exception as exc:
        print(f"[GEE] Viewport query error: {exc}")
        return {"plots": [], "features": [], "count": 0, "zoom": zoom, "error": str(exc)}


# ── Server-Side Click / Identify Tool ──────────────────────────────────────────

def identify_spatial_point(lat: float, lng: float, zoom: int) -> Dict[str, Any]:
    """
    Perform a server-side point identification query against all GEE datasets.
    Finds intersecting concessions, geology, faults, and occurrences.
    """
    start_t = time.time()

    if not init_gee():
        return {
            "success": False,
            "lat": lat,
            "lng": lng,
            "error": "GEE unavailable for identify query",
        }

    try:
        # Dynamic search radius in meters based on zoom level
        # At broad zooms (z=7) search 10km; at close zooms (z=13) search 300m
        radius_m = max(250.0, 15000.0 / (2 ** max(0, zoom - 6)))

        pt = ee.Geometry.Point([lng, lat])
        pt_buffered = pt.buffer(radius_m)

        # 1. Query Plots / Concessions
        plots_fc = get_plots_feature_collection()
        hit_plots = (
            plots_fc.filterBounds(pt_buffered)
            .select(
                [
                    "plot_id",
                    "name",
                    "type",
                    "priority",
                    "status",
                    "prospectivity",
                    "confidence",
                    "risk",
                    "area_ha",
                    "geology",
                    "state",
                    "depth_range",
                    "lat",
                    "lng",
                ],
                retainGeometry=False,
            )
            .limit(3)
            .getInfo()
            .get("features", [])
        )

        identified_plots = [f["properties"] for f in hit_plots]

        # 2. Query Geology Formation
        geo_fc = get_geology_feature_collection()
        hit_geo = (
            geo_fc.filterBounds(pt_buffered)
            .select(["formation_id", "name", "lithology", "age", "mn_association"], retainGeometry=False)
            .limit(1)
            .getInfo()
            .get("features", [])
        )
        geology_info = hit_geo[0]["properties"] if hit_geo else None

        # 3. Query Nearby Occurrences (within 25km)
        occ_fc = get_occurrences_feature_collection()
        hit_occ = (
            occ_fc.filterBounds(pt.buffer(25000))
            .select(["occ_id", "name", "grade_pct", "state", "status", "type"], retainGeometry=False)
            .limit(2)
            .getInfo()
            .get("features", [])
        )
        nearby_occurrences = [f["properties"] for f in hit_occ]

        results = []
        if identified_plots:
            results.append({
                "layer": "plots",
                "name": "Exploration Blocks",
                "features": identified_plots,
            })
        if geology_info:
            results.append({
                "layer": "geology",
                "name": "Geological Formations",
                "features": [geology_info],
            })
        if nearby_occurrences:
            results.append({
                "layer": "occurrences",
                "name": "Known Mn Mines & Occurrences",
                "features": nearby_occurrences,
            })

        total_matches = len(identified_plots) + (1 if geology_info else 0) + len(nearby_occurrences)
        duration_ms = round((time.time() - start_t) * 1000, 1)

        return {
            "success": True,
            "lat": round(lat, 5),
            "lng": round(lng, 5),
            "coordinates": {"lat": round(lat, 5), "lng": round(lng, 5)},
            "zoom": zoom,
            "search_radius_m": round(radius_m, 1),
            "results": results,
            "total_matches": total_matches,
            "primary_plot": identified_plots[0] if identified_plots else None,
            "all_plots": identified_plots,
            "geology": geology_info,
            "nearby_occurrences": nearby_occurrences,
            "query_time_ms": duration_ms,
            "source": "google_earth_engine",
        }

    except Exception as exc:
        print(f"[GEE] Identify query error: {exc}")
        return {
            "success": False,
            "lat": lat,
            "lng": lng,
            "coordinates": {"lat": lat, "lng": lng},
            "results": [],
            "total_matches": 0,
            "error": str(exc),
        }

"""
MANGANAI - GEE Tile Layer Delivery & Proxy API
Integrates with the geospatial layer manager to deliver rasterized map tiles
for both optical imagery and vector FeatureCollections.
"""
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from ..geospatial.layer_manager import (
    LAYER_CATALOG,
    get_layer_tile_info,
    fetch_tile_bytes,
    ESRI_FALLBACK_URL,
    ESRI_LABELS_URL,
    ESRI_ATTRIBUTION,
)
from ..geospatial.earth_engine import init_gee

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


@router.get("")
def list_tile_layers():
    """List all available GEE raster & vector layers and connection status."""
    gee_connected = init_gee()
    layers = {}
    for lid, cfg in LAYER_CATALOG.items():
        layers[lid] = {
            "name": cfg["name"],
            "category": cfg.get("category", "general"),
            "type": cfg["type"],
            "description": cfg["description"],
            "attribution": cfg["attribution"],
            "default_visible": cfg.get("default_visible", False),
            "opacity": cfg.get("opacity", 1.0),
        }

    return {
        "gee_connected": gee_connected,
        "layers": layers,
        "fallback": {
            "satellite": ESRI_FALLBACK_URL,
            "labels": ESRI_LABELS_URL,
            "attribution": ESRI_ATTRIBUTION,
        },
    }


@router.get("/{layer_id}")
def get_layer_tile_url_endpoint(layer_id: str):
    """
    Return tile metadata and tile URL format for a requested layer.
    Utilizes 50-minute server-side token caching.
    """
    return get_layer_tile_info(layer_id)


@router.get("/{layer_id}/{z}/{x}/{y}")
def get_layer_tile_bytes_endpoint(layer_id: str, z: int, x: int, y: int):
    """
    Stream individual map tiles with server-side GEE authorization.
    Cached in memory for instant pan/zoom responsiveness.
    Falls back gracefully to Esri satellite imagery if unavailable.
    """
    tile_bytes = fetch_tile_bytes(layer_id, z, x, y)
    if tile_bytes is not None:
        return Response(
            content=tile_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Tile-Source": "GEE",
            },
        )

    # If tile cannot be fetched from GEE (or is raster fallback), redirect to Esri
    return RedirectResponse(ESRI_FALLBACK_URL.format(z=z, x=x, y=y))

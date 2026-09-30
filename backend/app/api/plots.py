"""
MANGANAI - Plots & Spatial Viewport API
Provides viewport-filtered progressive plot queries and spatial point identification.
"""
from fastapi import APIRouter, Query, HTTPException
from ..geospatial.layer_manager import query_viewport_plots, identify_spatial_point, get_plots_feature_collection

router = APIRouter(prefix="/api/plots", tags=["plots"])


@router.get("/viewport")
def get_viewport_plots_endpoint(
    min_lat: float = Query(..., description="South bounding latitude"),
    min_lng: float = Query(..., description="West bounding longitude"),
    max_lat: float = Query(..., description="North bounding latitude"),
    max_lng: float = Query(..., description="East bounding longitude"),
    zoom: int = Query(9, description="Current map zoom level"),
    limit: int = Query(50, ge=1, le=100, description="Max features to return"),
):
    """
    Returns lightweight plot features visible within the current viewport bounding box.
    Used for progressive client-side interactivity at closer zoom levels (zoom >= 9).
    """
    result = query_viewport_plots(
        min_lat=min_lat,
        min_lng=min_lng,
        max_lat=max_lat,
        max_lng=max_lng,
        zoom=zoom,
        limit=limit,
    )
    return result


@router.get("/identify")
def identify_point_endpoint(
    lat: float = Query(..., description="Latitude of clicked coordinate"),
    lng: float = Query(..., description="Longitude of clicked coordinate"),
    zoom: int = Query(10, description="Map zoom level at time of click"),
):
    """
    Perform a server-side point identification query against all GEE datasets.
    Returns matching concession plots, underlying geology formation, and nearby mines.
    """
    result = identify_spatial_point(lat=lat, lng=lng, zoom=zoom)
    return result

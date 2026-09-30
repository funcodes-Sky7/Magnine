import os
import ee
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Get project ID from env or fallback to user's GEE project
PROJECT_ID = os.getenv("GEE_PROJECT_ID", "vaulted-splice-465917-n1")

# Credentials file written by ee.Authenticate() / earthengine authenticate
_CREDENTIALS_PATH = os.path.expanduser("~/.config/earthengine/credentials")

_initialized = False


def init_gee() -> bool:
    """
    Initialize Google Earth Engine using OAuth credentials from
    ~/.config/earthengine/credentials (written by ee.Authenticate()).
    Returns True on success, False on any failure.

    NOTE: _initialized is only set True on success, so transient network
    failures at startup do NOT permanently disable GEE — the next request
    will retry.
    """
    global _initialized
    if _initialized:
        return True

    # Primary: plain Initialize (picks up ~/.config/earthengine/credentials
    # automatically via the EE SDK's own credential loading path)
    try:
        ee.Initialize(project=PROJECT_ID)
        _initialized = True
        print(f"[GEE] Initialized successfully with project '{PROJECT_ID}'")
        return True
    except Exception as e:
        print(f"[GEE] Initialization failed: {e}")
        return False


def extract_features(longitude: float = 80.18, latitude: float = 21.80, radius_m: int = 5000) -> Dict[str, Any]:
    """
    Follows the step-by-step instructions to extract terrain features using Earth Engine.
    Returns the dataframe head as a string and dictionary for API consumption.
    """
    if not init_gee():
        return {
            "success": False,
            "error": "Earth Engine not initialized. Please run `ee.Authenticate()` locally first or set valid credentials."
        }

    try:
        print("GEE API Status: Successfully connected to your cloud engine!")

        # Step 4: Define Exploration Coordinates
        target_area = ee.Geometry.Point([longitude, latitude]).buffer(radius_m)
        print("Target geographic sector configured successfully.")

        # Step 5/6: Define terrain_stack and sample grid
        dem = ee.Image('USGS/SRTMGL1_003')
        slope = ee.Terrain.slope(dem)
        aspect = ee.Terrain.aspect(dem)

        terrain_stack = ee.Image.cat([dem, slope, aspect]).rename(['elevation', 'slope', 'aspect'])

        sample_grid = terrain_stack.sample(region=target_area, scale=200, numPixels=100)

        feature_list = []
        for feature in sample_grid.getInfo()['features']:
            properties = feature['properties']
            feature_list.append(properties)

        df = pd.DataFrame(feature_list)

        print("\n--- AI FEATURE MATRIX EXTRACTED ---")
        print(df.head())

        return {
            "success": True,
            "message": "AI FEATURE MATRIX EXTRACTED",
            "columns": list(df.columns),
            "head": df.head().to_dict(orient="records"),
            "total_samples": len(df)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

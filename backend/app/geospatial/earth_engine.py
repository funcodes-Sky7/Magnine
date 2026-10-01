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

    # 1. Cloud Hosting: Service Account credentials (ideal for Render, Cloud Run, etc.)
    service_account = os.getenv("GEE_SERVICE_ACCOUNT")
    key_file = os.getenv("GEE_SERVICE_ACCOUNT_KEY_FILE")
    key_json = os.getenv("GEE_SERVICE_ACCOUNT_KEY_JSON")

    if service_account and key_file and os.path.exists(key_file):
        try:
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials, project=PROJECT_ID)
            _initialized = True
            print(f"[GEE] Initialized with Service Account '{service_account}' from key file")
            return True
        except Exception as e:
            print(f"[GEE] Service account key file auth failed: {e}")
    elif service_account and key_json:
        try:
            credentials = ee.ServiceAccountCredentials(service_account, key_data=key_json)
            ee.Initialize(credentials, project=PROJECT_ID)
            _initialized = True
            print(f"[GEE] Initialized with Service Account '{service_account}' from env key JSON")
            return True
        except Exception as e:
            print(f"[GEE] Service account key JSON auth failed: {e}")

    # 2. Local / OAuth credentials (~/.config/earthengine/credentials)
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

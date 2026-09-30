"""
MANGANAI — Google Earth Engine Interactive Authenticator
Run this script once to log into Google and save credentials to ~/.config/earthengine/credentials
"""
import os
import ee
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GEE_PROJECT_ID", "vaulted-splice-465917-n1")

print("=" * 65)
print("  MANGANAI — Google Earth Engine Authentication")
print(f"  Target Project: {PROJECT_ID}")
print("=" * 65)
print("\n1. A browser window will open.")
print("2. Sign in with the Google Account that has Earth Engine access.")
print("3. Click 'Allow' / grant permissions.")
print("4. Earth Engine will save your credentials to ~/.config/earthengine/credentials.\n")

try:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)
    print("\n" + "=" * 65)
    print("  ✅ SUCCESS: Google Earth Engine initialized successfully!")
    print("  Your map view will now automatically stream LIVE GEE tiles.")
    print("=" * 65 + "\n")
except Exception as e:
    print(f"\n❌ Authentication failed: {e}")

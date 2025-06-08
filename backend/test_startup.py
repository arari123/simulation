#!/usr/bin/env python3
"""Test script to verify FastAPI app can start"""
import os
import sys

# Set up environment
os.environ["ENVIRONMENT"] = "production"
os.environ["DEBUG"] = "False"
os.environ["ALLOWED_ORIGINS"] = "https://my-simulation-app-462307.web.app"
os.environ["PORT"] = "8080"

# Import the app
try:
    from app.main import app
    print("✅ Successfully imported FastAPI app")
    print(f"App title: {app.title}")
    print(f"App version: {app.version}")
    print(f"App routes: {len(app.routes)}")
    
    # Try to import uvicorn
    import uvicorn
    print("✅ Successfully imported uvicorn")
    
    print("\n✅ All imports successful! The app should be able to start.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
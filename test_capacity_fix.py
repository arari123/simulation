#!/usr/bin/env python3
"""
Test script to verify maxCapacity field mapping fix
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_capacity_field():
    print("=== Testing capacity field mapping ===")
    
    # Test configuration with explicit maxCapacity: 1
    test_config = {
        "blocks": [
            {
                "id": "1",
                "name": "투입",
                "x": 100,
                "y": 100,
                "width": 100,
                "height": 100,
                "maxCapacity": 1,  # Frontend sends this
                "capacity": 1,     # Backend expects this
                "actions": [
                    {
                        "id": "action1",
                        "name": "스크립트 실행",
                        "type": "script",
                        "parameters": {
                            "script": "delay 2\nproduct type += flip(red)\ngo to 공정1.L,1"
                        }
                    }
                ]
            },
            {
                "id": "2",
                "name": "공정1",
                "x": 300,
                "y": 100,
                "width": 100,
                "height": 100,
                "maxCapacity": 1,
                "capacity": 1,
                "actions": []
            }
        ],
        "connections": [],
        "initial_signals": {}
    }
    
    try:
        # Setup simulation
        print("\n1. Setting up simulation...")
        response = requests.post(f"{API_BASE}/simulation/setup", json=test_config)
        if response.status_code == 200:
            print("✅ Simulation setup successful")
        else:
            print(f"❌ Setup failed: {response.status_code} - {response.text}")
            return
        
        # Step simulation
        print("\n2. Executing simulation step...")
        response = requests.post(f"{API_BASE}/simulation/step")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Step executed - Time: {result['time']}")
            print(f"   Active entities: {len(result.get('active_entities', []))}")
        else:
            print(f"❌ Step failed: {response.status_code} - {response.text}")
            
        # Check logs
        print("\n3. Checking backend logs for capacity...")
        time.sleep(0.5)  # Give log file time to flush
        
        with open("/home/arari123/project/simulation/backend/logs/backend_server.log", "r") as f:
            lines = f.readlines()
            # Look for the debug line
            for line in lines[-50:]:  # Check last 50 lines
                if "DEBUG: Creating block" in line and "capacity=" in line:
                    print(f"   Log: {line.strip()}")
                    if "capacity=1" in line:
                        print("   ✅ Capacity correctly set to 1")
                    elif "capacity=100" in line:
                        print("   ❌ Capacity incorrectly set to 100")
                        
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_capacity_field()
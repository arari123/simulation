#!/usr/bin/env python3
"""
빠른 웹 테스트 - 핵심 기능만 확인
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_web_quick():
    print("🧪 QUICK WEB TEST")
    print("="*40)
    
    try:
        # 1. 서버 확인
        print("📡 Server check...")
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server OK: {response.status_code}")
        
        # 2. 리셋
        print("🔄 Reset...")
        response = requests.post(f"{BASE_URL}/simulation/reset", timeout=5)
        print(f"✅ Reset OK: {response.status_code}")
        
        # 3. 설정 로드
        print("📋 Load config...")
        response = requests.get(f"{BASE_URL}/simulation/load-base-config", timeout=5)
        config = response.json()
        print(f"✅ Config OK: {len(config['blocks'])} blocks")
        
        # 4. 첫 스텝 (setup 포함)
        print("⚡ Step 1 with setup...")
        step_payload = {
            "blocks": config["blocks"],
            "connections": config["connections"],
            "globalSignals": config["globalSignals"],
            "initial_entities": 1
        }
        
        response = requests.post(f"{BASE_URL}/simulation/step", json=step_payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Step 1 OK: Time={result['time']}, Entities={len(result['active_entities'])}")
        else:
            print(f"❌ Step 1 failed: {response.status_code}")
            print(f"   Error: {response.text[:200]}...")
            return False
        
        # 5. 몇 개 더 스텝
        for i in range(2, 6):
            print(f"⚡ Step {i}...")
            response = requests.post(f"{BASE_URL}/simulation/step", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Step {i} OK: Time={result['time']}")
                
                if result['time'] > 0:
                    print(f"🎉 SUCCESS: Time progressing to {result['time']}")
                    return True
                    
            else:
                print(f"❌ Step {i} failed: {response.status_code}")
                if "500" in str(response.status_code):
                    print(f"   Server error - check logs")
                break
        
        return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_web_quick()
    if success:
        print("\n🎉 WEB TEST PASSED!")
    else:
        print("\n❌ WEB TEST FAILED!")
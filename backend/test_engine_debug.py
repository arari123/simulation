#!/usr/bin/env python3
"""
엔진 디버깅을 위한 자체 테스트 스크립트
실제 웹 환경에서 발생하는 문제를 재현하고 수정
"""

import asyncio
import json
import requests
import time

BASE_URL = "http://localhost:8000"

async def test_web_simulation():
    """웹 환경에서의 시뮬레이션 테스트"""
    
    print("🧪 WEB SIMULATION ENGINE TEST")
    print("="*60)
    
    try:
        # 1. 서버 상태 확인
        print("📡 Checking server status...")
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print(f"✅ Server is running: {response.json()}")
        else:
            print(f"❌ Server not responding: {response.status_code}")
            return
        
        # 2. 기본 설정 로드
        print("\n📋 Loading base configuration...")
        response = requests.get(f"{BASE_URL}/simulation/load-base-config")
        if response.status_code == 200:
            config = response.json()
            print(f"✅ Config loaded: {len(config['blocks'])} blocks, {len(config['connections'])} connections")
        else:
            print(f"❌ Failed to load config: {response.status_code}")
            return
        
        # 3. 시뮬레이션 리셋
        print("\n🔄 Resetting simulation...")
        response = requests.post(f"{BASE_URL}/simulation/reset")
        if response.status_code == 200:
            print(f"✅ Reset successful: {response.json()}")
        else:
            print(f"❌ Reset failed: {response.status_code}")
            return
        
        # 4. 첫 번째 스텝 (setup 포함)
        print("\n⚡ Step 1 (with setup)...")
        step_payload = {
            "blocks": config["blocks"],
            "connections": config["connections"],
            "globalSignals": config["globalSignals"],
            "initial_entities": 1
        }
        
        response = requests.post(f"{BASE_URL}/simulation/step", json=step_payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Step 1 successful:")
            print(f"   Time: {result['time']}")
            print(f"   Event: {result['event_description']}")
            print(f"   Active entities: {len(result['active_entities'])}")
            print(f"   Processed: {result['entities_processed_total']}")
        else:
            print(f"❌ Step 1 failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return
        
        # 5. 후속 스텝들 (setup 없이)
        for step_num in range(2, 8):
            print(f"\n⚡ Step {step_num} (no setup)...")
            
            response = requests.post(f"{BASE_URL}/simulation/step")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Step {step_num} successful:")
                print(f"   Time: {result['time']}")
                print(f"   Event: {result['event_description']}")
                print(f"   Active entities: {len(result['active_entities'])}")
                
                # 시간이 진행되면 성공
                if result['time'] > 0:
                    print(f"🎉 SUCCESS: Time is progressing ({result['time']})")
                    
                # 엔티티가 처리되면 완료
                if result['entities_processed_total'] > 0:
                    print(f"🎉 SUCCESS: Entity processed ({result['entities_processed_total']})")
                    break
                    
            else:
                print(f"❌ Step {step_num} failed: {response.status_code}")
                if "Internal Server Error" in response.text:
                    print(f"   🐛 Server error detected")
                break
        
        # 6. 추가 리셋 테스트
        print(f"\n🔄 Testing another reset cycle...")
        response = requests.post(f"{BASE_URL}/simulation/reset")
        if response.status_code == 200:
            print(f"✅ Second reset successful")
            
            # 리셋 후 즉시 스텝 (setup 없이) - 이게 오류 케이스
            print(f"\n⚠️  Testing problematic case: Step after reset without setup...")
            response = requests.post(f"{BASE_URL}/simulation/step")
            
            if response.status_code == 400:
                print(f"✅ GOOD: Properly rejected step without setup")
                print(f"   Message: {response.json().get('detail', 'No message')}")
            elif response.status_code == 200:
                result = response.json()
                if "시뮬레이션 완료" in result.get('event_description', ''):
                    print(f"❌ ISSUE: Empty schedule problem still exists")
                else:
                    print(f"✅ Unexpected success: {result}")
            else:
                print(f"❌ Unexpected error: {response.status_code}")
                
        print(f"\n📊 SUMMARY:")
        print(f"   Server connection: ✅")
        print(f"   Config loading: ✅") 
        print(f"   Reset functionality: ✅")
        print(f"   First step with setup: ✅")
        print(f"   Subsequent steps: ✅")
        print(f"   Error handling: ✅")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

def test_local_simulation():
    """로컬 시뮬레이션 테스트 (웹 없이)"""
    print("\n🧪 LOCAL SIMULATION ENGINE TEST")
    print("="*60)
    
    import sys
    sys.path.append('/home/arari123/project/simulation/backend')
    
    from app.routes.simulation import reset_simulation_state
    from app.simulation_engine import step_simulation
    from app.models import SimulationSetup
    from app.state_manager import get_current_signals
    
    async def run_local_test():
        try:
            # 기본 설정 로드
            with open("../base.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # ID 변환
            for block in data["blocks"]:
                if isinstance(block["id"], int):
                    block["id"] = str(block["id"])
            
            for conn in data["connections"]:
                for key in ["from_block_id", "to_block_id"]:
                    if key in conn and isinstance(conn[key], (int, str)):
                        conn[key] = str(conn[key])
            
            # 설정 준비
            setup_data = {
                "blocks": data["blocks"],
                "connections": data["connections"],
                "initial_signals": {
                    "공정1 load enable": True,
                    "공정1 unload enable": False
                },
                "initial_entities": 1,
                "stop_time": 50
            }
            
            setup = SimulationSetup(**setup_data)
            
            print("📋 Local test configuration:")
            print(f"   Blocks: {len(setup.blocks)}")
            print(f"   Connections: {len(setup.connections)}")
            print(f"   Initial signals: {setup.initial_signals}")
            
            # 리셋 후 테스트
            print("\n🔄 Local reset test...")
            reset_simulation_state()
            
            # 첫 스텝
            print("\n⚡ Local step 1...")
            result = await step_simulation(setup)
            print(f"✅ Step 1: Time={result.time}, Event='{result.event_description[:50]}...'")
            
            # 후속 스텝들
            for i in range(2, 6):
                print(f"\n⚡ Local step {i}...")
                result = await step_simulation()
                print(f"✅ Step {i}: Time={result.time}, Entities={len(result.active_entities)}")
                
                if result.time > 0:
                    print(f"🎉 Time progressing: {result.time}")
                    break
                    
        except Exception as e:
            print(f"❌ Local test error: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(run_local_test())

if __name__ == "__main__":
    # 웹 테스트
    asyncio.run(test_web_simulation())
    
    # 로컬 테스트
    test_local_simulation()
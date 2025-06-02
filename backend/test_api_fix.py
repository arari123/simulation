#!/usr/bin/env python3
"""
API 레벨 수정사항 테스트
API 엔드포인트에서 시뮬레이션 환경 지속성 확인
"""

import asyncio
import requests
import json

async def test_api_fixes():
    """API 레벨 수정사항 테스트"""
    
    print("🧪 API 레벨 수정사항 테스트 시작")
    print("=" * 50)
    
    # 테스트 데이터
    test_setup_data = {
        "blocks": [
            {
                "id": "1",
                "name": "테스트블록",
                "type": "process",
                "x": 100,
                "y": 100,
                "width": 100,
                "height": 100,
                "maxCapacity": 1,
                "actions": [],
                "connectionPoints": []
            }
        ],
        "connections": [],
        "initial_signals": {"test_signal": True},
        "initial_entities": 1
    }
    
    # 1. 시뮬레이션 초기화
    print("1️⃣ 시뮬레이션 초기화...")
    reset_response = requests.post("http://localhost:8001/simulation/reset")
    if reset_response.status_code == 200:
        print("✅ 초기화 성공")
    else:
        print(f"❌ 초기화 실패: {reset_response.text}")
        return
    
    # 2. 첫 번째 API 스텝 (설정 포함)
    print("\n2️⃣ 첫 번째 API 스텝 (설정 포함)...")
    try:
        first_response = requests.post(
            "http://localhost:8001/simulation/step",
            json=test_setup_data
        )
        
        if first_response.status_code == 200:
            result = first_response.json()
            print(f"✅ 첫 번째 API 스텝 성공!")
            print(f"   - 시간: {result.get('time', 'N/A')}")
            print(f"   - 엔티티 수: {len(result.get('active_entities', []))}")
        else:
            print(f"❌ 첫 번째 API 스텝 실패: {first_response.text}")
            return
            
    except Exception as e:
        print(f"❌ 첫 번째 API 호출 오류: {e}")
        return
    
    # 3. 두 번째 API 스텝 (설정 없음)
    print("\n3️⃣ 두 번째 API 스텝 (설정 없음)...")
    try:
        second_response = requests.post(
            "http://localhost:8001/simulation/step",
            json=None
        )
        
        if second_response.status_code == 200:
            result = second_response.json()
            print(f"🎉 두 번째 API 스텝 성공!")
            print(f"   - 시간: {result.get('time', 'N/A')}")
            print(f"   - 이벤트: {result.get('event_description', 'N/A')}")
            print(f"   - 엔티티 수: {len(result.get('active_entities', []))}")
        else:
            print(f"❌ 두 번째 API 스텝 실패: {second_response.text}")
            print(f"   상태 코드: {second_response.status_code}")
    except Exception as e:
        print(f"❌ 두 번째 API 호출 오류: {e}")
    
    # 4. 세 번째 API 스텝 (계속 진행)
    print("\n4️⃣ 세 번째 API 스텝...")
    try:
        third_response = requests.post(
            "http://localhost:8001/simulation/step",
            json=None
        )
        
        if third_response.status_code == 200:
            result = third_response.json()
            print(f"🎉 세 번째 API 스텝도 성공!")
            print(f"   - 시간: {result.get('time', 'N/A')}")
            print(f"   - 이벤트: {result.get('event_description', 'N/A')}")
        else:
            print(f"❌ 세 번째 API 스텝 실패: {third_response.text}")
    except Exception as e:
        print(f"❌ 세 번째 API 호출 오류: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 API 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_api_fixes())
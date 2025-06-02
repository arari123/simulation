#!/usr/bin/env python3
"""
시뮬레이션 환경 지속성 문제 진단 테스트
sim_env 전역 변수가 스텝 간에 유지되는지 확인
"""

import asyncio
import json
from app.routes.simulation import step_simulation_endpoint
from app.simulation_engine import step_simulation
from app.state_manager import sim_env, reset_simulation_state
from app.models import SimulationSetup
import app.state_manager as state_mgr

async def test_sim_env_persistence():
    """시뮬레이션 환경 지속성 테스트"""
    
    print("🧪 시뮬레이션 환경 지속성 진단 시작")
    print("=" * 50)
    
    # 1. 초기 상태 확인
    print(f"1️⃣ 초기 상태:")
    print(f"   - sim_env (import): {sim_env}")
    print(f"   - state_mgr.sim_env: {state_mgr.sim_env}")
    
    # 2. 시뮬레이션 초기화
    print(f"\n2️⃣ 시뮬레이션 초기화...")
    reset_simulation_state()
    print(f"   - 초기화 후 sim_env (import): {sim_env}")
    print(f"   - 초기화 후 state_mgr.sim_env: {state_mgr.sim_env}")
    
    # 3. 테스트 설정 데이터
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
    
    # 4. 첫 번째 스텝 실행 (설정 포함)
    print(f"\n3️⃣ 첫 번째 스텝 실행 (설정 포함)...")
    
    try:
        setup = SimulationSetup(**test_setup_data)
        result1 = await step_simulation(setup)
        
        print(f"   ✅ 첫 번째 스텝 성공")
        print(f"   - 결과 시간: {result1.time}")
        print(f"   - 스텝 후 sim_env (import): {sim_env}")
        print(f"   - 스텝 후 state_mgr.sim_env: {state_mgr.sim_env}")
        print(f"   - 두 참조가 같은지: {sim_env is state_mgr.sim_env}")
        
    except Exception as e:
        print(f"   ❌ 첫 번째 스텝 실패: {e}")
        return
    
    # 5. 두 번째 스텝 실행 (설정 없음)
    print(f"\n4️⃣ 두 번째 스텝 실행 (설정 없음)...")
    
    try:
        result2 = await step_simulation(None)
        
        print(f"   ✅ 두 번째 스텝 성공!")
        print(f"   - 결과 시간: {result2.time}")
        print(f"   - 스텝 후 sim_env (import): {sim_env}")
        print(f"   - 스텝 후 state_mgr.sim_env: {state_mgr.sim_env}")
        
    except Exception as e:
        print(f"   ❌ 두 번째 스텝 실패: {e}")
        print(f"   - 실패 시 sim_env (import): {sim_env}")
        print(f"   - 실패 시 state_mgr.sim_env: {state_mgr.sim_env}")
    
    # 6. API 엔드포인트를 통한 테스트
    print(f"\n5️⃣ API 엔드포인트를 통한 테스트...")
    
    # 먼저 초기화
    reset_simulation_state()
    
    try:
        # 첫 번째 API 호출
        api_result1 = await step_simulation_endpoint(test_setup_data)
        print(f"   ✅ API 첫 번째 스텝 성공")
        print(f"   - API 후 sim_env (import): {sim_env}")
        print(f"   - API 후 state_mgr.sim_env: {state_mgr.sim_env}")
        
        # 두 번째 API 호출
        api_result2 = await step_simulation_endpoint(None)
        print(f"   ✅ API 두 번째 스텝 성공!")
        print(f"   - API 후 sim_env (import): {sim_env}")
        print(f"   - API 후 state_mgr.sim_env: {state_mgr.sim_env}")
        
    except Exception as e:
        print(f"   ❌ API 테스트 실패: {e}")
        print(f"   - API 실패 시 sim_env (import): {sim_env}")
        print(f"   - API 실패 시 state_mgr.sim_env: {state_mgr.sim_env}")
    
    print(f"\n" + "=" * 50)
    print("🎯 진단 완료!")
    
    # 7. 결론
    print(f"\n📊 진단 결과:")
    print(f"   - import된 sim_env와 state_mgr.sim_env 동기화 상태: {'✅' if sim_env is state_mgr.sim_env else '❌'}")
    print(f"   - 현재 시뮬레이션 환경 존재: {'✅' if state_mgr.sim_env is not None else '❌'}")
    
    if sim_env is not state_mgr.sim_env:
        print(f"\n⚠️ 근본 원인: import된 변수와 모듈 변수가 분리되어 있음")
        print(f"   해결책: 모든 참조를 state_manager.sim_env로 통일 필요")

if __name__ == "__main__":
    asyncio.run(test_sim_env_persistence())
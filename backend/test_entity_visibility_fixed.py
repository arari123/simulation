#!/usr/bin/env python3
"""
엔티티 가시성 문제 수정된 테스트
올바른 신호 초기값으로 시뮬레이션을 실행하여 엔티티 가시성 문제를 조사합니다.
"""

import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig, Action, ConnectionPoint
from app.entity import get_active_entity_states

async def test_entity_visibility_with_correct_signals():
    """올바른 신호 설정으로 엔티티 가시성 테스트"""
    
    print("=== 🔍 엔티티 가시성 문제 수정된 테스트 ===")
    print()
    
    # 환경 설정
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    reset_simulation_state()
    
    # 시뮬레이션 설정 생성
    blocks = []
    connections = []
    
    for block_data in data["blocks"]:
        # ConnectionPoint 객체 생성
        connection_points = []
        if "connectionPoints" in block_data:
            for cp_data in block_data["connectionPoints"]:
                actions = []
                if "actions" in cp_data:
                    for action_data in cp_data["actions"]:
                        action = Action(**action_data)
                        actions.append(action)
                
                connection_point = ConnectionPoint(
                    id=cp_data["id"],
                    name=cp_data["name"],
                    x=cp_data.get("x", 0),
                    y=cp_data.get("y", 0),
                    actions=actions
                )
                connection_points.append(connection_point)
        
        # Action 객체 생성
        actions = []
        for action_data in block_data["actions"]:
            action = Action(**action_data)
            actions.append(action)
        
        block = ProcessBlockConfig(
            id=str(block_data["id"]),
            name=block_data["name"],
            actions=actions,
            capacity=block_data.get("maxCapacity"),
            connectionPoints=connection_points
        )
        blocks.append(block)
    
    for conn_data in data["connections"]:
        connection = ConnectionConfig(**conn_data)
        connections.append(connection)
    
    # 🔥 올바른 초기 신호 설정
    initial_signals = {}
    if "globalSignals" in data:
        for signal_data in data["globalSignals"]:
            signal_name = signal_data["name"]
            initial_value = signal_data.get("initialValue", signal_data.get("value", False))
            initial_signals[signal_name] = initial_value
            print(f"📡 신호 '{signal_name}' 초기값: {initial_value}")
    
    setup = SimulationSetup(
        blocks=blocks,
        connections=connections,
        initial_entities=1,
        initial_signals=initial_signals  # 🔥 올바른 신호 초기값 설정
    )
    
    print("\n📋 시뮬레이션 설정:")
    print(f"  - 블록 수: {len(blocks)}")
    print(f"  - 연결 수: {len(connections)}")
    print(f"  - 초기 신호: {initial_signals}")
    print()
    
    # 각 스텝별로 엔티티 상태 추적
    max_steps = 20
    
    for step in range(1, max_steps + 1):
        print(f"=== 📍 스텝 {step} ===")
        
        try:
            # 스텝 실행
            result = await step_simulation(setup if step == 1 else None)
            
            print(f"⏰ 시간: {result.time:.2f}초")
            print(f"📝 이벤트: {result.event_description}")
            print(f"🏭 처리된 엔티티: {result.entities_processed_total}")
            
            # 엔티티 상태 상세 분석
            entity_states = result.active_entities
            print(f"👥 활성 엔티티 수: {len(entity_states)}")
            
            if entity_states:
                print("📊 엔티티 상세 정보:")
                for i, entity in enumerate(entity_states, 1):
                    print(f"  {i}. ID: {entity.id}")
                    print(f"     현재 블록 ID: {entity.current_block_id}")
                    print(f"     현재 블록 이름: {entity.current_block_name}")
                    
                    # 🔍 핵심: 어떤 블록에 있는지 확인
                    if entity.current_block_id == "transit":
                        print(f"     ⚠️  TRANSIT 상태 - 이때 화면에서 사라질 수 있음!")
                    elif entity.current_block_name == "In Transit":
                        print(f"     ⚠️  In Transit 상태 - 이때 화면에서 사라질 수 있음!")
                    else:
                        # 실제 블록에 있는 경우
                        block_name = next((b.name for b in blocks if str(b.id) == str(entity.current_block_id)), "Unknown")
                        print(f"     ✅ 실제 블록 '{block_name}'에 위치")
                        
                        # 🔥 중요: 커넥터 액션 중에도 엔티티가 블록에 위치함을 확인
                        if "waiting" in result.event_description.lower() or "signal" in result.event_description.lower():
                            print(f"     🔍 커넥터 액션 중이지만 블록 '{block_name}'에서 보임 - 정상!")
                    print()
            else:
                print("  📭 활성 엔티티 없음")
            
            # 커넥터 액션 실행 중인지 이벤트 설명으로 판단
            event_desc = result.event_description.lower()
            connector_action_keywords = ["connector", "waiting", "signal", "routed", "moving to same block"]
            
            if any(keyword in event_desc for keyword in connector_action_keywords):
                print("🔍 커넥터 액션 관련 이벤트 감지!")
                print(f"   이벤트: '{result.event_description}'")
                
                if entity_states:
                    for entity in entity_states:
                        if entity.current_block_id == "transit" or entity.current_block_name == "In Transit":
                            print(f"   ⚠️  엔티티 {entity.id}가 transit 상태 - 화면에서 보이지 않을 수 있음!")
                        else:
                            print(f"   ✅ 엔티티 {entity.id}가 블록 {entity.current_block_name}에 정상 위치")
                            print(f"      🎯 이 경우 프론트엔드에서 엔티티가 보여야 함!")
                print()
            
            # 신호 상태
            if result.current_signals:
                print(f"🔔 현재 신호:")
                for signal_name, value in result.current_signals.items():
                    print(f"  - {signal_name}: {value}")
            
            print("-" * 60)
            print()
            
            # 시뮬레이션 완료 체크
            if result.entities_processed_total > 0:
                print(f"🎉 시뮬레이션 완료! 총 {result.entities_processed_total}개 엔티티 처리됨")
                break
                
            if "시뮬레이션 완료" in result.event_description:
                print("🏁 시뮬레이션 종료")
                break
                
        except Exception as e:
            print(f"❌ 스텝 {step} 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n=== 🔍 최종 분석 결과 ===")
    print("엔티티 가시성 문제의 핵심:")
    print("1. 커넥터 액션 실행 중에도 엔티티는 실제 블록(투입, 공정1, 배출)에 위치함")
    print("2. 엔티티가 'transit' 상태가 되는 것은 파이프를 통해 이동할 때만임")
    print("3. 프론트엔드에서 'transit' 상태나 'In Transit' 블록의 엔티티를 표시하지 않는 것으로 보임")
    print("4. 해결책: 프론트엔드에서 모든 블록 ID의 엔티티를 표시하도록 수정")

if __name__ == "__main__":
    asyncio.run(test_entity_visibility_with_correct_signals())
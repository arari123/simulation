#!/usr/bin/env python3
"""
블록 상태 속성 기능 테스트
"""

import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8000"

async def test_block_status():
    """블록 상태 속성 테스트"""
    
    # 테스트 설정 로드
    with open('test_block_status.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    async with aiohttp.ClientSession() as session:
        # 1. 시뮬레이션 리셋
        print("1. 시뮬레이션 리셋...")
        async with session.post(f"{BASE_URL}/simulation/reset") as resp:
            if resp.status != 200:
                print(f"리셋 실패: {await resp.text()}")
                return
        
        # 2. 시뮬레이션 설정
        print("2. 시뮬레이션 설정...")
        async with session.post(f"{BASE_URL}/simulation/setup", json=config) as resp:
            if resp.status != 200:
                print(f"설정 실패: {await resp.text()}")
                return
            result = await resp.json()
            print(f"설정 완료: {result}")
        
        # 3. 시뮬레이션 스텝 실행 및 상태 확인
        print("\n3. 시뮬레이션 스텝 실행...")
        for i in range(20):
            print(f"\n--- 스텝 {i+1} ---")
            
            # 스텝 실행
            async with session.post(f"{BASE_URL}/simulation/step") as resp:
                if resp.status != 200:
                    print(f"스텝 실패: {await resp.text()}")
                    break
                
                result = await resp.json()
                
                # 블록 상태 출력
                if 'block_states' in result:
                    print("블록 상태:")
                    for block_id, block_state in result['block_states'].items():
                        status = block_state.get('status', 'None')
                        name = block_state.get('name', block_id)
                        entities = len(block_state.get('entities', []))
                        print(f"  - {name}: status='{status}', entities={entities}")
                
                # 스크립트 로그 출력
                if 'script_logs' in result and result['script_logs']:
                    print("스크립트 로그:")
                    for log in result['script_logs']:
                        print(f"  [{log['time']:.1f}s] [{log.get('block', '')}] {log['message']}")
                
                # 시뮬레이션 시간
                print(f"시뮬레이션 시간: {result.get('time', 0):.1f}초")
                
            # 잠시 대기
            await asyncio.sleep(0.5)
        
        print("\n테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_block_status())
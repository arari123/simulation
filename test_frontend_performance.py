#!/usr/bin/env python3
"""
프론트엔드 성능 최적화 테스트
백엔드와 프론트엔드 간 API 호출 성능을 비교 측정합니다.
"""

import asyncio
import aiohttp
import time
import json
import statistics

API_BASE = "http://localhost:8000"

async def test_single_step_performance():
    """단일 스텝 API 호출 성능 테스트"""
    print("🚀 단일 스텝 API 성능 테스트")
    print("=" * 50)
    
    # 기본 설정 로드
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/simulation/load-base-config") as response:
            base_config = await response.json()
    
    # 리셋
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/simulation/reset") as response:
            await response.json()
    
    # 단일 스텝 10번 실행하여 평균 시간 측정
    durations = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(10):
            start_time = time.time()
            
            # 첫 번째 스텝에만 설정 데이터 전송
            data = base_config if i == 0 else None
            
            async with session.post(f"{API_BASE}/simulation/step", 
                                  json=data) as response:
                result = await response.json()
                
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # ms로 변환
            durations.append(duration)
            
            print(f"   스텝 {i+1:2d}: {duration:6.2f}ms | Time={result.get('time', 0):4.1f}s | Event='{result.get('event_description', '')[:50]}'")
    
    avg_duration = statistics.mean(durations)
    print(f"\n📊 단일 스텝 API 결과:")
    print(f"   평균 응답 시간: {avg_duration:.2f}ms")
    print(f"   최소 응답 시간: {min(durations):.2f}ms")
    print(f"   최대 응답 시간: {max(durations):.2f}ms")
    
    return avg_duration

async def test_batch_step_performance():
    """배치 스텝 API 호출 성능 테스트"""
    print("\n🚀 배치 스텝 API 성능 테스트")
    print("=" * 50)
    
    # 기본 설정 로드
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/simulation/load-base-config") as response:
            base_config = await response.json()
    
    # 리셋
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/simulation/reset") as response:
            await response.json()
    
    # 배치 크기별 성능 테스트
    batch_sizes = [10, 50, 100]
    
    for batch_size in batch_sizes:
        # 리셋
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_BASE}/simulation/reset") as response:
                await response.json()
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            data = {**base_config, "step_count": batch_size}
            async with session.post(f"{API_BASE}/simulation/batch-step", 
                                  json=data) as response:
                result = await response.json()
                
        end_time = time.time()
        duration = (end_time - start_time) * 1000  # ms로 변환
        
        steps_per_second = batch_size / (duration / 1000) if duration > 0 else 0
        
        print(f"   배치 {batch_size:3d}: {duration:8.2f}ms | {steps_per_second:8.1f} steps/sec | Steps={result.get('steps_executed', 0)}")

async def simulate_frontend_execution():
    """프론트엔드의 전체 실행 패턴 시뮬레이션"""
    print("\n🚀 프론트엔드 전체 실행 시뮬레이션")
    print("=" * 50)
    
    # 기본 설정 로드
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/simulation/load-base-config") as response:
            base_config = await response.json()
    
    # 리셋
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/simulation/reset") as response:
            await response.json()
    
    print("1. 기존 방식 (개별 스텝 + 100ms 대기):")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        for i in range(20):
            data = base_config if i == 0 else None
            
            async with session.post(f"{API_BASE}/simulation/step", 
                                  json=data) as response:
                result = await response.json()
            
            # 프론트엔드의 기존 100ms 대기 시뮬레이션
            await asyncio.sleep(0.1)
    
    duration_old = time.time() - start_time
    steps_per_sec_old = 20 / duration_old
    
    print(f"   20스텝 소요시간: {duration_old:.2f}초")
    print(f"   속도: {steps_per_sec_old:.1f} steps/sec")
    
    # 리셋
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/simulation/reset") as response:
            await response.json()
    
    print("\n2. 최적화된 방식 (개별 스텝 + requestAnimationFrame):")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        for i in range(20):
            data = base_config if i == 0 else None
            
            async with session.post(f"{API_BASE}/simulation/step", 
                                  json=data) as response:
                result = await response.json()
            
            # requestAnimationFrame 시뮬레이션 (약 16ms)
            await asyncio.sleep(0.016)
    
    duration_new = time.time() - start_time
    steps_per_sec_new = 20 / duration_new
    
    print(f"   20스텝 소요시간: {duration_new:.2f}초")
    print(f"   속도: {steps_per_sec_new:.1f} steps/sec")
    
    # 리셋
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/simulation/reset") as response:
            await response.json()
    
    print("\n3. 고속 배치 방식 (50스텝 배치):")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        data = {**base_config, "step_count": 50}
        async with session.post(f"{API_BASE}/simulation/batch-step", 
                              json=data) as response:
            result = await response.json()
    
    duration_batch = time.time() - start_time
    steps_executed = result.get('steps_executed', 50)
    steps_per_sec_batch = steps_executed / duration_batch
    
    print(f"   {steps_executed}스텝 소요시간: {duration_batch:.2f}초")
    print(f"   속도: {steps_per_sec_batch:.1f} steps/sec")
    
    print(f"\n📈 성능 개선 결과:")
    print(f"   기존 → 최적화: {(steps_per_sec_new / steps_per_sec_old - 1) * 100:+.1f}% 개선")
    print(f"   기존 → 배치: {(steps_per_sec_batch / steps_per_sec_old - 1) * 100:+.1f}% 개선")

async def main():
    """메인 테스트 실행"""
    print("🧪 프론트엔드 성능 최적화 테스트")
    print("=" * 60)
    
    try:
        await test_single_step_performance()
        await test_batch_step_performance()
        await simulate_frontend_execution()
        
        print(f"\n✅ 모든 테스트 완료!")
        print("📋 요약:")
        print("   - 100ms → 16ms 대기로 변경하면 약 6배 빨라짐")
        print("   - 배치 처리 사용 시 수십 배 빨라짐")
        print("   - 성능 모니터링 비활성화로 추가 최적화 가능")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        print("   백엔드 서버가 실행 중인지 확인해주세요 (http://localhost:8000)")

if __name__ == "__main__":
    asyncio.run(main())
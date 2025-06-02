#!/usr/bin/env python3
"""
메인 테스트 실행기
통합 시뮬레이션 테스트를 실행하고 결과를 표시합니다.
"""

import asyncio
import sys
from test_unified_simulation import UnifiedSimulationTester

async def main():
    """메인 테스트 실행"""
    print("🚀 통합 시뮬레이션 테스트 시작")
    print("=" * 60)
    
    tester = UnifiedSimulationTester()
    results = await tester.run_all_tests()
    
    print("\n" + "=" * 60)
    if results["success"]:
        print("🎉 모든 테스트 성공!")
        print(f"✅ {results['passed_tests']}/{results['total_tests']} 테스트 통과")
        print(f"⚡ 실행 시간: {results['duration']:.2f}초")
        exit_code = 0
    else:
        print("❌ 일부 테스트 실패")
        print(f"❌ {results['failed_tests']}/{results['total_tests']} 테스트 실패")
        print(f"⚠️ 시뮬레이션 엔진을 수정하세요")
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
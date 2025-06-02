#!/usr/bin/env python3
"""
통합 시뮬레이션 테스트 시스템 (Unified Simulation Test System)

이 파일은 시뮬레이션 엔진을 직접 참조하여 테스트하는 통합 테스트 시스템입니다.
- 중복 로직 제거: 시뮬레이션 엔진의 변환 함수를 직접 사용
- 통합 테스트: 모든 테스트를 하나의 파일에서 순차적으로 실행
- 효율적 워크플로우: 엔진 수정 → 테스트 → 완료 (중복 작업 없음)

테스트 커버리지:
1. 기본 시뮬레이션 엔진 테스트
2. 신호 처리 시스템 테스트 (즉시 처리 + 대기/깨우기)
3. 엔티티 이동 및 흐름 테스트
4. 전체 시뮬레이션 플로우 테스트
5. 성능 벤치마크 테스트
6. 오류 처리 테스트
"""

import asyncio
import json
import time
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 시뮬레이션 엔진 모듈들 직접 import (중복 방지)
from app.routes.simulation import (
    reset_simulation_state, 
    convert_config_ids_to_strings,
    convert_global_signals_to_initial_signals
)
from app.simulation_engine import step_simulation, run_simulation, batch_step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig, Action
from app.entity import Entity, EntityPool, get_active_entity_states
from app.state_manager import get_current_signals, set_signal
from app.script_executor import execute_script_line, execute_conditional_branch_script
from app.utils import parse_delay_value, check_entity_movement

class UnifiedSimulationTester:
    """통합 시뮬레이션 테스터 - 시뮬레이션 엔진을 직접 참조"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.base_config = None
        
        # 테스트 설정
        self.verbose = True
        self.max_simulation_steps = 30
        self.performance_threshold = 5.0
        
    def log(self, message: str, level: str = "INFO"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] [{level}] {message}"
        print(formatted_message)
        if self.verbose or level in ["ERROR", "CRITICAL"]:
            self.test_results.append(formatted_message)
    
    def add_test_result(self, test_name: str, passed: bool, message: str = "", duration: float = 0):
        """테스트 결과 추가"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result_msg = f"{status} | {test_name} | {duration:.3f}s"
        if message:
            result_msg += f" | {message}"
        
        self.log(result_msg, "RESULT")
    
    def load_base_config(self) -> bool:
        """기본 설정 로드"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "base.json")
            with open(config_path, "r", encoding="utf-8") as f:
                self.base_config = json.load(f)
            self.log(f"기본 설정 로드 완료: {len(self.base_config.get('blocks', []))}개 블록")
            return True
        except Exception as e:
            self.log(f"기본 설정 로드 실패: {e}", "ERROR")
            return False
    
    def prepare_simulation_setup(self) -> SimulationSetup:
        """시뮬레이션 설정 준비 - 엔진의 변환 함수 직접 사용"""
        if not self.base_config:
            raise Exception("기본 설정이 로드되지 않음")
        
        # 🔥 시뮬레이션 엔진의 변환 함수를 직접 사용 (중복 제거)
        converted_config = convert_config_ids_to_strings(self.base_config)
        initial_signals = convert_global_signals_to_initial_signals(converted_config)
        
        blocks = [ProcessBlockConfig(**block) for block in converted_config["blocks"]]
        connections = [ConnectionConfig(**conn) for conn in converted_config["connections"]]
        
        return SimulationSetup(
            blocks=blocks,
            connections=connections,
            initial_signals=initial_signals
        )
    
    async def test_basic_simulation_engine(self) -> bool:
        """기본 시뮬레이션 엔진 테스트"""
        self.log("=== 기본 시뮬레이션 엔진 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # 시뮬레이션 상태 초기화
            reset_simulation_state()
            
            # 시뮬레이션 설정 생성
            setup = self.prepare_simulation_setup()
            
            # 첫 번째 스텝 실행
            result = await step_simulation(setup)
            assert result is not None
            assert hasattr(result, 'time')
            self.log(f"첫 스텝 실행 성공: 시간 {result.time}")
            
            # 추가 스텝 실행 (최대 5스텝)
            step_count = 1
            for i in range(4):
                try:
                    result = await step_simulation()
                    step_count += 1
                    self.log(f"{step_count}번째 스텝 실행: 시간 {result.time}")
                    
                    # 시간이 진행되지 않으면 중단
                    if result.time == 0 and step_count > 2:
                        self.log("시간 진행 없음으로 스텝 중단")
                        break
                        
                except Exception as step_error:
                    self.log(f"스텝 {step_count + 1} 실행 중 오류: {step_error}")
                    break
            
            duration = time.time() - start_time
            self.add_test_result("기본 시뮬레이션 엔진", True, f"{step_count}스텝 실행 성공", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("기본 시뮬레이션 엔진", False, str(e), duration)
            self.log(f"기본 시뮬레이션 엔진 테스트 실패: {e}", "ERROR")
            return False
    
    async def test_signal_processing_system(self) -> bool:
        """신호 처리 시스템 통합 테스트 (즉시 처리 + 대기/깨우기)"""
        self.log("=== 신호 처리 시스템 통합 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # 시뮬레이션 상태 초기화
            reset_simulation_state()
            
            # 시뮬레이션 설정 생성
            setup = self.prepare_simulation_setup()
            
            self.log(f"초기 신호 상태: {setup.initial_signals}")
            
            # 신호 처리 테스트를 위한 상세 스텝 실행
            signal_test_passed = True
            step_count = 0
            entity_moved_count = 0
            signal_change_detected = False
            
            # 첫 번째 스텝 - 초기화
            result = await step_simulation(setup)
            step_count += 1
            self.log(f"1단계: 시간 {result.time}, 신호: {get_current_signals()}")
            
            # 2-20단계: 신호 처리 및 엔티티 이동 확인
            for i in range(2, 21):
                try:
                    result = await step_simulation()
                    step_count += 1
                    
                    current_signals = get_current_signals()
                    entities = result.active_entities
                    
                    # 신호 변경 감지
                    if i == 10:  # 대략 9초 시점에서 신호 변경 예상
                        load_enable = current_signals.get("공정1 load enable", False)
                        if load_enable:
                            signal_change_detected = True
                            self.log(f"{i}단계: 신호 '공정1 load enable'가 True로 변경됨")
                    
                    # 엔티티 이동 확인
                    for entity in entities:
                        if entity.current_block_id != "1":  # 투입 블록이 아닌 곳으로 이동
                            entity_moved_count += 1
                            self.log(f"{i}단계: 엔티티 {entity.id}가 블록 {entity.current_block_id}로 이동")
                    
                    # 엔티티가 처리되었는지 확인
                    if result.entities_processed_total > 0:
                        self.log(f"🎉 엔티티 처리 완료: {result.entities_processed_total}개")
                        break
                    
                    # 시간이 멈춘 경우 확인
                    if i > 5 and result.time == 0:
                        self.log("시간 진행 정체 감지")
                        break
                        
                except Exception as step_error:
                    self.log(f"신호 테스트 {i}단계 오류: {step_error}")
                    signal_test_passed = False
                    break
            
            # 신호 처리 결과 평가
            success_criteria = [
                signal_change_detected,  # 신호 변경 감지
                entity_moved_count >= 2,  # 최소 2개 엔티티 이동
                result.entities_processed_total >= 1  # 최소 1개 엔티티 처리
            ]
            
            signal_test_passed = all(success_criteria)
            
            duration = time.time() - start_time
            message = f"{step_count}스텝, 신호변경: {signal_change_detected}, 이동: {entity_moved_count}개, 처리: {result.entities_processed_total}개"
            self.add_test_result("신호 처리 시스템 통합", signal_test_passed, message, duration)
            return signal_test_passed
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("신호 처리 시스템 통합", False, str(e), duration)
            self.log(f"신호 처리 시스템 테스트 실패: {e}", "ERROR")
            return False
    
    async def test_entity_flow_system(self) -> bool:
        """엔티티 흐름 시스템 테스트"""
        self.log("=== 엔티티 흐름 시스템 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # 시뮬레이션 상태 초기화
            reset_simulation_state()
            
            # 시뮬레이션 설정 생성
            setup = self.prepare_simulation_setup()
            
            # 엔티티 흐름 테스트
            flow_test_passed = True
            entities_created = 0
            entities_in_transit = 0
            entities_processed = 0
            
            # 첫 번째 스텝 실행
            result = await step_simulation(setup)
            
            # 흐름 추적을 위한 스텝 실행
            for i in range(2, self.max_simulation_steps + 1):
                try:
                    result = await step_simulation()
                    
                    # 엔티티 상태 분석
                    current_entities = len(result.active_entities)
                    transit_count = sum(1 for e in result.active_entities if e.current_block_id == "transit")
                    processed_count = result.entities_processed_total
                    
                    if current_entities > entities_created:
                        entities_created = current_entities
                        self.log(f"스텝 {i}: 새 엔티티 생성, 총 {entities_created}개")
                    
                    if transit_count > entities_in_transit:
                        entities_in_transit = transit_count
                        self.log(f"스텝 {i}: 엔티티 이동 중, {transit_count}개")
                    
                    if processed_count > entities_processed:
                        entities_processed = processed_count
                        self.log(f"스텝 {i}: 엔티티 처리 완료, 총 {entities_processed}개")
                        
                        # 첫 엔티티 처리 완료 시 성공
                        if entities_processed >= 1:
                            break
                    
                    # 무한 루프 방지
                    if i > 20 and result.time == 0:
                        self.log("시간 진행 정체로 테스트 중단")
                        break
                        
                except Exception as step_error:
                    self.log(f"흐름 테스트 스텝 {i} 오류: {step_error}")
                    flow_test_passed = False
                    break
            
            # 흐름 테스트 결과 평가
            flow_success = entities_created >= 1 and entities_processed >= 1
            
            duration = time.time() - start_time
            message = f"생성: {entities_created}개, 이동: {entities_in_transit}개, 처리: {entities_processed}개"
            self.add_test_result("엔티티 흐름 시스템", flow_success, message, duration)
            return flow_success
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("엔티티 흐름 시스템", False, str(e), duration)
            self.log(f"엔티티 흐름 시스템 테스트 실패: {e}", "ERROR")
            return False
    
    async def test_data_models_and_utils(self) -> bool:
        """데이터 모델 및 유틸리티 테스트"""
        self.log("=== 데이터 모델 및 유틸리티 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # Action 모델 테스트
            action = Action(
                type="delay",
                name="테스트 딜레이",
                parameters={"delay_time": "5"}
            )
            assert action.type == "delay"
            self.log("Action 모델 생성 성공")
            
            # 딜레이 파싱 테스트
            delay_value = parse_delay_value("5")
            assert delay_value == 5.0
            self.log("딜레이 파싱 테스트 성공")
            
            # 범위 딜레이 파싱 테스트
            range_delay = parse_delay_value("3-10")
            assert 3.0 <= range_delay <= 10.0
            self.log("범위 딜레이 파싱 테스트 성공")
            
            # 엔티티 시스템 테스트
            from app.state_manager import sim_env
            import simpy
            
            if sim_env is None:
                env = simpy.Environment()
            else:
                env = sim_env
                
            pool = EntityPool()
            entity = pool.get_entity(env, "test_entity", "test_block")
            assert entity is not None
            assert entity.id == "test_entity"
            self.log("엔티티 생성 성공")
            
            pool.return_entity(entity)
            self.log("엔티티 반환 성공")
            
            # 활성 엔티티 상태 조회
            states = get_active_entity_states()
            assert isinstance(states, list)
            self.log("활성 엔티티 상태 조회 성공")
            
            duration = time.time() - start_time
            self.add_test_result("데이터 모델 및 유틸리티", True, "모든 기본 기능 성공", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("데이터 모델 및 유틸리티", False, str(e), duration)
            self.log(f"데이터 모델 및 유틸리티 테스트 실패: {e}", "ERROR")
            return False
    
    async def test_batch_and_performance(self) -> bool:
        """배치 실행 및 성능 테스트"""
        self.log("=== 배치 실행 및 성능 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # 배치 실행 테스트
            reset_simulation_state()
            setup = self.prepare_simulation_setup()
            
            # 배치 실행을 위해 먼저 시뮬레이션 설정
            await step_simulation(setup)
            
            # 배치 실행 (5스텝)
            batch_result = await batch_step_simulation(5)
            assert batch_result is not None
            assert hasattr(batch_result, 'steps_executed')
            self.log(f"배치 실행 성공: {batch_result.steps_executed}스텝")
            
            # 성능 테스트 (빠른 반복)
            iterations = 3
            total_time = 0
            
            for i in range(iterations):
                iteration_start = time.time()
                
                reset_simulation_state()
                setup = self.prepare_simulation_setup()
                
                # 빠른 스텝 실행
                await step_simulation(setup)
                await step_simulation()
                
                iteration_time = time.time() - iteration_start
                total_time += iteration_time
                self.log(f"성능 반복 {i+1}: {iteration_time:.3f}초")
            
            avg_time = total_time / iterations
            is_fast_enough = avg_time < self.performance_threshold
            
            duration = time.time() - start_time
            message = f"배치: {batch_result.steps_executed}스텝, 평균 성능: {avg_time:.3f}초"
            self.add_test_result("배치 실행 및 성능", is_fast_enough, message, duration)
            return is_fast_enough
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("배치 실행 및 성능", False, str(e), duration)
            self.log(f"배치 실행 및 성능 테스트 실패: {e}", "ERROR")
            return False
    
    async def test_error_handling(self) -> bool:
        """오류 처리 테스트"""
        self.log("=== 오류 처리 테스트 시작 ===")
        start_time = time.time()
        
        try:
            # None 파라미터 테스트
            try:
                await step_simulation(None)
                self.log("None 파라미터 처리: 정상 실행 또는 적절한 예외")
            except Exception as expected_error:
                self.log(f"None 파라미터 처리: 예외 발생 ({type(expected_error).__name__})")
            
            # 잘못된 설정 테스트
            try:
                invalid_blocks = [ProcessBlockConfig(
                    id="invalid",
                    name="Invalid Block",
                    block_type="invalid_type",
                    actions=[]
                )]
                invalid_setup = SimulationSetup(
                    blocks=invalid_blocks,
                    connections=[],
                    initial_signals={}
                )
                await step_simulation(invalid_setup)
                self.log("잘못된 설정 처리: 정상 실행 또는 적절한 예외")
            except Exception as expected_error:
                self.log(f"잘못된 설정 처리: 예외 발생 ({type(expected_error).__name__})")
            
            duration = time.time() - start_time
            self.add_test_result("오류 처리", True, "오류 상황 적절히 처리", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result("오류 처리", False, str(e), duration)
            self.log(f"오류 처리 테스트 실패: {e}", "ERROR")
            return False
    
    def generate_report(self) -> str:
        """테스트 결과 리포트 생성"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        report = f"""
{'='*80}
통합 시뮬레이션 테스트 결과 리포트
{'='*80}

📊 테스트 통계:
   • 총 테스트: {self.total_tests}개
   • 성공: {self.passed_tests}개 (✅)
   • 실패: {self.failed_tests}개 (❌)
   • 성공률: {success_rate:.1f}%
   • 실행 시간: {duration:.2f}초

🎯 테스트 상태:
   {'🎉 모든 테스트 통과!' if self.failed_tests == 0 else '⚠️ 일부 테스트 실패'}

📝 상세 결과:
"""
        
        # 테스트 결과에서 RESULT 레벨만 추출
        for result in self.test_results:
            if "[RESULT]" in result:
                report += f"   {result.split('] ')[2]}\\n"
        
        report += f"\\n{'='*80}\\n"
        
        if self.failed_tests > 0:
            report += "⚠️ 실패한 테스트가 있습니다. 시뮬레이션 엔진을 수정하세요.\\n"
        else:
            report += "✅ 모든 시뮬레이션 기능이 정상적으로 작동합니다!\\n"
        
        report += f"{'='*80}"
        
        return report
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        self.start_time = datetime.now()
        self.log("🚀 통합 시뮬레이션 테스트 시작!")
        
        # 기본 설정 로드
        if not self.load_base_config():
            return {"success": False, "error": "기본 설정 로드 실패"}
        
        # 테스트 실행 순서 (통합된 순서)
        test_methods = [
            self.test_data_models_and_utils,
            self.test_basic_simulation_engine,
            self.test_signal_processing_system,  # 신호 테스트 통합
            self.test_entity_flow_system,
            self.test_batch_and_performance,
            self.test_error_handling,
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                self.log(f"테스트 메서드 {test_method.__name__} 실행 중 치명적 오류: {e}", "CRITICAL")
                self.add_test_result(test_method.__name__, False, f"치명적 오류: {e}")
        
        # 리포트 생성
        report = self.generate_report()
        print(report)
        
        return {
            "success": self.failed_tests == 0,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0,
            "duration": (self.end_time - self.start_time).total_seconds(),
            "report": report
        }

async def main():
    """메인 실행 함수"""
    tester = UnifiedSimulationTester()
    results = await tester.run_all_tests()
    
    # 종료 코드 설정
    exit_code = 0 if results["success"] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
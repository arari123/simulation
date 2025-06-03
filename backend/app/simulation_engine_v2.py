"""
리팩토링된 시뮬레이션 엔진
모듈화되고 동적인 시뮬레이션을 지원합니다.
"""
import simpy
import logging
from typing import Optional, Dict, List, Any

from .models import (
    ProcessBlockConfig, ConnectionConfig, SimulationSetup,
    SimulationStepResult, SimulationRunResult, BatchStepResult
)
from .core.constants import ActionType, DEBUG_MODE, PERFORMANCE_MODE, MONITORING_MODE
from .core.entity_manager import EntityManager
from .core.signal_manager import SignalManager
from .core.pipe_manager import PipeManager
from .core.source_manager import SourceManager
from .core.action_executor import ActionExecutor
from .core.block_processor import BlockProcessor
from .core.monitoring import simulation_monitor

logger = logging.getLogger(__name__)

class SimulationEngine:
    """리팩토링된 시뮬레이션 엔진"""
    
    def __init__(self):
        # 매니저 초기화
        self.entity_manager = EntityManager()
        self.signal_manager = SignalManager()
        self.pipe_manager = PipeManager()
        self.source_manager = SourceManager()
        
        # 실행기 초기화
        self.action_executor = ActionExecutor(
            self.entity_manager, self.signal_manager, self.pipe_manager
        )
        
        # 프로세서 초기화
        self.block_processor = BlockProcessor(
            self.entity_manager, self.signal_manager, 
            self.pipe_manager, self.source_manager, self.action_executor
        )
        
        # 시뮬레이션 상태
        self.sim_env: Optional[simpy.Environment] = None
        self.sim_log: List[Dict] = []
        self.processed_entities_count = 0
        self.step_count = 0
        
        # 캐시
        self._cached_setup: Optional[SimulationSetup] = None
        self._entity_states_cache = None
        self._entity_states_dirty = True
        
    def reset(self):
        """시뮬레이션을 초기화합니다."""
        self.sim_env = None
        self.sim_log.clear()
        self.processed_entities_count = 0
        self.step_count = 0
        
        # 매니저들 초기화
        self.signal_manager.reset()
        self.pipe_manager.reset()
        self.source_manager.reset()
        self.block_processor.reset()
        
        # 캐시 초기화
        self._cached_setup = None
        self._entity_states_cache = None
        self._entity_states_dirty = True
        
        # 엔티티 레지스트리 초기화
        from .entity import entity_pool, active_entities_registry
        entity_pool.reset()
        active_entities_registry.clear()
        
    async def setup_simulation(self, setup: SimulationSetup):
        """시뮬레이션을 설정합니다."""
        logger.info(f"[SETUP] Setting up simulation with {len(setup.blocks)} blocks")
        if DEBUG_MODE:
            logger.debug(f"Setting up simulation with {len(setup.blocks)} blocks")
            for block in setup.blocks:
                logger.debug(f"  - Block: {block.name}({block.id})")
        self.sim_env = simpy.Environment()
        
        # 초기 신호 설정
        if setup.initial_signals:
            if DEBUG_MODE:
                logger.debug(f"Initializing signals: {setup.initial_signals}")
            self.signal_manager.initialize_signals(setup.initial_signals, self.sim_env)
            
        # 파이프 생성
        if DEBUG_MODE:
            logger.debug(f"Creating {len(setup.connections)} connections")
        self.pipe_manager.create_pipes(setup.connections, setup.blocks, self.sim_env)
        
        # 소스 블록 등록
        for block in setup.blocks:
            in_pipes = self.pipe_manager.get_input_pipes(str(block.id))
            has_custom_sink = any(action.type == ActionType.CUSTOM_SINK for action in block.actions)
            
            if DEBUG_MODE:
                logger.debug(f"Block {block.name}({block.id}): in_pipes={len(in_pipes)}, has_custom_sink={has_custom_sink}")
            
            # 입력 파이프가 없으면 소스 블록
            if not in_pipes:
                # 소스 블록으로 등록
                generation_condition = self._extract_generation_condition(block)
                if DEBUG_MODE:
                    logger.debug(f"Registering {block.name}({block.id}) as source block with condition: {generation_condition}")
                self.source_manager.register_source_block(
                    block.id, self.sim_env, condition=generation_condition
                )
                
        # 블록 프로세스 시작
        if DEBUG_MODE:
            logger.debug(f"Starting block processes")
        for block in setup.blocks:
            try:
                process = self.block_processor.create_block_process(self.sim_env, block)
                self.sim_env.process(process)
                if DEBUG_MODE:
                    logger.debug(f"Started process for {block.name}({block.id})")
            except Exception as e:
                logger.error(f"Failed to start process for {block.name}({block.id}): {e}")
                import traceback
                logger.error(traceback.format_exc())
            
        # 초기 이벤트 트리거
        if DEBUG_MODE:
            logger.debug(f"Triggering initial events for source blocks")
        self.source_manager.trigger_initial_events(self.sim_env)
        
        # 첫 스텝 실행
        if DEBUG_MODE:
            logger.debug(f"Executing first step")
            logger.debug(f"Event queue before first step: {len(self.sim_env._queue)} events")
        try:
            self.sim_env.step()
            if DEBUG_MODE:
                logger.debug(f"First step completed, current time: {self.sim_env.now}")
                logger.debug(f"Event queue after first step: {len(self.sim_env._queue)} events")
        except simpy.core.EmptySchedule:
            if DEBUG_MODE:
                logger.debug(f"Empty schedule after first step")
            pass
            
    def _extract_generation_condition(self, block: ProcessBlockConfig) -> Optional[Dict[str, Any]]:
        """블록에서 생성 조건을 추출합니다."""
        # 블록의 액션에서 신호 대기 조건 찾기
        for action in block.actions:
            if action.type == ActionType.SIGNAL_WAIT:
                signal_name = action.parameters.get("signal_name")
                expected_value = action.parameters.get("expected_value", True)
                if signal_name:
                    return {
                        "signal_name": signal_name,
                        "expected_value": expected_value
                    }
                    
        # 소스 블록의 기본 생성 조건 찾기
        if hasattr(block, 'generation_condition'):
            return block.generation_condition
            
        return None
        
    async def run_simulation(self, setup: SimulationSetup) -> SimulationRunResult:
        """전체 시뮬레이션을 실행합니다."""
        self.reset()
        await self.setup_simulation(setup)
        
        # 엔티티 수 모니터링 프로세스
        if setup.stop_entities_processed:
            def entity_count_monitor(env, target_count):
                while True:
                    if self.block_processor.processed_entities_count >= target_count:
                        break
                    yield env.timeout(0.1)
                    
            self.sim_env.process(entity_count_monitor(self.sim_env, setup.stop_entities_processed))
            
        # 시뮬레이션 실행
        try:
            if setup.stop_time:
                self.sim_env.run(until=setup.stop_time)
            else:
                self.sim_env.run()
        except Exception as e:
            if not PERFORMANCE_MODE:
                logger.error(f"Simulation ended with exception: {e}")
                
        # 결과 반환
        return SimulationRunResult(
            message=f"Simulation completed. Processed {self.block_processor.processed_entities_count} "
                   f"entities at time {self.sim_env.now:.2f}",
            log=self.block_processor.sim_log,
            total_entities_processed=self.block_processor.processed_entities_count,
            final_time=self.sim_env.now,
            active_entities=self.entity_manager.get_active_entities()
        )
        
    async def step_simulation(self, setup: Optional[SimulationSetup] = None) -> SimulationStepResult:
        """단일 스텝을 실행합니다."""
        if DEBUG_MODE:
            logger.debug(f"[DEBUG-STEP] step_simulation called, setup provided: {setup is not None}")
        try:
            # 설정이 변경되었는지 확인
            if setup is not None and setup != self._cached_setup:
                if DEBUG_MODE:
                    logger.debug(f"[DEBUG-STEP] New setup detected, reinitializing simulation")
                if DEBUG_MODE:
                    logger.debug("[INIT] 새로운 시뮬레이션 설정으로 환경 재생성")
                    
                self.reset()
                await self.setup_simulation(setup)
                self._cached_setup = setup
                self._entity_states_dirty = True
                
            if self.sim_env is None:
                logger.error(f"ERROR: sim_env is None!")
                raise RuntimeError("시뮬레이션 환경이 초기화되지 않았습니다.")
                
            current_time = self.sim_env.now
            if DEBUG_MODE:
                logger.debug(f"[DEBUG-STEP] Current simulation time: {current_time}")
            
            # 스케줄 확인
            queue_length = len(self.sim_env._queue)
            if DEBUG_MODE:
                logger.debug(f"[DEBUG-STEP] Event queue length: {queue_length}")
                logger.debug(f"[DEBUG-STEP] Active entities: {len(self.entity_manager.get_active_entities())}")
                logger.debug(f"[DEBUG-STEP] Processed entities: {self.block_processor.processed_entities_count}")
                # 큐의 이벤트들 확인
                if queue_length > 0:
                    events_info = []
                    for _, _, _, proc in self.sim_env._queue:
                        proc_name = getattr(proc, '__name__', str(proc))
                        events_info.append(proc_name)
                    logger.debug(f"[DEBUG-STEP] Events in queue: {events_info[:5]}")
            
            # 투입 블록이 없으면 강제로 추가 (한 번만 실행)
            if queue_length == 2 and len(self.entity_manager.get_active_entities()) == 0 and not hasattr(self, '_source_forced'):
                logger.warning("[DEBUG-STEP] Only 2 timeout events in queue, no source block. Forcing source block creation.")
                # 투입 블록 찾기
                if self._cached_setup and self._cached_setup.blocks:
                    for block in self._cached_setup.blocks:
                        if block.name == "투입" or (not self.pipe_manager.get_input_pipes(str(block.id))):
                            logger.info(f"[DEBUG-STEP] Creating process for source block: {block.name}")
                            process = self.block_processor.create_block_process(self.sim_env, block)
                            self.sim_env.process(process)
                            # 소스 블록 등록
                            if not self.source_manager.is_source_block(str(block.id)):
                                self.source_manager.register_source_block(
                                    block.id, self.sim_env, condition=None
                                )
                            # 초기 이벤트 트리거
                            self.source_manager.trigger_request_event(str(block.id), self.sim_env)
                            self._source_forced = True
                            break
            
            if queue_length == 0:
                if DEBUG_MODE:
                    logger.debug(f"[DEBUG-STEP] Queue is empty, simulation complete")
                return SimulationStepResult(
                    time=current_time,
                    event_description="시뮬레이션 완료",
                    active_entities=[],
                    entities_processed_total=self.block_processor.processed_entities_count,
                    current_signals=self.signal_manager.get_all_signals()
                )
                
            # 상태 저장
            initial_time = self.sim_env.now
            initial_entity_count = len(self.entity_manager.get_active_entities())
            initial_processed = self.block_processor.processed_entities_count
            
            # 엔티티 위치 저장
            initial_entity_states = {}
            for entity_state in self.entity_manager.get_active_entities():
                # EntityState 객체는 속성으로 접근
                initial_entity_states[entity_state.id] = entity_state.current_block_id
                
            # 스텝 실행 - go to 액션(엔티티 이동)이 발생할 때까지 계속 실행
            entity_moved = False
            step_count = 0
            max_steps = 1000  # 무한루프 방지
            
            while len(self.sim_env._queue) > 0 and not entity_moved and step_count < max_steps:
                step_count += 1
                
                # 이전 엔티티 위치 저장
                pre_step_entity_states = {e.id: e.current_block_id for e in self.entity_manager.get_active_entities()}
                pre_step_processed = self.block_processor.processed_entities_count
                
                # 단일 이벤트 실행
                self.sim_env.step()
                
                # 이동 감지: 엔티티 위치 변화 또는 처리된 엔티티 수 증가
                current_entity_states = {e.id: e.current_block_id for e in self.entity_manager.get_active_entities()}
                current_processed = self.block_processor.processed_entities_count
                
                # 엔티티 위치가 변경되었거나 처리된 엔티티가 증가했다면 이동으로 간주
                if (current_entity_states != pre_step_entity_states or 
                    current_processed > pre_step_processed):
                    entity_moved = True
                    if DEBUG_MODE:
                        logger.debug(f"[DEBUG-STEP] Entity movement detected after {step_count} sub-steps")
                    break
                    
            new_time = self.sim_env.now
            
            # 변화 감지
            time_changed = (new_time != initial_time)
            entity_count_changed = (len(self.entity_manager.get_active_entities()) != initial_entity_count)
            processed_changed = (self.block_processor.processed_entities_count != initial_processed)
            
            # 최종 엔티티 상태
            current_entity_states = {e.id: e.current_block_id for e in self.entity_manager.get_active_entities()}
            for entity_id, old_location in initial_entity_states.items():
                if entity_id in current_entity_states and current_entity_states[entity_id] != old_location:
                    entity_moved = True
                    break
                    
            # 이벤트 설명 생성
            if processed_changed:
                event_desc = f"엔티티 처리 완료 (총 {self.block_processor.processed_entities_count}개)"
            elif entity_moved:
                event_desc = "엔티티 이동 감지"
            elif time_changed:
                event_desc = f"시간 진행: {round(initial_time, 2)}s → {round(new_time, 2)}s"
            elif entity_count_changed:
                event_desc = f"엔티티 수 변화: {initial_entity_count} → {len(self.entity_manager.get_active_entities())}"
            else:
                event_desc = f"시뮬레이션 이벤트 처리 (시간: {round(new_time, 2)}s)"
                
            self._entity_states_dirty = True
            
            # 엔티티 상태 캐싱
            if self._entity_states_dirty:
                self._entity_states_cache = self.entity_manager.get_active_entities()
                self._entity_states_dirty = False
            
            # 모니터링 로깅
            self.step_count += 1
            if MONITORING_MODE:
                simulation_monitor.log_simulation_state(
                    step_num=self.step_count,
                    sim_time=new_time,
                    event_queue_size=queue_length,
                    active_entities=self._entity_states_cache,
                    processed_count=self.block_processor.processed_entities_count,
                    signals=self.signal_manager.get_all_signals(),
                    current_event=event_desc
                )
                
            return SimulationStepResult(
                time=round(new_time, 2),
                event_description=event_desc,
                active_entities=self._entity_states_cache,
                entities_processed_total=self.block_processor.processed_entities_count,
                current_signals=self.signal_manager.get_all_signals()
            )
            
        except Exception as e:
            logger.error(f"스텝 실행 중 오류: {e}")
            return SimulationStepResult(
                time=round(self.sim_env.now if self.sim_env else 0, 2),
                event_description=f"오류: {str(e)}",
                active_entities=[],
                entities_processed_total=self.block_processor.processed_entities_count,
                current_signals=self.signal_manager.get_all_signals()
            )
            
    async def batch_step_simulation(self, steps: int) -> BatchStepResult:
        """여러 스텝을 연속으로 실행합니다."""
        if not self.sim_env:
            raise ValueError("시뮬레이션이 초기화되지 않았습니다.")
            
        initial_log_count = len(self.block_processor.sim_log)
        executed_steps = 0
        
        for i in range(steps):
            try:
                self.sim_env.step()
                executed_steps += 1
            except simpy.core.EmptySchedule:
                break
                
        # 최종 이벤트 설명
        final_description = "배치 실행 완료"
        if self.block_processor.sim_log:
            last_log = self.block_processor.sim_log[-1]
            final_description = last_log.get('event', final_description)
            
        return BatchStepResult(
            message=f"{executed_steps} 스텝 실행 완료",
            steps_executed=executed_steps,
            final_event_description=final_description,
            log=self.block_processor.sim_log[initial_log_count:],
            current_time=self.sim_env.now,
            active_entities=self.entity_manager.get_active_entities(),
            total_entities_processed=self.block_processor.processed_entities_count
        )

# 글로벌 엔진 인스턴스
_simulation_engine = SimulationEngine()

# 기존 인터페이스와의 호환성을 위한 함수들
async def run_simulation(setup: SimulationSetup) -> SimulationRunResult:
    """전체 시뮬레이션을 실행합니다."""
    return await _simulation_engine.run_simulation(setup)
    
async def step_simulation(setup: Optional[SimulationSetup] = None) -> SimulationStepResult:
    """단일 스텝을 실행합니다."""
    return await _simulation_engine.step_simulation(setup)
    
async def batch_step_simulation(steps: int) -> BatchStepResult:
    """여러 스텝을 연속으로 실행합니다."""
    return await _simulation_engine.batch_step_simulation(steps)
    
def reset_simulation():
    """시뮬레이션을 초기화합니다."""
    _simulation_engine.reset()
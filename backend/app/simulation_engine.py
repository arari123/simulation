import simpy
import random
import logging
from typing import Optional, Dict, List, Any

from .models import (
    ProcessBlockConfig, ConnectionConfig, SimulationSetup,
    SimulationStepResult, SimulationRunResult, BatchStepResult
)
from . import state_manager
from .state_manager import (
    sim_log, block_pipes, signals, 
    reset_simulation_state, processed_entities_count, block_entity_counts,
    source_entity_request_events, source_entity_generated_counts, source_entity_total_limits,
    set_signal, get_current_signals, wait_for_signal
)
from .entity import Entity, entity_pool, active_entities_registry, get_active_entity_states, get_block_entity_count
from .script_executor import execute_script_line, execute_conditional_branch_script
from .utils import parse_delay_value, get_latest_movement_description

# 🚀 Performance optimization: Configure logging
logger = logging.getLogger(__name__)

# 🚀 Performance optimization: Cache for simulation setup
_cached_simulation_setup = None
_entity_states_cache = None
_entity_states_dirty = True

# 🚀 Performance optimization: Debugging control
DEBUG_MODE = False  # Set to True for detailed debugging
PERFORMANCE_MODE = True  # Set to False to enable all logging for debugging

async def run_simulation(setup: SimulationSetup) -> SimulationRunResult:
    """전체 시뮬레이션을 실행합니다."""
    global sim_log, processed_entities_count
    
    # 시뮬레이션 초기화
    reset_simulation_state()
    
    state_manager.sim_env = simpy.Environment()
    processed_entities_count = 0
    
    # 초기 신호 설정
    if setup.initial_signals:
        for signal_name, value in setup.initial_signals.items():
            set_signal(signal_name, value, state_manager.sim_env)
    
    # 파이프 생성
    for conn in setup.connections:
        pipe_id = f"{conn.from_block_id}_{conn.from_connector_id}_to_{conn.to_block_id}_{conn.to_connector_id}"
        block_pipes[pipe_id] = simpy.Store(state_manager.sim_env)
    
    # 블록별 입출력 파이프 매핑
    in_pipes_map = {}
    out_pipes_map = {}
    
    for block in setup.blocks:
        in_pipes_map[block.id] = []
        out_pipes_map[block.id] = {}
    
    for conn in setup.connections:
        pipe_id = f"{conn.from_block_id}_{conn.from_connector_id}_to_{conn.to_block_id}_{conn.to_connector_id}"
        in_pipes_map[str(conn.to_block_id)].append(pipe_id)
        
        to_block = next((b for b in setup.blocks if str(b.id) == str(conn.to_block_id)), None)
        out_pipes_map[str(conn.from_block_id)][conn.from_connector_id] = {
            'pipe_id': pipe_id,
            'block_id': conn.to_block_id,
            'block_name': to_block.name if to_block else 'Unknown',
            'connector_name': conn.to_connector_id
        }
    
    # 소스 블록 이벤트 초기화
    for block in setup.blocks:
        has_custom_sink = any(action.type == "custom_sink" for action in block.actions)
        if not in_pipes_map[str(block.id)] and not has_custom_sink:
            source_entity_request_events[str(block.id)] = state_manager.sim_env.event()
            source_entity_generated_counts[str(block.id)] = 0
            # 🔥 연속 생성을 위해 제한 없음으로 설정 (무한 생성 가능)
            source_entity_total_limits[str(block.id)] = float('inf')  # 무한 생성 가능
            if not PERFORMANCE_MODE:
                print(f"[INIT] 소스 블록 {block.id} ({block.name}) 초기화됨 (연속 생성 모드)")
    
    if not PERFORMANCE_MODE:
        print(f"[INIT] 총 {len(source_entity_request_events)}개 소스 블록 초기화됨")
    
    # 블록 프로세스들 시작
    for block_config in setup.blocks:
        state_manager.sim_env.process(block_process(state_manager.sim_env, block_config, in_pipes_map[str(block_config.id)], out_pipes_map[str(block_config.id)]))
    
    # 첫 스텝에서는 초기 엔티티 생성
    if not PERFORMANCE_MODE:
        print(f"[INIT] 첫 스텝에서 소스 블록 이벤트 트리거 시작")
    for block in setup.blocks:
        if str(block.id) in source_entity_request_events:
            event = source_entity_request_events[str(block.id)]
            if not PERFORMANCE_MODE:
                print(f"[INIT] 블록 {block.id}: 이벤트 트리거 시도")
            event.succeed()
            source_entity_request_events[str(block.id)] = state_manager.sim_env.event()
            if not PERFORMANCE_MODE:
                print(f"[INIT] 블록 {block.id}: 이벤트 트리거됨, 새 이벤트 생성됨")
    
    # 이벤트가 즉시 처리되도록 스케줄링 강제 실행
    if not PERFORMANCE_MODE:
        print(f"[INIT] 이벤트 스케줄링 강제 실행")
    try:
        state_manager.sim_env.step()
        if not PERFORMANCE_MODE:
            print(f"[INIT] 첫 스케줄링 단계 완료, 현재 시간: {state_manager.sim_env.now}")
    except simpy.core.EmptySchedule:
        if not PERFORMANCE_MODE:
            print(f"[INIT] 스케줄이 비어있음 - 정상")
    except Exception as e:
        if not PERFORMANCE_MODE:
            print(f"[INIT] 스케줄링 오류: {e}")
    
    # 시뮬레이션 실행
    def entity_count_monitor(env, target_count):
        while True:
            if processed_entities_count >= target_count:
                break
            yield env.timeout(0.1)
    
    if setup.stop_entities_processed:
        state_manager.sim_env.process(entity_count_monitor(state_manager.sim_env, setup.stop_entities_processed))
    
    try:
        if setup.stop_time:
            state_manager.sim_env.run(until=setup.stop_time)
        else:
            state_manager.sim_env.run()
    except Exception as e:
        if not PERFORMANCE_MODE:
            print(f"Simulation ended with exception: {e}")
    
    # 결과 반환
    return SimulationRunResult(
        message=f"Simulation completed. Processed {processed_entities_count} entities at time {state_manager.sim_env.now:.2f}",
        log=sim_log,
        total_entities_processed=processed_entities_count,
        final_time=state_manager.sim_env.now,
        active_entities=get_active_entity_states()
    )

async def step_simulation(setup: Optional[SimulationSetup] = None) -> SimulationStepResult:
    """🚀 OPTIMIZED: 엔티티 이동 기반 단일 스텝 시뮬레이션을 실행합니다. (main_old.py 패턴 적용)"""
    global sim_log, _cached_simulation_setup, _entity_states_cache, _entity_states_dirty
    
    try:
        # 🚀 Performance optimization: Only recreate environment when setup actually changes
        if setup is not None:
            if setup != _cached_simulation_setup:
                if DEBUG_MODE:
                    logger.debug("[INIT] 새로운 시뮬레이션 설정으로 환경 재생성")
                reset_simulation_state()
                
                state_manager.sim_env = simpy.Environment()
                if DEBUG_MODE:
                    logger.debug(f"[INIT] 새로운 SimPy 환경 생성됨 (시간: {state_manager.sim_env.now})")
                
                await run_simulation_setup_for_step(setup)
                _cached_simulation_setup = setup
                _entity_states_dirty = True
                
                if DEBUG_MODE:
                    logger.debug(f"[INIT] 시뮬레이션 설정 완료, 현재 시간: {state_manager.sim_env.now}")
            elif DEBUG_MODE:
                logger.debug("[INIT] 동일한 설정 - 환경 재사용")
        
        if state_manager.sim_env is None:
            raise RuntimeError("시뮬레이션 환경이 초기화되지 않았습니다. setup을 제공해주세요.")
        
        current_time = state_manager.sim_env.now
        
        # 🚀 Performance optimization: Simplified queue check
        if len(state_manager.sim_env._queue) == 0:
            if DEBUG_MODE:
                logger.debug("스케줄 비어있음 - 시뮬레이션 완료")
                logger.debug(f"활성 엔티티 수: {len(get_active_entity_states())}")
                logger.debug(f"처리된 엔티티 수: {processed_entities_count}")
            
            return SimulationStepResult(
                time=current_time,
                event_description="시뮬레이션 완료",
                active_entities=[],
                entities_processed_total=processed_entities_count,
                current_signals=get_current_signals()
            )
        
        # 🔥 FIXED: Only trigger source events when needed, not every step
        # 소스 이벤트는 초기화 단계에서만 트리거하고, 이후에는 자연스럽게 동작하도록 함
        
        # 🚀 SIMPLIFIED: Execute one meaningful event per step
        initial_time = state_manager.sim_env.now
        initial_entity_count = len(get_active_entity_states())
        initial_processed = processed_entities_count
        
        # 스텝 시작 전 엔티티 위치 상태 저장
        initial_entity_states = {}
        for entity in active_entities_registry:
            if hasattr(entity, 'id') and hasattr(entity, 'current_block_id'):
                initial_entity_states[entity.id] = entity.current_block_id
        
        if not PERFORMANCE_MODE:
            print(f"[STEP_DEBUG] 스텝 시작: 시간={initial_time}, 큐길이={len(state_manager.sim_env._queue)}, 엔티티={initial_entity_count}")
            
            # 🔍 이벤트 큐 상세 분석
            if len(state_manager.sim_env._queue) > 0:
                print(f"[STEP_DEBUG] 이벤트 큐 상태:")
                for i, event in enumerate(state_manager.sim_env._queue[:5]):  # 처음 5개 이벤트 출력
                    print(f"  Event {i}: time={event[0]}, priority={event[1]}, id={id(event[2])}")
            else:
                print(f"[STEP_DEBUG] 이벤트 큐가 비어있음")
        
        if len(state_manager.sim_env._queue) == 0:
            event_desc = "시뮬레이션 완료 - 더 이상 실행할 이벤트가 없음"
        else:
            # 단순히 다음 이벤트 하나만 실행
            next_event_time = state_manager.sim_env.peek()
            if not PERFORMANCE_MODE:
                print(f"[STEP_DEBUG] 다음 이벤트 시간: {next_event_time}")
            
            # 🔥 FIXED: Skip time 0 events if they don't advance time
            if next_event_time == 0 and initial_time == 0:
                # 시간 0 이벤트를 건너뛰고 시간이 진행되는 다음 이벤트로 넘어감
                if not PERFORMANCE_MODE:
                    print(f"[STEP_DEBUG] 시간 0 이벤트 감지 - 시간 진행 이벤트 찾기")
                found_time_advancing_event = False
                
                # 큐에서 시간이 진행되는 이벤트 찾기
                for i, item in enumerate(state_manager.sim_env._queue):
                    event_time = item[0]
                    if event_time > 0:
                        if not PERFORMANCE_MODE:
                            print(f"[STEP_DEBUG] 시간 진행 이벤트 발견: {event_time}초")
                        found_time_advancing_event = True
                        break
                
                if found_time_advancing_event:
                    # 시간이 진행되는 이벤트까지 실행
                    target_time = next((item[0] for item in state_manager.sim_env._queue if item[0] > 0), None)
                    if target_time:
                        if not PERFORMANCE_MODE:
                            print(f"[STEP_DEBUG] 시간 {target_time}까지 실행")
                        state_manager.sim_env.run(until=target_time)
                else:
                    # 시간이 진행되지 않으면 단일 스텝만 실행
                    state_manager.sim_env.step()
            else:
                state_manager.sim_env.step()
            new_time = state_manager.sim_env.now
            
            # 변화 감지
            time_changed = (new_time != initial_time)
            entity_count_changed = (len(get_active_entity_states()) != initial_entity_count)
            processed_changed = (processed_entities_count != initial_processed)
            
            # 엔티티 위치 변화 감지
            from .utils import check_entity_movement
            entity_moved = check_entity_movement(initial_entity_states, initial_processed)
            
            if not PERFORMANCE_MODE:
                print(f"[STEP_DEBUG] 스텝 완료: 시간={initial_time}→{new_time}, 엔티티={initial_entity_count}→{len(get_active_entity_states())}, 처리됨={initial_processed}→{processed_entities_count}")
            
            # 이벤트 설명 생성
            if processed_changed:
                event_desc = f"엔티티 처리 완료 (총 {processed_entities_count}개)"
            elif entity_moved:
                movement_description = get_latest_movement_description()
                event_desc = movement_description if movement_description else "엔티티 이동 감지"
            elif time_changed:
                event_desc = f"시간 진행: {initial_time:.1f}s → {new_time:.1f}s"
            elif entity_count_changed:
                event_desc = f"엔티티 수 변화: {initial_entity_count} → {len(get_active_entity_states())}"
            else:
                event_desc = f"시뮬레이션 이벤트 처리 (시간: {new_time:.1f}s)"
        
        new_time = state_manager.sim_env.now
        _entity_states_dirty = True  # Mark entity states as dirty
        
        # 🚀 Performance optimization: Cache entity states calculation
        if _entity_states_dirty:
            _entity_states_cache = get_active_entity_states()
            _entity_states_dirty = False
        entity_states = _entity_states_cache
        
        if DEBUG_MODE:
            logger.debug(f"최종 결과: 시간={new_time:.1f}, 이벤트='{event_desc}', 엔티티={len(entity_states)}개")
        
        return SimulationStepResult(
            time=new_time,
            event_description=event_desc,
            active_entities=entity_states,
            entities_processed_total=processed_entities_count,
            current_signals=get_current_signals()
        )
        
    except Exception as e:
        if not PERFORMANCE_MODE:
            print(f"[ERROR] 스텝 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
        return SimulationStepResult(
            time=state_manager.sim_env.now if state_manager.sim_env else 0,
            event_description=f"오류: {str(e)}",
            active_entities=[],
            entities_processed_total=processed_entities_count,
            current_signals=get_current_signals()
        )

async def batch_step_simulation(steps: int) -> BatchStepResult:
    """여러 스텝을 연속으로 실행합니다."""
    global processed_entities_count
    
    if not state_manager.sim_env:
        raise ValueError("No active simulation. Please start simulation first.")
    
    initial_log_count = len(sim_log)
    executed_steps = 0
    
    for i in range(steps):
        try:
            state_manager.sim_env.step()
            executed_steps += 1
        except simpy.core.EmptySchedule:
            break
    
    # 최종 이벤트 설명
    final_description = get_latest_movement_description()
    
    return BatchStepResult(
        message=f"{executed_steps} 스텝 실행 완료",
        steps_executed=executed_steps,
        final_event_description=final_description,
        log=sim_log[initial_log_count:],
        current_time=state_manager.sim_env.now,
        active_entities=get_active_entity_states(),
        total_entities_processed=processed_entities_count
    )

async def run_simulation_setup_for_step(setup: SimulationSetup) -> Optional[SimulationStepResult]:
    """스텝 실행을 위한 시뮬레이션 초기 설정"""
    global sim_log, processed_entities_count
    
    # 🔥 이미 step_simulation에서 초기화했으므로 여기서는 하지 않음
    # reset_simulation_state()는 step_simulation에서 이미 호출됨
    
    # 🔥 이미 state_manager.sim_env가 step_simulation에서 설정됨
    processed_entities_count = 0
    
    # 초기 신호 설정
    if setup.initial_signals:
        for signal_name, value in setup.initial_signals.items():
            set_signal(signal_name, value, state_manager.sim_env)
    
    # 파이프 생성
    for conn in setup.connections:
        pipe_id = f"{conn.from_block_id}_{conn.from_connector_id}_to_{conn.to_block_id}_{conn.to_connector_id}"
        block_pipes[pipe_id] = simpy.Store(state_manager.sim_env)
    
    # 블록별 입출력 파이프 매핑 (완전히 구성)
    in_pipes_map = {}
    out_pipes_map = {}
    
    for block in setup.blocks:
        in_pipes_map[block.id] = []
        out_pipes_map[block.id] = {}
    
    for conn in setup.connections:
        pipe_id = f"{conn.from_block_id}_{conn.from_connector_id}_to_{conn.to_block_id}_{conn.to_connector_id}"
        in_pipes_map[str(conn.to_block_id)].append(pipe_id)
        
        to_block = next((b for b in setup.blocks if str(b.id) == str(conn.to_block_id)), None)
        out_pipes_map[str(conn.from_block_id)][conn.from_connector_id] = {
            'pipe_id': pipe_id,
            'block_id': conn.to_block_id,
            'block_name': to_block.name if to_block else 'Unknown',
            'connector_name': conn.to_connector_id
        }
    
    # 소스 블록 이벤트 초기화
    for block in setup.blocks:
        has_custom_sink = any(action.type == "custom_sink" for action in block.actions)
        if not in_pipes_map[str(block.id)] and not has_custom_sink:
            source_entity_request_events[str(block.id)] = state_manager.sim_env.event()
            source_entity_generated_counts[str(block.id)] = 0
            # 🔥 연속 생성을 위해 제한 없음으로 설정 (무한 생성 가능)
            source_entity_total_limits[str(block.id)] = float('inf')  # 무한 생성 가능
            if not PERFORMANCE_MODE:
                print(f"[INIT] 소스 블록 {block.id} ({block.name}) 초기화됨 (연속 생성 모드)")
    
    if not PERFORMANCE_MODE:
        print(f"[INIT] 총 {len(source_entity_request_events)}개 소스 블록 초기화됨")
    
    # 블록 프로세스들 시작
    for block_config in setup.blocks:
        state_manager.sim_env.process(block_process(state_manager.sim_env, block_config, in_pipes_map[str(block_config.id)], out_pipes_map[str(block_config.id)]))
    
    # 첫 스텝에서는 초기 엔티티 생성
    if not PERFORMANCE_MODE:
        print(f"[INIT] 첫 스텝에서 소스 블록 이벤트 트리거 시작")
    for block in setup.blocks:
        if str(block.id) in source_entity_request_events:
            event = source_entity_request_events[str(block.id)]
            if not PERFORMANCE_MODE:
                print(f"[INIT] 블록 {block.id}: 이벤트 트리거 시도")
            event.succeed()
            source_entity_request_events[str(block.id)] = state_manager.sim_env.event()
            if not PERFORMANCE_MODE:
                print(f"[INIT] 블록 {block.id}: 이벤트 트리거됨, 새 이벤트 생성됨")
    
    # 이벤트가 즉시 처리되도록 스케줄링 강제 실행
    if not PERFORMANCE_MODE:
        print(f"[INIT] 이벤트 스케줄링 강제 실행")
    try:
        state_manager.sim_env.step()
        if not PERFORMANCE_MODE:
            print(f"[INIT] 첫 스케줄링 단계 완료, 현재 시간: {state_manager.sim_env.now}")
    except simpy.core.EmptySchedule:
        if not PERFORMANCE_MODE:
            print(f"[INIT] 스케줄이 비어있음 - 정상")
    except Exception as e:
        if not PERFORMANCE_MODE:
            print(f"[INIT] 스케줄링 오류: {e}")
    
    # 초기 설정 단계이므로 None을 반환하여 정상적인 스텝 실행이 계속되도록 함
    return None

def block_process(env: simpy.Environment, block_config: ProcessBlockConfig, in_pipe_ids: List[str], out_pipe_connectors: Dict[str, str]):
    """🚀 OPTIMIZED: 블록 프로세스의 핵심 로직"""
    global processed_entities_count, sim_log, signals, block_pipes, active_entities_registry
    global source_entity_request_events, source_entity_generated_counts 
    
    # 🚀 Performance optimization: Pre-calculate block type and prefix once
    block_log_prefix = f"BPROC [{block_config.name}({block_config.id})]"
    has_custom_sink = any(action.type == "custom_sink" for action in block_config.actions)
    is_source_block = not in_pipe_ids and not has_custom_sink
    
    if DEBUG_MODE:
        logger.debug(f"{env.now:.2f}: {block_log_prefix} Process started. Inputs: {in_pipe_ids}, Outputs: {out_pipe_connectors}")
        logger.debug(f"{env.now:.2f}: {block_log_prefix} Block analysis - Has input pipes: {bool(in_pipe_ids)}, Has custom_sink: {has_custom_sink}, Is source: {is_source_block}")
    
    sim_log.append({"time": env.now, "event": f"{block_log_prefix} process started."})

    while True:
        entity: Optional[Entity] = None
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} New loop iteration. Is source: {is_source_block}")

        # 엔티티 획득 로직 (소스/싱크/일반 블록별 처리)
        entity = yield from get_entity_for_block(env, block_config, is_source_block, has_custom_sink, in_pipe_ids, block_log_prefix)
        
        if not entity:
            if DEBUG_MODE:
                logger.debug(f"{env.now:.2f}: {block_log_prefix} No entity to process this iteration.")
            # 🚀 Performance optimization: Use longer timeout to reduce event overhead
            yield env.timeout(0.1)  # Increased from 0.0001 to 0.1
            continue

        # 액션 실행
        yield from execute_block_actions(env, block_config, entity, out_pipe_connectors, block_log_prefix)

def get_entity_for_block(env, block_config, is_source_block, has_custom_sink, in_pipe_ids, block_log_prefix):
    """블록 타입에 따라 엔티티를 획득합니다."""
    if is_source_block:
        return (yield from get_source_entity(env, block_config, block_log_prefix))
    elif has_custom_sink or in_pipe_ids:
        return (yield from get_pipe_entity(env, block_config, in_pipe_ids, block_log_prefix))
    else:
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} No valid input method. Idling.")
        yield env.timeout(1)
        return None

def get_source_entity(env, block_config, block_log_prefix):
    """🚀 OPTIMIZED: 소스 블록에서 엔티티를 생성합니다."""
    block_id_str = str(block_config.id)
    if block_id_str not in source_entity_request_events:
        if DEBUG_MODE:
            logger.error(f"{env.now:.2f}: {block_log_prefix} Critical Error: source_entity_request_event not initialized.")
        yield env.timeout(float('inf'))
        return None

    current_total_generated = source_entity_generated_counts.get(block_id_str, 0)
    if DEBUG_MODE:
        logger.debug(f"{env.now:.2f}: {block_log_prefix} Source block. Total generated so far: {current_total_generated}.")
    
    # Capacity check with detailed logging and type debugging
    current_entity_count = block_entity_counts.get(block_config.id, 0)
    max_capacity = getattr(block_config, 'maxCapacity', None) or getattr(block_config, 'capacity', None)
    
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} DEBUG: block_config.id={block_config.id} (type: {type(block_config.id)})")
        print(f"{env.now:.2f}: {block_log_prefix} DEBUG: block_entity_counts keys: {list(block_entity_counts.keys())}")
        print(f"{env.now:.2f}: {block_log_prefix} Capacity check: {current_entity_count}/{max_capacity}")
    
    if max_capacity is not None and current_entity_count >= max_capacity:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {block_log_prefix} Source block at capacity ({current_entity_count}/{max_capacity}). Waiting for space...")
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} Source block at capacity ({current_entity_count}/{max_capacity}). Cannot generate new entity.")
        sim_log.append({"time": env.now, "block_id": block_config.id, "event": f"Source {block_config.name} at capacity ({current_entity_count}/{max_capacity}), generation blocked"})
        yield env.timeout(0.5)  # 더 짧은 대기 시간으로 빠른 재시도
        return None
    
    # 🔥 Continuous production: Generate entities when capacity allows
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} Ready to generate new entity (total generated: {current_total_generated})")
    
    # For continuous production, only wait for events if we need to respect production timing
    if current_total_generated == 0 and env.now == 0:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {block_log_prefix} First entity - generating immediately.")
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} First entity - generating immediately.")
    else:
        # 🔥 Wait for signal only if needed, otherwise generate continuously when capacity allows
        current_signals = get_current_signals()
        load_enable = current_signals.get('공정1 load enable', True)
        
        if load_enable:
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {block_log_prefix} Load signal is enabled - generating entity immediately")
        else:
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {block_log_prefix} Waiting for load enable signal...")
            try:
                # 🔥 FIXED: Wait for signal change instead of entity request event
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {block_log_prefix} Waiting for '공정1 load enable' signal to become True")
                yield wait_for_signal('공정1 load enable', True, env)
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {block_log_prefix} Load enable signal received - proceeding with entity generation")
            except Exception as e:
                if DEBUG_MODE:
                    logger.error(f"{env.now:.2f}: {block_log_prefix} Exception waiting for signal: {e}.")
                yield env.timeout(0.1)
                return None
    
    # Re-check capacity after waiting
    current_entity_count = block_entity_counts.get(block_config.id, 0)
    if max_capacity is not None and current_entity_count >= max_capacity:
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} Source block capacity limit reached after wait ({current_entity_count}/{max_capacity}). Skipping generation.")
        yield env.timeout(0.1)
        return None
    
    # Entity generation
    entity_id_str = f"{block_config.id}-e{current_total_generated + 1}"
    entity = entity_pool.get_entity(env, entity_id_str)
    entity.update_location(block_config.id, block_config.name)
    
    # Entity generation logging with capacity update
    current_entity_count = block_entity_counts.get(block_config.id, 0)
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} Generated Entity {entity.id} (총 {current_total_generated + 1}번째, 용량: {current_entity_count + 1}/{max_capacity})")
    if DEBUG_MODE:
        logger.debug(f"{env.now:.2f}: {block_log_prefix} Generated Entity {entity.id} (capacity: {current_entity_count}/{max_capacity})")
    sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} generated at Source {block_config.name}"})
    
    source_entity_generated_counts[block_id_str] = current_total_generated + 1
    return entity

def get_pipe_entity(env, block_config, in_pipe_ids, block_log_prefix):
    """파이프에서 엔티티를 획득합니다."""
    # 여러 입력 파이프가 있는 경우 우선순위대로 체크
    for pipe_id in in_pipe_ids:
        pipe = block_pipes.get(pipe_id)
        if pipe and len(pipe.items) > 0:
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {block_log_prefix} Waiting for entity from pipe '{pipe_id}'")
            entity = yield pipe.get()
            
            # 🔥 수용량 체크 - 블록이 가득 찬 경우 엔티티를 받지 않음
            current_count = get_block_entity_count(block_config.id)
            max_capacity = getattr(block_config, 'maxCapacity', None) or getattr(block_config, 'capacity', None)
            
            if max_capacity is not None and current_count >= max_capacity:
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {block_log_prefix} Block at capacity ({current_count}/{max_capacity}), entity blocked")
                # 엔티티를 다시 파이프에 넣어서 나중에 처리
                yield pipe.put(entity)
                yield env.timeout(0.1)  # 짧은 대기 후 다시 시도
                continue
            
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {block_log_prefix} Received Entity {entity.id} from TRANSIT state (capacity: {current_count + 1}/{max_capacity or 'None'})")
            
            # 🔥 엔티티 위치를 현재 블록으로 업데이트
            entity.update_location(block_config.id, block_config.name)
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {block_log_prefix} Entity {entity.id} location updated from transit to block {block_config.name}")
            
            # 커넥터 액션이 있으면 먼저 실행
            yield from execute_connector_actions(env, block_config, entity, pipe_id, block_log_prefix)
            
            return entity
    
    # 모든 파이프가 비어있거나 수용량 초과인 경우
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} Waiting for entity from pipe '{in_pipe_ids[0] if in_pipe_ids else 'unknown'}'")
    entity = yield block_pipes[in_pipe_ids[0]].get()
    
    # 🔥 수용량 재체크
    current_count = get_block_entity_count(block_config.id)
    max_capacity = getattr(block_config, 'maxCapacity', None) or getattr(block_config, 'capacity', None)
    
    if max_capacity is not None and current_count >= max_capacity:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {block_log_prefix} Block still at capacity, waiting...")
        yield block_pipes[in_pipe_ids[0]].put(entity)
        yield env.timeout(0.1)
        return None
    
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} Received Entity {entity.id} from TRANSIT state (capacity: {current_count + 1}/{max_capacity or 'None'})")
    
    # 🔥 엔티티 위치를 현재 블록으로 업데이트
    entity.update_location(block_config.id, block_config.name)
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {block_log_prefix} Entity {entity.id} location updated from transit to block {block_config.name}")
    
    # 커넥터 액션이 있으면 먼저 실행
    yield from execute_connector_actions(env, block_config, entity, in_pipe_ids[0], block_log_prefix)
    
    return entity

def execute_connector_actions(env, block_config, entity, arrival_pipe_id, block_log_prefix):
    """도착한 커넥터의 액션들을 실행합니다."""
    # 도착한 파이프에 해당하는 커넥터 찾기
    target_connector = None
    if hasattr(block_config, 'connectionPoints') and block_config.connectionPoints:
        for connector in block_config.connectionPoints:
            # 파이프 ID 형태: "1_1-conn-right_to_2_2-conn-left"
            # 커넥터 ID가 파이프 ID에 포함되는지 확인
            if arrival_pipe_id.endswith(f"to_{block_config.id}_{connector.id}"):
                target_connector = connector
                break
    
    if not target_connector:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {block_log_prefix} No actions in connector {arrival_pipe_id}")
        return
    
    if not hasattr(target_connector, 'actions') or not target_connector.actions:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {block_log_prefix} No actions in connector {target_connector.id}")
        return
    
    # 커넥터 액션 실행
    connector_log_prefix = f"{block_log_prefix} [Connector:{target_connector.id}] [E:{entity.id}]"
    
    # 🔥 중요: 커넥터 액션 실행 중에는 엔티티가 여전히 현재 블록에 위치함을 보장
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {connector_log_prefix} Starting connector actions (entity remains in block {block_config.name})")
    
    # 🔥 엔티티 위치를 명시적으로 현재 블록으로 설정 (화면 표시용)
    entity.update_location(block_config.id, block_config.name)
    
    for action in target_connector.actions:
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {connector_log_prefix} Executing connector action: {action.name} ({action.type})")
        
        if action.type == "block_entry":
            # 블록으로 이동 액션 (커넥터에서 같은 블록으로 진입)
            delay = action.parameters.get("delay", "1")
            target_block_name = action.parameters.get("target_block_name", block_config.name)
            
            # 딜레이 처리 (엔티티는 아직 현재 블록에 있음)
            if delay and delay != "0":
                delay_time = parse_delay_value(str(delay))
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} Delaying for {delay_time}s before entering block {target_block_name}")
                entity.update_location(block_config.id, block_config.name)
                # 🔥 DEBUG: Timeout 이벤트 생성 전 큐 상태 확인
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} DEBUG: Creating timeout event for {delay_time}s (target time: {env.now + delay_time})")
                    print(f"{env.now:.2f}: {connector_log_prefix} DEBUG: Queue size before timeout: {len(env._queue)}")
                timeout_event = env.timeout(delay_time)
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} DEBUG: Queue size after timeout: {len(env._queue)}")
                yield timeout_event
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} DEBUG: Timeout completed at time {env.now}")
            
            # 같은 블록으로 진입 완료
            if not PERFORMANCE_MODE:
                print(f"{env.now:.2f}: {connector_log_prefix} Entity entering block {target_block_name}")
            entity.update_location(block_config.id, block_config.name)
            return  # 커넥터 액션 완료, 블록 액션으로 진행
            
        elif action.type == "conditional_branch":
            script = action.parameters.get("script", "")
            if script:
                act_log = []
                yield from execute_conditional_branch_script(env, script, entity, act_log, {})
                
                # 🔥 중요: 커넥터에서 같은 블록으로 이동하는 경우 체크 (더 정확한 매칭)
                self_move_detected = any("moving to same block's main process" in log.lower() for log in act_log)
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} Act log contents: {act_log}")
                    print(f"{env.now:.2f}: {connector_log_prefix} Self move detected: {self_move_detected}")
                
                if self_move_detected:
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Entity stays in same block - no location change needed")
                    # 🔥 엔티티 위치 확실히 유지
                    entity.update_location(block_config.id, block_config.name)
                    # 커넥터 액션 완료, 엔티티는 계속 같은 블록에서 블록 액션 진행
                    return
                    
                # 다른 블록으로 이동한 경우만 반환
                external_move_detected = any("moved to" in log.lower() and "same block" not in log.lower() for log in act_log)
                if external_move_detected:
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Entity moved to different block")
                    return
        
        elif action.type == "signal_wait":
            # 신호 대기 액션 (엔티티는 여전히 같은 블록에 있음)
            signal_name = action.parameters.get("signal_name")
            expected_value = action.parameters.get("expected_value", True)
            
            if signal_name:
                # 🔥 먼저 현재 신호 값 확인하여 즉시 처리 가능한지 확인
                current_signals = get_current_signals()
                if current_signals.get(signal_name, False) == expected_value:
                    # 이미 원하는 값이면 즉시 진행
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' already {expected_value} - proceeding immediately (entity in {block_config.name})")
                else:
                    # 원하는 값이 아니면 대기
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Waiting for signal '{signal_name}' = {expected_value} (entity in {block_config.name})")
                    # 🔥 엔티티 위치를 확실히 유지
                    entity.update_location(block_config.id, block_config.name)
                    yield wait_for_signal(signal_name, expected_value, env)
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' received")
        
        elif action.type == "signal_update":
            # 신호 업데이트 액션 (엔티티는 여전히 같은 블록에 있음)
            signal_name = action.parameters.get("signal_name")
            value = action.parameters.get("value", False)
            
            if signal_name:
                set_signal(signal_name, value, env)
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' set to {value}")
        
        elif action.type == "route_to_connector":
            # 다른 블록으로 라우팅 액션
            delay = action.parameters.get("delay", "0")
            target_block_id = action.parameters.get("target_block_id")
            target_connector_id = action.parameters.get("target_connector_id")
            
            # 딜레이 처리 (엔티티는 아직 현재 블록에 있음)
            if delay and delay != "0":
                delay_time = parse_delay_value(str(delay))
                if not PERFORMANCE_MODE:
                    print(f"{env.now:.2f}: {connector_log_prefix} Delaying for {delay_time}s before routing (entity in {block_config.name})")
                # 🔥 딜레이 중에도 엔티티 위치 유지
                entity.update_location(block_config.id, block_config.name)
                yield env.timeout(delay_time)
            
            # 🔥 라우팅 처리 - 이때만 엔티티 위치를 변경
            if target_block_id and target_connector_id:
                pipe_id = f"{block_config.id}_{target_connector.id}_to_{target_block_id}_{target_connector_id}"
                
                if pipe_id in block_pipes:
                    # 🔥 엔티티가 실제로 다른 블록으로 이동할 때만 transit 상태로 변경
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Connector actions completed - now routing to different block")
                    
                    yield block_pipes[pipe_id].put(entity)
                    target_block_name = action.parameters.get("target_block_name", f"Block {target_block_id}")
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {block_log_prefix} [E:{entity.id}] Routed to {target_block_name}")
                    sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} routed from {block_config.name} to {target_block_name}"})
                    return  # 엔티티가 다른 블록으로 이동했으므로 반환
                else:
                    # 🔥 파이프가 존재하지 않는 경우 오류 처리
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} ERROR: Pipe {pipe_id} not found. Available pipes: {list(block_pipes.keys())}")
                        print(f"{env.now:.2f}: {connector_log_prefix} Routing failed - entity remains in current block")
                    return
    
    if not PERFORMANCE_MODE:
        print(f"{env.now:.2f}: {connector_log_prefix} All connector actions completed (entity remains in {block_config.name})")

def execute_block_actions(env, block_config, entity, out_pipe_connectors, block_log_prefix):
    """블록의 액션들을 실행합니다."""
    global processed_entities_count
    
    entity_log_prefix = f"{block_log_prefix} [E:{entity.id}]"
    current_action_index = 0
    
    while current_action_index < len(block_config.actions):
        action = block_config.actions[current_action_index]
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {entity_log_prefix} Executing action: {action.name} ({action.type})")
        
        # 액션 실행
        result = yield from execute_single_action(env, action, entity, out_pipe_connectors, entity_log_prefix, block_config)
        
        if result == 'route_out':
            # 엔티티가 다른 블록으로 라우팅됨
            break
        elif result == 'processed':
            # 엔티티가 처리됨 (싱크)
            processed_entities_count += 1
            entity_pool.return_entity(entity)
            break
        
        current_action_index += 1

def execute_single_action(env, action, entity, out_pipe_connectors, entity_log_prefix, block_config):
    """단일 액션을 실행합니다."""
    act_log = []
    
    if action.type == "delay":
        duration = parse_delay_value(str(action.parameters.get("duration", 0)))
        if duration > 0:
            yield env.timeout(duration)
        else:
            yield env.timeout(0.00001)
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {entity_log_prefix} Delayed for {duration}s.")
    
    elif action.type == "custom_sink":
        # 🔥 Entity 클래스의 remove()가 자동으로 카운트 감소
        if not PERFORMANCE_MODE:
            print(f"{env.now:.2f}: {entity_log_prefix} Processed by custom sink.")
        sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} processed by sink"})
        return 'processed'
    
    elif action.type == "route_to_connector":
        connector_id = action.parameters.get("connector_id")
        delay = action.parameters.get("delay", "0")
        
        if delay and delay != "0":
            delay_time = parse_delay_value(str(delay))
            yield env.timeout(delay_time)
        
        if connector_id and connector_id in out_pipe_connectors:
            pipe_info = out_pipe_connectors[connector_id]
            pipe_id = pipe_info.get('pipe_id')
            
            if pipe_id and pipe_id in block_pipes:
                # 같은 블록 내 커넥터로 이동하는 경우 커넥터 액션 실행
                target_connector = None
                if hasattr(block_config, 'connectionPoints') and block_config.connectionPoints:
                    for connector in block_config.connectionPoints:
                        if connector.id == connector_id:
                            target_connector = connector
                            break
                
                if target_connector and hasattr(target_connector, 'actions') and target_connector.actions:
                    # 커넥터 액션들을 실행
                    connector_log_prefix = f"{entity_log_prefix} [Connector:{target_connector.id}]"
                    if not PERFORMANCE_MODE:
                        print(f"{env.now:.2f}: {connector_log_prefix} Executing connector actions before routing")
                        # 🔥 커넥터 액션 실행 중에는 엔티티가 여전히 같은 블록에 있음을 명시
                        print(f"{env.now:.2f}: {connector_log_prefix} Entity remains in block {block_config.name} during connector actions")
                    
                    # 🔥 라우팅 정보를 저장할 변수 (모든 액션 실행 후 라우팅 수행)
                    pending_route_action = None
                    
                    for conn_action in target_connector.actions:
                        if not PERFORMANCE_MODE:
                            print(f"{env.now:.2f}: {connector_log_prefix} Executing: {conn_action.name} ({conn_action.type})")
                        
                        if conn_action.type == "signal_wait":
                            signal_name = conn_action.parameters.get("signal_name")
                            expected_value = conn_action.parameters.get("expected_value", True)
                            if signal_name:
                                # 🔥 먼저 현재 신호 값 확인하여 즉시 처리 가능한지 확인
                                current_signals = get_current_signals()
                                if current_signals.get(signal_name, False) == expected_value:
                                    # 이미 원하는 값이면 즉시 진행
                                    if not PERFORMANCE_MODE:
                                        print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' already {expected_value} - proceeding immediately (entity in {block_config.name})")
                                else:
                                    # 원하는 값이 아니면 대기
                                    if not PERFORMANCE_MODE:
                                        print(f"{env.now:.2f}: {connector_log_prefix} Waiting for signal '{signal_name}' = {expected_value} (entity in {block_config.name})")
                                    yield wait_for_signal(signal_name, expected_value, env)
                                    if not PERFORMANCE_MODE:
                                        print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' received")
                        
                        elif conn_action.type == "signal_update":
                            signal_name = conn_action.parameters.get("signal_name")
                            value = conn_action.parameters.get("value", False)
                            if signal_name:
                                set_signal(signal_name, value, env)
                                if not PERFORMANCE_MODE:
                                    print(f"{env.now:.2f}: {connector_log_prefix} Signal '{signal_name}' set to {value}")
                        
                        elif conn_action.type == "route_to_connector":
                            # 🔥 커넥터의 route_to_connector 액션 - 라우팅 정보만 저장하고 계속 실행
                            conn_delay = conn_action.parameters.get("delay", "0")
                            if conn_delay and conn_delay != "0":
                                conn_delay_time = parse_delay_value(str(conn_delay))
                                if not PERFORMANCE_MODE:
                                    print(f"{env.now:.2f}: {connector_log_prefix} Delaying for {conn_delay_time}s before routing (entity in {block_config.name})")
                                yield env.timeout(conn_delay_time)
                            
                            # 🔥 라우팅 액션 정보 저장 (나중에 실행)
                            pending_route_action = conn_action
                            if not PERFORMANCE_MODE:
                                print(f"{env.now:.2f}: {connector_log_prefix} Route action scheduled: will move to {conn_action.parameters.get('target_block_name', 'Unknown')} after all connector actions complete")
                            # 🔥 break 하지 않고 계속 다음 액션 실행
                    
                    # 🔥 모든 커넥터 액션 완료 후 라우팅 수행
                    if pending_route_action:
                        if not PERFORMANCE_MODE:
                            print(f"{env.now:.2f}: {connector_log_prefix} All connector actions completed - now executing pending route action")
                        
                        # 저장된 라우팅 액션의 파라미터로 라우팅 수행
                        target_block_id = pending_route_action.parameters.get("target_block_id")
                        target_connector_id = pending_route_action.parameters.get("target_connector_id")
                        target_block_name = pending_route_action.parameters.get("target_block_name", f"Block {target_block_id}")
                        
                        if target_block_id and target_connector_id:
                            # 새로운 파이프 ID 생성
                            route_pipe_id = f"{block_config.id}_{connector_id}_to_{target_block_id}_{target_connector_id}"
                            
                            if route_pipe_id in block_pipes:
                                # 🔥 Entity visibility fix: Set to transit state and ensure UI can track
                                transit_display_name = f"{block_config.name}→{target_block_name}"
                                entity.update_location("transit", transit_display_name)
                                if not PERFORMANCE_MODE:
                                    print(f"{env.now:.2f}: {connector_log_prefix} Entity {entity.id} set to TRANSIT state before routing to {target_block_name}")
                                
                                # 🔥 Enhanced logging for UI visibility tracking
                                if not PERFORMANCE_MODE:
                                    print(f"{env.now:.2f}: [TRANSIT_TRACKING] Entity {entity.id} entering transit from 공정1.R to 배출.L")
                                sim_log.append({
                                    "time": env.now, 
                                    "entity_id": entity.id, 
                                    "event": f"Entity {entity.id} entering transit from {block_config.name} to {target_block_name}",
                                    "transit_from": block_config.name,
                                    "transit_to": target_block_name
                                })
                                
                                yield block_pipes[route_pipe_id].put(entity)
                                if not PERFORMANCE_MODE:
                                    print(f"{env.now:.2f}: {connector_log_prefix} Entity routed to {target_block_name}")
                                sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} routed from {block_config.name} to {target_block_name}"})
                                return 'route_out'
                            else:
                                print(f"{env.now:.2f}: {connector_log_prefix} ERROR: Route pipe {route_pipe_id} not found. Available: {list(block_pipes.keys())}")
                                return 'route_error'
                        else:
                            print(f"{env.now:.2f}: {connector_log_prefix} ERROR: Invalid route parameters")
                            return 'route_error'
                    else:
                        print(f"{env.now:.2f}: {connector_log_prefix} No routing action found - connector actions completed without routing")
                
                # 🔥 커넥터에 액션이 없는 경우에만 기본 라우팅 수행
                else:
                    # 🔥 커넥터에 액션이 없는 경우의 기본 라우팅 로직
                    print(f"{env.now:.2f}: {entity_log_prefix} No connector actions - performing direct routing")
                    
                    # 🔥 파이프 존재 여부 확인
                    if pipe_id not in block_pipes:
                        print(f"{env.now:.2f}: {entity_log_prefix} ERROR: Pipe {pipe_id} not found. Available pipes: {list(block_pipes.keys())}")
                        return 'route_error'
                    
                    # 🔥 Entity visibility fix: Enhanced transit tracking for direct routing
                    target_block_name = pipe_info.get('block_name', 'Unknown')
                    transit_display_name = f"{block_config.name}→{target_block_name}"
                    entity.update_location("transit", transit_display_name)
                    print(f"{env.now:.2f}: {entity_log_prefix} Entity {entity.id} set to TRANSIT state before direct routing")
                    
                    # 🔥 Enhanced logging for UI visibility tracking
                    print(f"{env.now:.2f}: [TRANSIT_TRACKING] Entity {entity.id} entering transit from {block_config.name} to {target_block_name}")
                    sim_log.append({
                        "time": env.now, 
                        "entity_id": entity.id, 
                        "event": f"Entity {entity.id} entering transit from {block_config.name} to {target_block_name}",
                        "transit_from": block_config.name,
                        "transit_to": target_block_name
                    })
                    
                    yield block_pipes[pipe_id].put(entity)
                    print(f"{env.now:.2f}: {entity_log_prefix} Routed to {target_block_name}")
                    sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} routed out"})
                    return 'route_out'
    
    elif action.type == "conditional_branch":
        script = action.parameters.get("script", "")
        if script:
            yield from execute_conditional_branch_script(env, script, entity, act_log, out_pipe_connectors)
            if any("moved to" in log for log in act_log):
                # 🔥 스크립트로 이동은 이미 script_executor에서 처리되므로 여기서는 카운트 처리 안함
                return 'route_out'
    
    return 'continue' 
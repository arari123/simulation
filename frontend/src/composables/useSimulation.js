/**
 * 시뮬레이션 실행 관련 Composable
 * 시뮬레이션 상태와 실행 로직을 관리합니다.
 */

import { ref, computed } from 'vue'
import SimulationApi from '../services/SimulationApi.js'
import { usePerformanceMonitor } from './usePerformanceMonitor.js'

export function useSimulation() {
  // 성능 모니터링 시스템
  const performanceMonitor = usePerformanceMonitor()
  
  // 시뮬레이션 상태
  const dispatchedProductsFromSim = ref(0)
  const processTimeFromSim = ref(0)
  const currentStepCount = ref(0)
  const isFirstStep = ref(true)
  const activeEntityStates = ref([])
  const stepHistory = ref([])
  const isSimulationEnded = ref(false)
  const isFullExecutionRunning = ref(false)
  const shouldStopFullExecution = ref(false)
  
  // 설정
  const maxHistorySize = 100

  // 계산된 속성
  const hasStepHistory = computed(() => stepHistory.value.length > 0)
  const canGoBack = computed(() => currentStepCount.value > 0 && hasStepHistory.value)

  /**
   * 시뮬레이션 상태 초기화
   */
  function resetSimulationState() {
    dispatchedProductsFromSim.value = 0
    processTimeFromSim.value = 0
    currentStepCount.value = 0
    isFirstStep.value = true
    activeEntityStates.value = []
    stepHistory.value = []
    isSimulationEnded.value = false
    isFullExecutionRunning.value = false
    shouldStopFullExecution.value = false
  }

  /**
   * 스텝 히스토리에 현재 상태 저장
   */
  function saveCurrentStateToHistory() {
    const currentState = {
      stepCount: currentStepCount.value,
      dispatchedProducts: dispatchedProductsFromSim.value,
      processTime: processTimeFromSim.value,
      entityStates: JSON.parse(JSON.stringify(activeEntityStates.value)),
      timestamp: Date.now()
    }
    
    stepHistory.value.push(currentState)
    
    // 히스토리 크기 제한
    if (stepHistory.value.length > maxHistorySize) {
      stepHistory.value.shift()
    }
  }

  /**
   * 이전 스텝으로 되돌리기
   */
  function goToPreviousStep() {
    if (!canGoBack.value) {
      console.warn('[useSimulation] 되돌릴 수 있는 스텝이 없습니다')
      return false
    }
    
    // 마지막 히스토리 제거 (현재 상태)
    stepHistory.value.pop()
    
    if (stepHistory.value.length > 0) {
      // 이전 상태로 복원
      const previousState = stepHistory.value[stepHistory.value.length - 1]
      
      currentStepCount.value = previousState.stepCount
      dispatchedProductsFromSim.value = previousState.dispatchedProducts
      processTimeFromSim.value = previousState.processTime
      activeEntityStates.value = JSON.parse(JSON.stringify(previousState.entityStates))
      
    } else {
      // 첫 번째 스텝으로 되돌아감
      resetSimulationState()
    }
    
    isSimulationEnded.value = false
    return true
  }

  /**
   * 단일 스텝 실행
   */
  async function executeStep(setupData, updateBlockWarnings) {
    try {
      // 현재 상태를 히스토리에 저장
      if (!isFirstStep.value) {
        saveCurrentStateToHistory()
      }
      
      // 🚀 성능 모니터링과 함께 API 호출
      const result = await performanceMonitor.measureApiCall(
        `stepSimulation-${currentStepCount.value + 1}`,
        SimulationApi.stepSimulation,
        setupData
      )
      
      // 결과 처리 - 백엔드에서는 SimulationStepResult 모델을 반환하므로 success 필드가 없음
      if (result && typeof result === 'object') {
        updateSimulationState(result, updateBlockWarnings)
        isFirstStep.value = false
        return { success: true, result }
      } else {
        console.error('[useSimulation] 스텝 실행 실패: 잘못된 응답 형식')
        return { success: false, error: '잘못된 응답 형식' }
      }
    } catch (error) {
      console.error('[useSimulation] 스텝 실행 중 오류:', error)
      return { success: false, error: error.message || '알 수 없는 오류' }
    }
  }

  /**
   * 배치 스텝 실행
   */
  async function executeBatchSteps(setupData, stepCount = 10) {
    try {
      // 현재 상태를 히스토리에 저장
      if (!isFirstStep.value) {
        saveCurrentStateToHistory()
      }
      
      // 🚀 성능 모니터링과 함께 API 호출
      const result = await performanceMonitor.measureApiCall(
        `batchStepSimulation-${stepCount}`,
        SimulationApi.batchStepSimulation,
        setupData,
        stepCount
      )
      
      // 결과 처리 - 백엔드에서는 BatchStepResult 모델을 반환하므로 success 편드가 없음
      if (result && typeof result === 'object') {
        updateSimulationState(result)
        isFirstStep.value = false
        return { success: true, result }
      } else {
        console.error('[useSimulation] 배치 스텝 실행 실패: 잘못된 응답 형식')
        return { success: false, error: '잘못된 응답 형식' }
      }
    } catch (error) {
      console.error('[useSimulation] 배치 스텝 실행 중 오류:', error)
      return { success: false, error: error.message || '알 수 없는 오류' }
    }
  }


  /**
   * 시뮬레이션 결과로 상태 업데이트
   */
  function updateSimulationState(result, updateBlockWarnings) {
    // 백엔드 응답 구조에 맞게 필드명 수정
    if (result.time !== undefined) {
      processTimeFromSim.value = result.time
    }
    
    // step 응답에는 step_count가 없으므로 직접 증가
    currentStepCount.value++
    
    if (result.entities_processed_total !== undefined) {
      dispatchedProductsFromSim.value = result.entities_processed_total
    }
    
    if (result.active_entities) {
      activeEntityStates.value = result.active_entities
    }
    
    // 블록 상태 및 경고 정보 업데이트
    if (result.block_states && updateBlockWarnings) {
      updateBlockWarnings(result.block_states)
    }
    
    // 배치 스텝 응답의 경우 추가 필드들 처리
    if (result.current_time !== undefined) {
      processTimeFromSim.value = result.current_time
    }
    
    if (result.total_entities_processed !== undefined) {
      dispatchedProductsFromSim.value = result.total_entities_processed
    }
    
    if (result.steps_executed !== undefined) {
      currentStepCount.value += (result.steps_executed - 1) // 이미 1 증가했으므로
    }
    
    // 시뮬레이션 종료 조건 확인
    if (result.event_description && 
        (result.event_description.includes('시뮬레이션 완료') || 
         result.event_description.includes('더 이상 실행할 이벤트가 없습니다'))) {
      isSimulationEnded.value = true
    }
  }

  /**
   * 스텝 기반 전체 실행 시작
   */
  async function startStepBasedExecution(setupData, onStepComplete, options = {}, updateBlockWarnings) {
    isFullExecutionRunning.value = true
    shouldStopFullExecution.value = false
    
    try {
      let currentSetupData = setupData // 첫 번째 스텝에만 setupData 사용
      let initialDispatchedProducts = dispatchedProductsFromSim.value // 시작 시점의 배출 제품 수
      
      while (!isSimulationEnded.value && !shouldStopFullExecution.value) {
        const result = await executeStep(currentSetupData, updateBlockWarnings)
        
        if (!result.success) {
          console.error('[useSimulation] 스텝 실행 실패, 전체 실행 중단:', result.error)
          break
        }
        
        // 첫 번째 스텝 이후에는 null 사용
        currentSetupData = null
        
        // 스텝 완료 콜백 호출
        if (onStepComplete) {
          onStepComplete(result.result)
        }
        
        // 투입 수량 기반 정지 조건 확인
        if (options.mode === 'quantity' && options.value) {
          const processedCount = dispatchedProductsFromSim.value - initialDispatchedProducts
          if (processedCount >= options.value) {
            shouldStopFullExecution.value = true
            break
          }
        }
        
        // 시간 기반 정지 조건 확인 (향후 구현)
        if (options.mode === 'time' && options.value) {
          // TODO: 시간 기반 정지 로직 구현
        }
        
        // UI 업데이트를 위한 최소 대기 (60fps)
        await new Promise(resolve => requestAnimationFrame(resolve))
      }
    } catch (error) {
      console.error('[useSimulation] 전체 실행 중 오류:', error)
    } finally {
      isFullExecutionRunning.value = false
      shouldStopFullExecution.value = false
      
      // 실행 완료
    }
  }


  /**
   * 전체 실행 중단
   */
  function stopFullExecution() {
    shouldStopFullExecution.value = true
  }

  /**
   * 시뮬레이션 초기화 (백엔드 포함)
   */
  async function resetSimulation() {
    try {
      // 🚀 성능 모니터링과 함께 백엔드 초기화
      await performanceMonitor.measureApiCall(
        'resetSimulation',
        SimulationApi.resetSimulation
      )
      
      // 프론트엔드 상태 초기화
      resetSimulationState()
      
      return { success: true }
    } catch (error) {
      console.error('[useSimulation] 시뮬레이션 초기화 실패:', error)
      return { success: false, error: error.message }
    }
  }

  return {
    // 상태
    dispatchedProductsFromSim,
    processTimeFromSim,
    currentStepCount,
    isFirstStep,
    activeEntityStates,
    stepHistory,
    isSimulationEnded,
    isFullExecutionRunning,
    shouldStopFullExecution,
    
    // 계산된 속성
    hasStepHistory,
    canGoBack,
    
    // 메서드
    resetSimulationState,
    saveCurrentStateToHistory,
    goToPreviousStep,
    executeStep,
    executeBatchSteps,
    updateSimulationState,
    startStepBasedExecution,
    stopFullExecution,
    resetSimulation,
    
    // 🚀 성능 모니터링 시스템
    performanceMonitor
  }
} 
/**
 * 디버그 관련 Composable
 * 디버그 상태 관리 및 제어
 */

import { ref, computed, watch } from 'vue'
import DebugApi from '../services/DebugApi.js'

export function useDebug() {
  // 디버그 상태
  const isDebugging = ref(false)
  const isPaused = ref(false)
  const currentBreak = ref(null) // { block_id, line }
  const executionContext = ref([])
  
  // 디버그 모드 시작/중지
  async function startDebugMode() {
    try {
      const result = await DebugApi.startDebugMode()
      isDebugging.value = true
      console.log('Debug mode started')
      return result
    } catch (error) {
      console.error('Failed to start debug mode:', error)
      throw error
    }
  }
  
  async function stopDebugMode() {
    try {
      const result = await DebugApi.stopDebugMode()
      isDebugging.value = false
      isPaused.value = false
      currentBreak.value = null
      console.log('Debug mode stopped')
      return result
    } catch (error) {
      console.error('Failed to stop debug mode:', error)
      throw error
    }
  }
  
  // 실행 제어
  async function continueExecution() {
    try {
      const result = await DebugApi.continueExecution()
      isPaused.value = false
      console.log('Execution continued')
      return result
    } catch (error) {
      console.error('Failed to continue execution:', error)
      throw error
    }
  }
  
  async function stepExecution() {
    try {
      const result = await DebugApi.stepExecution()
      console.log('Step execution')
      return result
    } catch (error) {
      console.error('Failed to step execution:', error)
      throw error
    }
  }
  
  // 디버그 상태 업데이트
  async function updateDebugStatus() {
    try {
      const status = await DebugApi.getDebugStatus()
      isDebugging.value = status.is_debugging
      isPaused.value = status.is_paused
      currentBreak.value = status.current_break
      executionContext.value = status.execution_context || []
      return status
    } catch (error) {
      console.error('Failed to update debug status:', error)
      return null
    }
  }
  
  // 브레이크포인트가 있는 블록인지 확인
  const currentBreakBlockId = computed(() => {
    return currentBreak.value?.block_id || null
  })
  
  const currentBreakLine = computed(() => {
    return currentBreak.value?.line || null
  })
  
  // 디버그 정보 텍스트
  const debugInfoText = computed(() => {
    if (!isDebugging.value) {
      return '디버그 모드 OFF'
    }
    
    if (isPaused.value && currentBreak.value) {
      return `브레이크포인트: 블록 ${currentBreak.value.block_id}, 라인 ${currentBreak.value.line}`
    }
    
    return '디버그 모드 ON'
  })
  
  return {
    // 상태
    isDebugging,
    isPaused,
    currentBreak,
    executionContext,
    
    // 계산된 속성
    currentBreakBlockId,
    currentBreakLine,
    debugInfoText,
    
    // 메서드
    startDebugMode,
    stopDebugMode,
    continueExecution,
    stepExecution,
    updateDebugStatus
  }
}
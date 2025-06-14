/**
 * 신호 관리 관련 Composable
 * 전역 신호의 생성, 수정, 삭제 및 참조 관리를 담당합니다.
 */

import { ref, computed } from 'vue'
import { SignalType, getDefaultValue, inferType } from '../constants/signalTypes.js'

export function useSignals() {
  // 신호 상태
  const globalSignals = ref([])
  const showGlobalSignalPanel = ref(false) // 초기값을 false로 변경하여 숨김 상태로 시작

  // 계산된 속성
  const getAllSignalNames = computed(() => {
    const signalNames = new Set()
    
    // 전역 신호에서 수집
    globalSignals.value.forEach(signal => {
      signalNames.add(signal.name)
    })

    return Array.from(signalNames)
  })

  /**
   * 초기 신호 설정
   */
  function setupInitialSignals(baseConfig) {
    if (baseConfig.globalSignals) {
      globalSignals.value = baseConfig.globalSignals.map(signal => ({
        ...signal,
        // 타입 정보 추가 (없으면 값에서 추론)
        type: signal.type || inferType(signal.value),
        // 초기값이 정의되어 있다면 value에 반영
        value: signal.initialValue !== undefined ? signal.initialValue : signal.value
      }))
    }
  }

  /**
   * 신호 패널 표시/숨김 토글
   */
  function toggleGlobalSignalPanelVisibility() {
    showGlobalSignalPanel.value = !showGlobalSignalPanel.value
  }

  /**
   * 신호 패널 닫기
   */
  function handleCloseGlobalSignalPanel() {
    showGlobalSignalPanel.value = false
  }

  /**
   * 새 신호 추가
   */
  function handleAddGlobalSignal(signal) {
    if (!globalSignals.value.find(s => s.name === signal.name)) {
      const signalType = signal.type || inferType(signal.value)
      const defaultVal = getDefaultValue(signalType)
      
      globalSignals.value.push({
        id: signal.id || `signal-${Date.now()}`,
        name: signal.name,
        type: signalType,
        value: signal.value !== undefined ? signal.value : defaultVal,
        initialValue: signal.initialValue !== undefined ? signal.initialValue : defaultVal
      })
    } else {
      console.warn(`[useSignals] 이미 존재하는 신호: ${signal.name}`)
    }
  }

  /**
   * 신호 삭제
   */
  function handleRemoveGlobalSignal(signalName) {
    const index = globalSignals.value.findIndex(s => s.name === signalName)
    if (index !== -1) {
      globalSignals.value.splice(index, 1)
    }
  }

  /**
   * 신호 값 업데이트
   */
  function handleUpdateGlobalSignalValue(data) {
    const signal = globalSignals.value.find(s => s.name === data.name)
    if (signal) {
      // 타입에 맞게 값 변환
      if (signal.type === SignalType.INTEGER && typeof data.value === 'string') {
        signal.value = parseInt(data.value, 10)
      } else {
        signal.value = data.value
      }
    }
  }

  /**
   * 시뮬레이션 결과에서 신호 상태 업데이트
   */
  function updateSignalsFromSimulation(data) {
    // 새로운 globalSignals 형식 우선
    if (data.globalSignals && Array.isArray(data.globalSignals)) {
      data.globalSignals.forEach(simSignal => {
        const signal = globalSignals.value.find(s => s.name === simSignal.name)
        if (signal) {
          signal.value = simSignal.value
          signal.type = simSignal.type || signal.type
        } else {
          // 새로운 신호가 시뮬레이션에서 생성된 경우 자동 추가
          globalSignals.value.push({
            id: simSignal.id || `signal-${Date.now()}-${simSignal.name}`,
            name: simSignal.name,
            type: simSignal.type || inferType(simSignal.value),
            value: simSignal.value,
            initialValue: simSignal.initialValue || simSignal.value
          })
        }
      })
      return
    }
    
    // 기존 currentSignals 형식 (backward compatibility)
    const currentSignals = data.current_signals || data.currentSignals
    if (!currentSignals || typeof currentSignals !== 'object') {
      return
    }

    Object.entries(currentSignals).forEach(([signalName, signalValue]) => {
      const signal = globalSignals.value.find(s => s.name === signalName)
      if (signal) {
        signal.value = signalValue
      } else {
        // 새로운 신호가 시뮬레이션에서 생성된 경우 자동 추가
        globalSignals.value.push({
          id: `signal-${Date.now()}-${signalName}`,
          name: signalName,
          type: inferType(signalValue),
          value: signalValue,
          initialValue: signalValue
        })
      }
    })
  }

  /**
   * 신호 편집 (이름 변경)
   */
  function handleEditGlobalSignal(data) {
    const signalIndex = globalSignals.value.findIndex(s => s.name === data.originalName)
    if (signalIndex !== -1) {
      const existingSignal = globalSignals.value[signalIndex]
      globalSignals.value[signalIndex] = {
        ...existingSignal,
        name: data.newName,
        type: data.type !== undefined ? data.type : existingSignal.type,
        value: data.value !== undefined ? data.value : existingSignal.value,
        initialValue: data.initialValue !== undefined ? data.initialValue : existingSignal.initialValue
      }
    }
  }

  /**
   * 블록에서 신호 참조 업데이트
   */
  function updateSignalReferences(oldName, newName, blocks) {
    blocks.forEach(block => {
      // 블록 액션에서 신호 참조 업데이트
      if (block.actions) {
        block.actions.forEach(action => {
          updateActionSignalReferences(action, oldName, newName)
        })
      }
      
      // 커넥터 액션에서 신호 참조 업데이트
      if (block.connectionPoints) {
        block.connectionPoints.forEach(cp => {
          if (cp.actions) {
            cp.actions.forEach(action => {
              updateActionSignalReferences(action, oldName, newName)
            })
          }
        })
      }
    })
  }

  /**
   * 개별 액션에서 신호 참조 업데이트
   */
  function updateActionSignalReferences(action, oldName, newName) {
    if (action.parameters) {
      // signal_name 파라미터 업데이트
      if (action.parameters.signal_name === oldName) {
        action.parameters.signal_name = newName
      }
      
      // script 파라미터에서 신호명 업데이트 (conditional_branch)
      if (action.parameters.script && typeof action.parameters.script === 'string') {
        action.parameters.script = action.parameters.script.replace(
          new RegExp(`\\b${oldName}\\b`, 'g'),
          newName
        )
      }
    }
    
    // 액션 이름에서도 신호명 업데이트
    if (action.name && action.name.includes(oldName)) {
      action.name = action.name.replace(
        new RegExp(`\\b${oldName}\\b`, 'g'),
        newName
      )
    }
  }

  /**
   * 블록에서 사용되는 모든 신호명 수집
   */
  function collectSignalNamesFromBlocks(blocks) {
    const signalNames = new Set()
    
    blocks.forEach(block => {
      // 블록 액션에서 신호명 수집
      if (block.actions) {
        block.actions.forEach(action => {
          collectActionSignalNames(action, signalNames)
        })
      }
      
      // 커넥터 액션에서 신호명 수집
      if (block.connectionPoints) {
        block.connectionPoints.forEach(cp => {
          if (cp.actions) {
            cp.actions.forEach(action => {
              collectActionSignalNames(action, signalNames)
            })
          }
        })
      }
    })
    
    return Array.from(signalNames)
  }

  /**
   * 개별 액션에서 신호명 수집
   */
  function collectActionSignalNames(action, signalNames) {
    if (action.parameters) {
      if (action.parameters.signal_name) {
        signalNames.add(action.parameters.signal_name)
      }
      
      // script에서 신호명 추출 (간단한 패턴 매칭)
      if (action.parameters.script && typeof action.parameters.script === 'string') {
        const signalMatches = action.parameters.script.match(/(\w+)\s*=\s*(true|false)/g)
        if (signalMatches) {
          signalMatches.forEach(match => {
            const signalName = match.split('=')[0].trim()
            signalNames.add(signalName)
          })
        }
        
        const waitMatches = action.parameters.script.match(/wait\s+(\w+)\s*=\s*(true|false)/g)
        if (waitMatches) {
          waitMatches.forEach(match => {
            const signalName = match.replace(/wait\s+/, '').split('=')[0].trim()
            signalNames.add(signalName)
          })
        }
      }
    }
  }

  /**
   * 모든 신호명 가져오기 (전역 + 블록에서 사용되는 신호)
   */
  function getAllSignalNamesFromBlocks(blocks) {
    const allSignalNames = new Set()
    
    // 전역 신호 추가
    globalSignals.value.forEach(signal => {
      allSignalNames.add(signal.name)
    })
    
    // 블록에서 사용되는 신호 추가
    const blockSignalNames = collectSignalNamesFromBlocks(blocks)
    blockSignalNames.forEach(name => {
      allSignalNames.add(name)
    })
    
    return Array.from(allSignalNames)
  }

  /**
   * 신호 초기화 (시뮬레이션 리셋 시)
   */
  function resetSignalsToInitialValues() {
    globalSignals.value.forEach(signal => {
      if (signal.initialValue !== undefined) {
        signal.value = signal.initialValue
      }
    })
  }

  return {
    // 상태
    globalSignals,
    showGlobalSignalPanel,
    
    // 계산된 속성
    getAllSignalNames,
    
    // 메서드
    setupInitialSignals,
    toggleGlobalSignalPanelVisibility,
    handleCloseGlobalSignalPanel,
    handleAddGlobalSignal,
    handleRemoveGlobalSignal,
    handleUpdateGlobalSignalValue,
    updateSignalsFromSimulation,
    handleEditGlobalSignal,
    updateSignalReferences,
    updateActionSignalReferences,
    collectSignalNamesFromBlocks,
    getAllSignalNamesFromBlocks,
    resetSignalsToInitialValues
  }
} 
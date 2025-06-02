/**
 * 신호 관리 관련 Composable
 * 전역 신호의 생성, 수정, 삭제 및 참조 관리를 담당합니다.
 */

import { ref, computed } from 'vue'

export function useSignals() {
  // 신호 상태
  const globalSignals = ref([])
  const showGlobalSignalPanel = ref(true)

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
    console.log('[useSignals] 전역 신호 설정 로드')
    
    if (baseConfig.globalSignals) {
      globalSignals.value = baseConfig.globalSignals.map(signal => ({
        ...signal,
        // 초기값이 정의되어 있다면 value에 반영
        value: signal.initialValue !== undefined ? signal.initialValue : signal.value
      }))
    }
    
    console.log(`[useSignals] ${globalSignals.value.length}개 전역 신호 로드됨`)
  }

  /**
   * 신호 패널 표시/숨김 토글
   */
  function toggleGlobalSignalPanelVisibility() {
    showGlobalSignalPanel.value = !showGlobalSignalPanel.value
    console.log(`[useSignals] 신호 패널 ${showGlobalSignalPanel.value ? '표시' : '숨김'}`)
  }

  /**
   * 신호 패널 닫기
   */
  function handleCloseGlobalSignalPanel() {
    showGlobalSignalPanel.value = false
    console.log('[useSignals] 신호 패널 닫기')
  }

  /**
   * 새 신호 추가
   */
  function handleAddGlobalSignal(signal) {
    console.log('[useSignals] 새 신호 추가:', signal)
    
    if (!globalSignals.value.find(s => s.name === signal.name)) {
      globalSignals.value.push({
        id: signal.id || `signal-${Date.now()}`,
        name: signal.name,
        value: signal.value !== undefined ? signal.value : false,
        initialValue: signal.initialValue !== undefined ? signal.initialValue : false
      })
      console.log(`[useSignals] 신호 "${signal.name}" 추가됨`)
    } else {
      console.warn(`[useSignals] 이미 존재하는 신호: ${signal.name}`)
    }
  }

  /**
   * 신호 삭제
   */
  function handleRemoveGlobalSignal(signalName) {
    console.log(`[useSignals] 신호 삭제: ${signalName}`)
    
    const index = globalSignals.value.findIndex(s => s.name === signalName)
    if (index !== -1) {
      globalSignals.value.splice(index, 1)
      console.log(`[useSignals] 신호 "${signalName}" 삭제됨`)
    }
  }

  /**
   * 신호 값 업데이트
   */
  function handleUpdateGlobalSignalValue(data) {
    console.log('[useSignals] 신호 값 업데이트:', data)
    
    const signal = globalSignals.value.find(s => s.name === data.name)
    if (signal) {
      signal.value = data.value
      console.log(`[useSignals] 신호 "${data.name}" 값이 ${data.value}로 변경됨`)
    }
  }

  /**
   * 시뮬레이션 결과에서 신호 상태 업데이트
   */
  function updateSignalsFromSimulation(currentSignals) {
    if (!currentSignals || typeof currentSignals !== 'object') {
      return
    }

    console.log('[useSignals] 시뮬레이션에서 신호 상태 업데이트:', currentSignals)
    
    // 시뮬레이션 결과의 신호 상태로 전역 신호 업데이트
    Object.entries(currentSignals).forEach(([signalName, signalValue]) => {
      const signal = globalSignals.value.find(s => s.name === signalName)
      if (signal) {
        const oldValue = signal.value
        signal.value = signalValue
        if (oldValue !== signalValue) {
          console.log(`[useSignals] 신호 "${signalName}" 값이 ${oldValue} → ${signalValue}로 변경됨`)
        }
      } else {
        // 새로운 신호가 시뮬레이션에서 생성된 경우 자동 추가
        console.log(`[useSignals] 새 신호 자동 추가: ${signalName} = ${signalValue}`)
        globalSignals.value.push({
          id: `signal-${Date.now()}-${signalName}`,
          name: signalName,
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
    console.log('[useSignals] 신호 편집:', data)
    
    const signalIndex = globalSignals.value.findIndex(s => s.name === data.originalName)
    if (signalIndex !== -1) {
      globalSignals.value[signalIndex] = {
        ...globalSignals.value[signalIndex],
        name: data.newName,
        value: data.value !== undefined ? data.value : globalSignals.value[signalIndex].value,
        initialValue: data.initialValue !== undefined ? data.initialValue : globalSignals.value[signalIndex].initialValue
      }
      
      console.log(`[useSignals] 신호 "${data.originalName}"이 "${data.newName}"으로 변경됨`)
    }
  }

  /**
   * 블록에서 신호 참조 업데이트
   */
  function updateSignalReferences(oldName, newName, blocks) {
    console.log(`[useSignals] 신호 참조 업데이트: ${oldName} → ${newName}`)
    
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
    console.log('[useSignals] 신호를 초기값으로 리셋')
    
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
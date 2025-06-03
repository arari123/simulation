/**
 * 블록 관리 관련 Composable
 * 블록 생성, 수정, 삭제 및 커넥터 관리를 담당합니다.
 */

import { ref, computed } from 'vue'
import {
  createNewBlock,
  addConnectorToBlock,
  validateBlockName,
  validateConnectorName,
  updateBlockReferences,
  updateConnectorReferences,
  findBlockById,
  findBlockByName,
  findConnectorById,
  generateBlockId,
  generateConnectorId
} from '../utils/BlockManager.js'

export function useBlocks() {
  // 블록 및 연결 상태
  const blocks = ref([])
  const connections = ref([])
  
  // 선택된 요소 상태
  const selectedBlockId = ref(null)
  const selectedConnectorInfo = ref(null)
  
  // 팝업 표시 상태
  const showBlockSettingsPopup = ref(false)
  const showConnectorSettingsPopup = ref(false)

  // 계산된 속성
  const allProcessBlocks = computed(() => blocks.value)
  
  const selectedBlockData = computed(() => {
    if (!selectedBlockId.value) return null
    return blocks.value.find(block => block.id === selectedBlockId.value)
  })

  const currentConnectorData = computed(() => {
    if (!selectedConnectorInfo.value || !selectedConnectorInfo.value.blockId || !selectedConnectorInfo.value.connectorId) return null
    const block = blocks.value.find(b => b.id === selectedConnectorInfo.value.blockId)
    if (!block || !block.connectionPoints) return null
    return block.connectionPoints.find(cp => cp.id === selectedConnectorInfo.value.connectorId)
  })

  /**
   * 새 블록을 캔버스에 추가
   */
  function addNewBlockToCanvas(name, currentSettings) {
    console.log(`[useBlocks] 새 블록 생성 시도: ${name}`)
    
    const validation = validateBlockName(name, blocks.value)
    if (!validation.valid) {
      alert(validation.error)
      return null
    }

    const newBlock = createNewBlock(name, blocks.value, currentSettings)
    blocks.value.push(newBlock)
    
    console.log(`[useBlocks] 새 블록 생성됨:`, newBlock)
    return newBlock
  }

  /**
   * 블록 클릭 처리
   */
  function handleBlockClicked(blockId) {
    console.log(`[useBlocks] 블록 클릭됨: ${blockId}`)
    
    // 선택 해제 요청인 경우
    if (blockId === null) {
      selectedBlockId.value = null
      showBlockSettingsPopup.value = false
      showConnectorSettingsPopup.value = false
      selectedConnectorInfo.value = null
      console.log(`[useBlocks] 모든 선택 해제`)
      return
    }

    // 블록 존재 확인 - 타입 안전한 비교
    const targetBlock = blocks.value.find(b => String(b.id) === String(blockId))
    if (!targetBlock) {
      console.error(`[useBlocks] 블록 ID ${blockId}를 찾을 수 없습니다`)
      console.log(`[useBlocks] 현재 블록 목록:`, blocks.value.map(b => ({ id: b.id, name: b.name, type: typeof b.id })))
      console.log(`[useBlocks] 찾는 blockId:`, blockId, typeof blockId)
      return
    }

    // 커넥터 설정창이 열려있다면 닫기
    if (showConnectorSettingsPopup.value) {
      showConnectorSettingsPopup.value = false
      selectedConnectorInfo.value = null
    }

    // 블록 선택 및 설정창 열기
    selectedBlockId.value = blockId
    showBlockSettingsPopup.value = true
    
    console.log(`[useBlocks] 블록 ${blockId} 선택됨, 설정창 열림`)
  }

  /**
   * 블록 위치 업데이트
   */
  function handleUpdateBlockPosition({ id, x, y }) {
    console.log(`[useBlocks] 블록 ${id} 위치 업데이트: (${x}, ${y})`)
    
    const block = blocks.value.find(b => String(b.id) === String(id))
    if (block) {
      block.x = x
      block.y = y
      console.log(`[useBlocks] 블록 ${id} 위치 업데이트 완료`)
    } else {
      console.error(`[useBlocks] 블록 ID ${id}를 찾을 수 없습니다!`)
      console.log(`[useBlocks] 현재 블록 목록:`, blocks.value.map(b => ({ id: b.id, name: b.name })))
    }
  }

  /**
   * 블록 설정창 닫기
   */
  function closeBlockSettingsPopup() {
    console.log(`[useBlocks] 블록 설정창 닫기`)
    showBlockSettingsPopup.value = false
    // selectedBlockId는 유지 (하이라이트 효과를 위해)
  }

  /**
   * 액션에서 연결 정보 추출
   */
  function extractConnectionsFromActions(actions, sourceBlockId) {
    const connections = []
    
    if (!actions || !Array.isArray(actions)) return connections
    
    actions.forEach(action => {
      if (action.type === 'route_to_connector' && action.parameters) {
        const params = action.parameters
        
        // 다른 블록으로의 라우팅인 경우만 연결 생성
        if (params.target_block_name && params.target_block_name !== 'self') {
          const targetBlock = blocks.value.find(b => b.name === params.target_block_name)
          if (targetBlock) {
            // 대상 커넥터 찾기
            let targetConnectorId = null
            if (params.target_connector_name && targetBlock.connectionPoints) {
              const targetConnector = targetBlock.connectionPoints.find(cp => cp.name === params.target_connector_name)
              targetConnectorId = targetConnector?.id
            }
            
            if (targetConnectorId) {
              connections.push({
                from_block_id: String(sourceBlockId),
                from_connector_id: "block-action", // 블록 액션에서 시작
                to_block_id: String(targetBlock.id),
                to_connector_id: targetConnectorId
              })
            }
          }
        }
      }
      
      // 조건부 실행 스크립트에서도 연결 추출
      if (action.type === 'conditional_branch' && action.parameters?.script) {
        const scriptConnections = extractConnectionsFromScript(action.parameters.script, sourceBlockId)
        connections.push(...scriptConnections)
      }
    })
    
    return connections
  }
  
  /**
   * 스크립트에서 연결 정보 추출
   */
  function extractConnectionsFromScript(script, sourceBlockId) {
    const connections = []
    
    if (!script) return connections
    
    // "go to 블록명.커넥터명" 패턴 찾기
    const goToRegex = /go\s+to\s+([^.\s]+)\.([^,\s]+)/gi
    let match
    
    while ((match = goToRegex.exec(script)) !== null) {
      const targetBlockName = match[1].trim()
      const targetConnectorName = match[2].trim()
      
      // 자기 자신에 대한 참조가 아닌 경우만
      if (targetBlockName !== 'self') {
        const targetBlock = blocks.value.find(b => b.name === targetBlockName)
        if (targetBlock) {
          // 대상 커넥터 찾기
          let targetConnectorId = null
          if (targetBlock.connectionPoints) {
            const targetConnector = targetBlock.connectionPoints.find(cp => cp.name === targetConnectorName)
            targetConnectorId = targetConnector?.id
          }
          
          if (targetConnectorId) {
            connections.push({
              from_block_id: String(sourceBlockId),
              from_connector_id: "block-action", // 스크립트에서 시작
              to_block_id: String(targetBlock.id),
              to_connector_id: targetConnectorId,
              from_conditional_script: true // 조건부 스크립트에서 생성된 연결 표시
            })
          }
        }
      }
    }
    
    return connections
  }
  
  /**
   * 자동 연결 생성
   */
  function createAutoConnections(blockId, actions) {
    const newConnections = extractConnectionsFromActions(actions, blockId)
    
    newConnections.forEach(newConn => {
      // 자동 생성 표시
      newConn.auto_generated = true
      
      // 이미 동일한 연결이 있는지 확인
      const existingConnection = connections.value.find(conn => 
        String(conn.from_block_id) === String(newConn.from_block_id) &&
        String(conn.from_connector_id) === String(newConn.from_connector_id) &&
        String(conn.to_block_id) === String(newConn.to_block_id) &&
        String(conn.to_connector_id) === String(newConn.to_connector_id)
      )
      
      if (!existingConnection) {
        console.log(`[useBlocks] 자동 연결 생성:`, newConn)
        connections.value.push(newConn)
      }
    })
  }

  /**
   * 블록 설정 저장
   */
  function saveBlockSettings(blockId, newActions, maxCapacity, blockName) {
    console.log(`[useBlocks] 블록 ${blockId} 설정 저장:`, { newActions, maxCapacity, blockName })
    
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (block) {
      block.actions = newActions
      if (maxCapacity !== undefined) {
        block.maxCapacity = maxCapacity
      }
      if (blockName && blockName !== block.name) {
        const oldName = block.name
        block.name = blockName
        // 다른 블록에서 이 블록을 참조하는 부분 업데이트
        updateBlockReferences(blocks.value, oldName, blockName)
      }
      
      // 액션에서 자동 연결 생성
      createAutoConnections(blockId, newActions)
      
      console.log(`[useBlocks] 블록 ${blockId} 설정 저장 완료`)
    }
  }

  /**
   * 커넥터 클릭 처리
   */
  function handleConnectorClicked({ blockId, connectorId }) {
    console.log(`[useBlocks] 커넥터 클릭됨: 블록 ${blockId}, 커넥터 ${connectorId}`)
    
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) {
      console.error(`[useBlocks] 블록 ID ${blockId}를 찾을 수 없습니다`)
      return
    }

    const connector = block.connectionPoints.find(cp => cp.id === connectorId)
    if (!connector) {
      console.error(`[useBlocks] 커넥터 ID ${connectorId}를 찾을 수 없습니다`)
      return
    }

    // 블록 설정창이 열려있다면 닫기
    if (showBlockSettingsPopup.value) {
      showBlockSettingsPopup.value = false
      selectedBlockId.value = null
    }

    // 커넥터 선택 및 설정창 열기
    selectedConnectorInfo.value = {
      blockId: blockId,
      connectorId: connectorId,
      blockName: block.name,
      connectorName: connector.name,
      actions: connector.actions || []
    }
    showConnectorSettingsPopup.value = true
    
    console.log(`[useBlocks] 커넥터 ${connectorId} 선택됨, 설정창 열림`, {
      actions: connector.actions?.length || 0
    })
  }

  /**
   * 커넥터 설정창 닫기
   */
  function closeConnectorSettingsPopup() {
    console.log(`[useBlocks] 커넥터 설정창 닫기`)
    showConnectorSettingsPopup.value = false
    // selectedConnectorInfo는 유지 (하이라이트 효과를 위해)
  }

  /**
   * 커넥터 설정 저장
   */
  function saveConnectorSettings(blockId, connectorId, newActions, newName) {
    console.log(`[useBlocks] 커넥터 ${connectorId} 설정 저장:`, { newActions, newName })
    
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) return

    const connector = (block.connectionPoints || []).find(cp => String(cp.id) === String(connectorId))
    if (connector) {
      connector.actions = newActions
      if (newName && newName !== connector.name) {
        const oldName = connector.name
        connector.name = newName
        // 다른 블록에서 이 커넥터를 참조하는 부분 업데이트
        updateConnectorReferences(blocks.value, block.name, oldName, newName)
      }
      
      // 커넥터 액션에서 자동 연결 생성
      createAutoConnectionsFromConnector(blockId, connectorId, newActions)
      
      console.log(`[useBlocks] 커넥터 ${connectorId} 설정 저장 완료`)
    }
  }
  
  /**
   * 커넥터 액션에서 자동 연결 생성
   */
  function createAutoConnectionsFromConnector(blockId, connectorId, actions) {
    const newConnections = extractConnectionsFromActions(actions, blockId)
    
    // 커넥터에서 시작하는 연결로 수정
    newConnections.forEach(newConn => {
      newConn.from_connector_id = connectorId // 블록 액션이 아닌 실제 커넥터 ID 사용
      newConn.auto_generated = true // 자동 생성 표시
      
      // 이미 동일한 연결이 있는지 확인
      const existingConnection = connections.value.find(conn => 
        String(conn.from_block_id) === String(newConn.from_block_id) &&
        String(conn.from_connector_id) === String(newConn.from_connector_id) &&
        String(conn.to_block_id) === String(newConn.to_block_id) &&
        String(conn.to_connector_id) === String(newConn.to_connector_id)
      )
      
      if (!existingConnection) {
        console.log(`[useBlocks] 커넥터에서 자동 연결 생성:`, newConn)
        connections.value.push(newConn)
      }
    })
  }

  /**
   * 블록 복사
   */
  function handleCopyBlock(blockId) {
    const sourceBlock = blocks.value.find(b => String(b.id) === String(blockId))
    if (!sourceBlock) return

    const newName = `${sourceBlock.name} 복사본`
    const validation = validateBlockName(newName, blocks.value)
    if (!validation.valid) {
      alert(`복사 실패: ${validation.error}`)
      return
    }

    const newBlock = JSON.parse(JSON.stringify(sourceBlock))
    newBlock.id = generateBlockId(blocks.value)
    newBlock.name = newName
    newBlock.x += 50
    newBlock.y += 50

    // 커넥터 ID도 새로 생성
    if (newBlock.connectionPoints) {
      newBlock.connectionPoints.forEach(cp => {
        cp.id = generateConnectorId()
      })
    }

    blocks.value.push(newBlock)
    console.log(`[useBlocks] 블록 복사됨:`, newBlock)
  }

  /**
   * 블록 삭제
   */
  function handleDeleteBlock(blockId) {
    const blockIndex = blocks.value.findIndex(b => String(b.id) === String(blockId))
    if (blockIndex === -1) return

    const blockName = blocks.value[blockIndex].name
    
    if (confirm(`"${blockName}" 블록을 삭제하시겠습니까?`)) {
      blocks.value.splice(blockIndex, 1)
      
      // 관련 연결선 제거
      connections.value = connections.value.filter(conn => 
        String(conn.startBlockId) !== String(blockId) && String(conn.endBlockId) !== String(blockId)
      )
      
      // 설정창 닫기
      if (String(selectedBlockId.value) === String(blockId)) {
        showBlockSettingsPopup.value = false
        selectedBlockId.value = null
      }
      
      console.log(`[useBlocks] 블록 ${blockId} 삭제됨`)
    }
  }

  /**
   * 커넥터 추가
   */
  function handleAddConnector(blockId, connectorData) {
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) return

    const validation = validateConnectorName(connectorData.name, block.connectionPoints || [])
    if (!validation.valid) {
      alert(validation.error)
      return
    }

    addConnectorToBlock(block, connectorData)
    console.log(`[useBlocks] 커넥터 추가됨:`, connectorData)
  }

  /**
   * 블록 이름 변경
   */
  function handleChangeBlockName(blockId, newName) {
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) return

    const validation = validateBlockName(newName, blocks.value.filter(b => b.id !== blockId))
    if (!validation.valid) {
      alert(validation.error)
      return
    }

    const oldName = block.name
    block.name = newName
    updateBlockReferences(blocks.value, oldName, newName)
    
    console.log(`[useBlocks] 블록 이름 변경: ${oldName} → ${newName}`)
  }

  /**
   * 커넥터 이름 변경
   */
  function handleChangeConnectorName(blockId, connectorId, newName) {
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) return

    const connector = block.connectionPoints?.find(cp => String(cp.id) === String(connectorId))
    if (!connector) return

    const validation = validateConnectorName(
      newName, 
      block.connectionPoints.filter(cp => cp.id !== connectorId)
    )
    if (!validation.valid) {
      alert(validation.error)
      return
    }

    const oldName = connector.name
    connector.name = newName
    updateConnectorReferences(blocks.value, block.name, oldName, newName)
    
    console.log(`[useBlocks] 커넥터 이름 변경: ${oldName} → ${newName}`)
  }

  /**
   * 모든 블록 액션에서 자동 연결 생성
   */
  function refreshAllAutoConnections() {
    console.log('[useBlocks] 모든 블록에서 자동 연결 새로고침 시작')
    
    // 자동 생성된 연결들 제거 (수동 생성된 연결은 유지)
    const manualConnections = connections.value.filter(conn => !conn.auto_generated)
    
    // 모든 블록의 액션 분석
    blocks.value.forEach(block => {
      // 블록 레벨 액션에서 연결 추출
      if (block.actions && block.actions.length > 0) {
        const blockConnections = extractConnectionsFromActions(block.actions, block.id)
        blockConnections.forEach(conn => {
          conn.auto_generated = true // 자동 생성 표시
          manualConnections.push(conn)
        })
      }
      
      // 커넥터 레벨 액션에서 연결 추출
      if (block.connectionPoints) {
        block.connectionPoints.forEach(connector => {
          if (connector.actions && connector.actions.length > 0) {
            const connectorConnections = extractConnectionsFromActions(connector.actions, block.id)
            connectorConnections.forEach(conn => {
              conn.from_connector_id = connector.id // 실제 커넥터 ID 사용
              conn.auto_generated = true // 자동 생성 표시
              
              // 중복 확인
              const duplicate = manualConnections.find(existing => 
                String(existing.from_block_id) === String(conn.from_block_id) &&
                String(existing.from_connector_id) === String(conn.from_connector_id) &&
                String(existing.to_block_id) === String(conn.to_block_id) &&
                String(existing.to_connector_id) === String(conn.to_connector_id)
              )
              
              if (!duplicate) {
                manualConnections.push(conn)
              }
            })
          }
        })
      }
    })
    
    connections.value = manualConnections
    console.log(`[useBlocks] 자동 연결 새로고침 완료: ${connections.value.length}개 연결`)
  }

  /**
   * 초기 시나리오 설정
   */
  function setupInitialBlocks(baseConfig, currentSettings) {
    console.log('[useBlocks] 기본 블록 설정 로드')
    
    if (baseConfig.blocks) {
      blocks.value = baseConfig.blocks.map(block => ({
        ...block,
        // base.json에 width/height가 있으면 그대로 사용, 없으면 현재 설정 사용
        width: block.width || currentSettings.boxSize,
        height: block.height || currentSettings.boxSize,
        // connectionPoints는 base.json의 원본 위치 정보를 그대로 사용
        connectionPoints: (block.connectionPoints || []).map(cp => ({
          ...cp,
          // base.json에서 정의된 위치를 그대로 사용
          x: cp.x !== undefined ? cp.x : (cp.name === 'R' ? currentSettings.boxSize : 0),
          y: cp.y !== undefined ? cp.y : currentSettings.boxSize / 2
        }))
      }))
    }

    if (baseConfig.connections) {
      connections.value = baseConfig.connections
    }
    
    console.log(`[useBlocks] ${blocks.value.length}개 블록, ${connections.value.length}개 연결 로드됨`)
  }

  /**
   * 설정 업데이트로 블록 크기 조정
   */
  function updateBlocksForSettings(newSettings) {
    console.log('[useBlocks] 설정 변경에 따른 블록 업데이트')
    
    blocks.value = blocks.value.map(b => ({
      ...b,
      width: newSettings.boxSize,
      height: newSettings.boxSize,
      connectionPoints: (b.connectionPoints || []).map(cp => {
        return {
          ...cp,
          x: cp.name === 'R' ? newSettings.boxSize : 0,
          y: newSettings.boxSize / 2
        }
      })
    }))
  }

  return {
    // 상태
    blocks,
    connections,
    selectedBlockId,
    selectedConnectorInfo,
    showBlockSettingsPopup,
    showConnectorSettingsPopup,
    
    // 계산된 속성
    allProcessBlocks,
    selectedBlockData,
    currentConnectorData,
    
    // 메서드
    addNewBlockToCanvas,
    handleBlockClicked,
    handleUpdateBlockPosition,
    closeBlockSettingsPopup,
    saveBlockSettings,
    handleConnectorClicked,
    closeConnectorSettingsPopup,
    saveConnectorSettings,
    handleCopyBlock,
    handleDeleteBlock,
    handleAddConnector,
    handleChangeBlockName,
    handleChangeConnectorName,
    refreshAllAutoConnections,
    setupInitialBlocks,
    updateBlocksForSettings
  }
} 
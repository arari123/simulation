/**
 * 블록 관리 관련 Composable
 * 블록 생성, 수정, 삭제 및 커넥터 관리를 담당합니다.
 */

import { ref, computed } from 'vue'
import {
  createNewBlock,
  addConnectorToBlock,
  addCustomConnectorToBlock,
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
import { validateScript } from '../utils/ScriptUtils.js'

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
    const validation = validateBlockName(name, blocks.value)
    if (!validation.valid) {
      alert(validation.error)
      return null
    }

    const newBlock = createNewBlock(name, blocks.value, currentSettings)
    blocks.value.push(newBlock)
    
    return newBlock
  }

  /**
   * 블록 클릭 처리
   */
  function handleBlockClicked(blockId) {
    // 선택 해제 요청인 경우
    if (blockId === null) {
      selectedBlockId.value = null
      showBlockSettingsPopup.value = false
      showConnectorSettingsPopup.value = false
      selectedConnectorInfo.value = null
      return
    }

    // 블록 존재 확인 - 타입 안전한 비교
    const targetBlock = blocks.value.find(b => String(b.id) === String(blockId))
    if (!targetBlock) {
      console.error(`[useBlocks] 블록 ID ${blockId}를 찾을 수 없습니다`)
      return
    }

    // 커넥터 설정창이 열려있다면 닫기 (커넥터 선택도 해제)
    if (showConnectorSettingsPopup.value || selectedConnectorInfo.value) {
      showConnectorSettingsPopup.value = false
      selectedConnectorInfo.value = null
    }

    // 블록 선택 및 설정창 열기
    selectedBlockId.value = blockId
    showBlockSettingsPopup.value = true
  }

  /**
   * 블록 위치 업데이트
   */
  function handleUpdateBlockPosition({ id, x, y }) {
    const block = blocks.value.find(b => String(b.id) === String(id))
    if (block) {
      block.x = x
      block.y = y
    } else {
      console.error(`[useBlocks] 블록 ID ${id}를 찾을 수 없습니다!`)
    }
  }

  /**
   * 커넥터 위치 업데이트
   */
  function handleUpdateConnectorPosition({ blockId, connectorId, x, y }) {
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (block && block.connectionPoints) {
      const connector = block.connectionPoints.find(cp => String(cp.id) === String(connectorId))
      if (connector) {
        connector.x = x
        connector.y = y
      } else {
        console.error(`[useBlocks] 커넥터 ID ${connectorId}를 찾을 수 없습니다!`)
      }
    } else {
      console.error(`[useBlocks] 블록 ID ${blockId}를 찾을 수 없습니다!`)
    }
  }

  /**
   * 블록 설정창 닫기
   */
  function closeBlockSettingsPopup() {
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
      
      // 스크립트 타입 액션에서도 연결 추출
      if (action.type === 'script' && action.parameters?.script) {
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
    
    
    // 현재 블록 찾기 (출발 커넥터 찾기 위해)
    const sourceBlock = blocks.value.find(b => String(b.id) === String(sourceBlockId))
    
    // "go from 커넥터명 to 블록명.커넥터명" 패턴 찾기 (새로운 형식)
    const goFromToRegex = /go\s+from\s+([^\s]+)\s+to\s+([^.\s]+)\.([^,\s]+)/gi
    let match
    
    while ((match = goFromToRegex.exec(script)) !== null) {
      const fromConnectorName = match[1].trim()
      const targetBlockName = match[2].trim()
      const targetConnectorName = match[3].trim()
      
      
      // 출발 커넥터 찾기
      let fromConnectorId = null
      if (sourceBlock && sourceBlock.connectionPoints) {
        const fromConnector = sourceBlock.connectionPoints.find(cp => cp.name === fromConnectorName)
        fromConnectorId = fromConnector?.id
        
        if (!fromConnector) {
          continue
        }
      }
      
      // 대상 블록과 커넥터 찾기
      if (targetBlockName !== 'self') {
        const targetBlock = blocks.value.find(b => b.name === targetBlockName)
        if (targetBlock) {
          
          // 대상 커넥터 찾기
          let targetConnectorId = null
          if (targetBlock.connectionPoints) {
            const targetConnector = targetBlock.connectionPoints.find(cp => cp.name === targetConnectorName)
            targetConnectorId = targetConnector?.id
            
            if (targetConnector) {
            } else {
              continue
            }
          }
          
          if (fromConnectorId && targetConnectorId) {
            const newConnection = {
              from_block_id: String(sourceBlockId),
              from_connector_id: fromConnectorId, // 실제 출발 커넥터 ID 사용
              to_block_id: String(targetBlock.id),
              to_connector_id: targetConnectorId,
              from_conditional_script: true
            }
            connections.push(newConnection)
          }
        } else {
        }
      }
    }
    
    // 기존 "go to 블록명.커넥터명" 패턴도 계속 지원 (하위 호환성)
    const goToRegex = /go\s+to\s+([^.\s]+)\.([^,\s]+)/gi
    goToRegex.lastIndex = 0 // 정규식 재설정
    
    while ((match = goToRegex.exec(script)) !== null) {
      // go from이 아닌 경우만 처리
      const fullMatch = match[0]
      if (!fullMatch.includes('from')) {
        const targetBlockName = match[1].trim()
        const targetConnectorName = match[2].trim()
        
        
        // 자기 자신에 대한 참조가 아닌 경우만
        if (targetBlockName !== 'self') {
          const targetBlock = blocks.value.find(b => b.name === targetBlockName)
          if (targetBlock) {
            let targetConnectorId = null
            if (targetBlock.connectionPoints) {
              const targetConnector = targetBlock.connectionPoints.find(cp => cp.name === targetConnectorName)
              targetConnectorId = targetConnector?.id
            }
            
            if (targetConnectorId) {
              const newConnection = {
                from_block_id: String(sourceBlockId),
                from_connector_id: "block-action", // 기존 형식은 블록 중앙에서 시작
                to_block_id: String(targetBlock.id),
                to_connector_id: targetConnectorId,
                from_conditional_script: true
              }
              connections.push(newConnection)
            }
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
    // 이 블록에서 시작하는 자동 생성 연결들을 모두 제거
    connections.value = connections.value.filter(conn => 
      !(String(conn.from_block_id) === String(blockId) && conn.auto_generated)
    )
    
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
        connections.value.push(newConn)
      }
    })
  }

  /**
   * 블록 설정 저장
   */
  function saveBlockSettings(blockId, newActions, maxCapacity, blockName) {
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
      
      // 스크립트 타입 액션이 있으면 전체 연결 새로고침
      const hasScriptAction = newActions.some(action => action.type === 'script')
      if (hasScriptAction) {
        console.log('[saveBlockSettings] 스크립트 액션 감지 - 전체 연결 새로고침')
        refreshAllAutoConnections()
      } else {
        // 일반 액션은 기존처럼 처리
        createAutoConnections(blockId, newActions)
      }
    }
  }

  /**
   * 커넥터 클릭 처리
   */
  function handleConnectorClicked({ blockId, connectorId }) {
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
  }

  /**
   * 커넥터 설정창 닫기
   */
  function closeConnectorSettingsPopup() {
    showConnectorSettingsPopup.value = false
    // selectedConnectorInfo는 유지 (하이라이트 효과를 위해)
  }

  /**
   * 커넥터 설정 저장
   */
  function saveConnectorSettings(blockId, connectorId, newActions, newName) {
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
        String(conn.from_block_id) !== String(blockId) && String(conn.to_block_id) !== String(blockId)
      )
      
      // 설정창 닫기
      if (String(selectedBlockId.value) === String(blockId)) {
        showBlockSettingsPopup.value = false
        selectedBlockId.value = null
      }
      
      // 자동 연결 새로고침
      refreshAllAutoConnections()
    }
  }

  /**
   * 커넥터 추가
   */
  function handleAddConnector(blockId, connectorData) {
    console.log('[handleAddConnector] 호출됨:', { blockId, connectorData })
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block) return

    const validation = validateConnectorName(connectorData.name, block.connectionPoints || [])
    if (!validation.valid) {
      alert(validation.error)
      return
    }

    const newConnector = addCustomConnectorToBlock(block, connectorData)
    console.log('[handleAddConnector] 커넥터 추가 완료:', newConnector)
    
    // 새 커넥터 추가 시 연결선 새로고침하지 않음
    // (커넥터를 추가했다고 해서 자동으로 연결이 생성되지는 않음)
    // refreshAllAutoConnections()
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
  }

  /**
   * 커넥터 삭제
   */
  function handleDeleteConnector(blockId, connectorId) {
    const block = blocks.value.find(b => String(b.id) === String(blockId))
    if (!block || !block.connectionPoints) return

    const connectorIndex = block.connectionPoints.findIndex(cp => String(cp.id) === String(connectorId))
    if (connectorIndex === -1) return

    const connector = block.connectionPoints[connectorIndex]
    
    console.log(`[handleDeleteConnector] 커넥터 삭제: ${block.name}.${connector.name}`)
    
    // 1. 이 커넥터와 관련된 모든 연결선 제거
    const removedConnections = connections.value.filter(conn => 
      (String(conn.from_block_id) === String(blockId) && String(conn.from_connector_id) === String(connectorId)) ||
      (String(conn.to_block_id) === String(blockId) && String(conn.to_connector_id) === String(connectorId))
    )
    
    connections.value = connections.value.filter(conn => 
      !(String(conn.from_block_id) === String(blockId) && String(conn.from_connector_id) === String(connectorId)) &&
      !(String(conn.to_block_id) === String(blockId) && String(conn.to_connector_id) === String(connectorId))
    )
    
    console.log(`[handleDeleteConnector] ${removedConnections.length}개 연결선 제거`)
    
    // 2. 커넥터를 블록에서 제거
    block.connectionPoints.splice(connectorIndex, 1)
    
    // 3. 설정창 닫기
    if (selectedConnectorInfo.value && 
        String(selectedConnectorInfo.value.blockId) === String(blockId) && 
        String(selectedConnectorInfo.value.connectorId) === String(connectorId)) {
      showConnectorSettingsPopup.value = false
      selectedConnectorInfo.value = null
    }
    
    // 4. 자동 연결 새로고침 (스크립트에서 참조하는 커넥터가 삭제된 경우 대응)
    refreshAllAutoConnections()
    
    console.log(`[handleDeleteConnector] 커넥터 삭제 완료`)
  }

  /**
   * 모든 블록 액션에서 자동 연결 생성
   */
  function refreshAllAutoConnections() {
    
    // 강제로 모든 연결을 제거하고 처음부터 다시 생성 (중복 문제 해결)
    connections.value = []
    
    // 새로운 자동 연결을 위한 배열
    const newAutoConnections = []
    
    // 모든 블록의 액션 분석
    blocks.value.forEach(block => {
      // 블록 레벨 액션에서 연결 추출
      if (block.actions && block.actions.length > 0) {
        const blockConnections = extractConnectionsFromActions(block.actions, block.id)
        blockConnections.forEach(conn => {
          conn.auto_generated = true // 자동 생성 표시
          newAutoConnections.push(conn)
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
              newAutoConnections.push(conn)
            })
          }
        })
      }
    })
    
    // 중복 제거
    const uniqueConnections = []
    newAutoConnections.forEach(newConn => {
      const isDuplicate = uniqueConnections.some(existing => 
        String(existing.from_block_id) === String(newConn.from_block_id) &&
        String(existing.from_connector_id) === String(newConn.from_connector_id) &&
        String(existing.to_block_id) === String(newConn.to_block_id) &&
        String(existing.to_connector_id) === String(newConn.to_connector_id)
      )
      
      if (!isDuplicate) {
        uniqueConnections.push(newConn)
      } else {
      }
    })
    
    // 최종 연결 목록 = 고유한 자동 연결만
    connections.value = uniqueConnections
    
  }

  /**
   * 초기 시나리오 설정
   */
  function setupInitialBlocks(baseConfig, currentSettings) {
    if (baseConfig.blocks) {
      blocks.value = baseConfig.blocks.map(block => {
        const processedBlock = {
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
        };
        
        // script 필드가 있고 actions 배열에 script 타입 액션이 없으면 추가
        if (processedBlock.script && processedBlock.script.trim()) {
          const hasScriptAction = processedBlock.actions?.some(action => action.type === 'script');
          
          if (!hasScriptAction) {
            // actions 배열이 없으면 생성
            if (!processedBlock.actions) {
              processedBlock.actions = [];
            }
            
            // script 타입 액션 추가
            processedBlock.actions.push({
              id: `script-action-${Date.now()}-${block.id}`,
              name: '스크립트 실행',
              type: 'script',
              parameters: {
                script: processedBlock.script
              }
            });
          }
        }
        
        return processedBlock;
      })
    }

    if (baseConfig.connections) {
      // 모든 초기 연결을 자동 생성된 것으로 표시
      connections.value = baseConfig.connections.map(conn => ({
        ...conn,
        auto_generated: true
      }))
    }
  }

  /**
   * 설정 업데이트로 블록 크기 조정
   */
  function updateBlocksForSettings(newSettings) {
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

  /**
   * 블록의 스크립트 오류 검사
   */
  function getBlockScriptErrors(block) {
    const errors = []
    
    // 모든 신호명 수집 (현재는 빈 배열, 추후 확장 가능)
    const allSignals = []
    
    // 블록 액션의 스크립트 검사
    if (block.actions && block.actions.length > 0) {
      for (const action of block.actions) {
        if (action.type === 'script' && action.parameters?.script) {
          const validationResult = validateScript(
            action.parameters.script,
            allSignals,
            blocks.value,
            block,
            'block'
          )
          if (!validationResult.valid) {
            errors.push(...validationResult.errors.map(err => `블록 스크립트: ${err}`))
          }
        }
      }
    }
    
    // 커넥터 액션의 스크립트 검사
    if (block.connectionPoints && block.connectionPoints.length > 0) {
      for (const connector of block.connectionPoints) {
        if (connector.actions && connector.actions.length > 0) {
          for (const action of connector.actions) {
            if (action.type === 'script' && action.parameters?.script) {
              const validationResult = validateScript(
                action.parameters.script,
                allSignals,
                blocks.value,
                block,
                'connector'
              )
              if (!validationResult.valid) {
                errors.push(...validationResult.errors.map(err => `커넥터 "${connector.name}": ${err}`))
              }
            }
          }
        }
      }
    }
    
    return errors
  }

  /**
   * 모든 블록의 스크립트 오류 상태 계산
   */
  const blocksWithErrors = computed(() => {
    const errorMap = new Map()
    
    for (const block of blocks.value) {
      const errors = getBlockScriptErrors(block)
      if (errors.length > 0) {
        errorMap.set(block.id, {
          block,
          errors,
          errorCount: errors.length
        })
      }
    }
    
    return errorMap
  })

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
    blocksWithErrors,
    
    // 메서드
    addNewBlockToCanvas,
    handleBlockClicked,
    handleUpdateBlockPosition,
    handleUpdateConnectorPosition,
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
    handleDeleteConnector,
    refreshAllAutoConnections,
    setupInitialBlocks,
    updateBlocksForSettings,
    getBlockScriptErrors
  }
} 
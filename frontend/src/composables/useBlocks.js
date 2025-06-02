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

    // 블록 존재 확인
    const targetBlock = blocks.value.find(b => b.id === blockId)
    if (!targetBlock) {
      console.error(`[useBlocks] 블록 ID ${blockId}를 찾을 수 없습니다`)
      console.log(`[useBlocks] 현재 블록 목록:`, blocks.value.map(b => ({ id: b.id, name: b.name })))
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
    
    const block = blocks.value.find(b => b.id === id)
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
   * 블록 설정 저장
   */
  function saveBlockSettings(blockId, newActions, maxCapacity, blockName) {
    console.log(`[useBlocks] 블록 ${blockId} 설정 저장:`, { newActions, maxCapacity, blockName })
    
    const block = blocks.value.find(b => b.id === blockId)
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
      console.log(`[useBlocks] 블록 ${blockId} 설정 저장 완료`)
    }
  }

  /**
   * 커넥터 클릭 처리
   */
  function handleConnectorClicked({ blockId, connectorId }) {
    console.log(`[useBlocks] 커넥터 클릭됨: 블록 ${blockId}, 커넥터 ${connectorId}`)
    
    const block = blocks.value.find(b => b.id === blockId)
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
    
    const block = blocks.value.find(b => b.id === blockId)
    if (!block) return

    const connector = (block.connectionPoints || []).find(cp => cp.id === connectorId)
    if (connector) {
      connector.actions = newActions
      if (newName && newName !== connector.name) {
        const oldName = connector.name
        connector.name = newName
        // 다른 블록에서 이 커넥터를 참조하는 부분 업데이트
        updateConnectorReferences(blocks.value, block.name, oldName, newName)
      }
      console.log(`[useBlocks] 커넥터 ${connectorId} 설정 저장 완료`)
    }
  }

  /**
   * 블록 복사
   */
  function handleCopyBlock(blockId) {
    const sourceBlock = blocks.value.find(b => b.id === blockId)
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
    const blockIndex = blocks.value.findIndex(b => b.id === blockId)
    if (blockIndex === -1) return

    const blockName = blocks.value[blockIndex].name
    
    if (confirm(`"${blockName}" 블록을 삭제하시겠습니까?`)) {
      blocks.value.splice(blockIndex, 1)
      
      // 관련 연결선 제거
      connections.value = connections.value.filter(conn => 
        conn.startBlockId !== blockId && conn.endBlockId !== blockId
      )
      
      // 설정창 닫기
      if (selectedBlockId.value === blockId) {
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
    const block = blocks.value.find(b => b.id === blockId)
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
    const block = blocks.value.find(b => b.id === blockId)
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
    const block = blocks.value.find(b => b.id === blockId)
    if (!block) return

    const connector = block.connectionPoints?.find(cp => cp.id === connectorId)
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
    setupInitialBlocks,
    updateBlocksForSettings
  }
} 
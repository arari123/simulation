/**
 * 블록과 커넥터 관리 유틸리티
 * 블록/커넥터의 생성, 수정, 삭제, 이름/ID 관리를 중앙화
 */

// 블록 ID 생성
export function generateBlockId(existingBlocks = []) {
  const maxId = existingBlocks.length > 0 ? Math.max(...existingBlocks.map(b => b.id)) : 0;
  return maxId + 1;
}

// 커넥터 ID 생성
export function generateConnectorId(blockId, connectorName, position) {
  // 표준화된 ID 형식: {blockId}-conn-{position}
  const sanitizedName = connectorName.toLowerCase().replace(/\s+/g, '-');
  return `${blockId}-conn-${position || sanitizedName}`;
}

// 블록 이름 유효성 검사
export function validateBlockName(name, existingBlocks = [], excludeId = null) {
  if (!name || !name.trim()) {
    return { valid: false, error: '블록 이름을 입력해주세요.' };
  }
  
  const trimmedName = name.trim();
  
  // 중복 이름 검사
  const isDuplicate = existingBlocks.some(block => 
    block.name === trimmedName && String(block.id) !== String(excludeId)
  );
  
  if (isDuplicate) {
    return { valid: false, error: '이미 사용 중인 블록 이름입니다.' };
  }
  
  return { valid: true };
}

// 커넥터 이름 유효성 검사
export function validateConnectorName(name, existingConnectors = [], excludeId = null) {
  if (!name || !name.trim()) {
    return { valid: false, error: '커넥터 이름을 입력해주세요.' };
  }
  
  const trimmedName = name.trim();
  
  // 중복 이름 검사
  const isDuplicate = existingConnectors.some(connector => 
    connector.name === trimmedName && String(connector.id) !== String(excludeId)
  );
  
  if (isDuplicate) {
    return { valid: false, error: '이미 사용 중인 커넥터 이름입니다.' };
  }
  
  return { valid: true };
}

// 표준 커넥터 생성
export function createStandardConnector(blockId, position, customName = null) {
  const positions = {
    'left': { x: 0, name: 'L' },
    'right': { x: 100, name: 'R' },  // 실제 x는 boxSize로 교체됨
    'top': { x: 50, name: 'T' },
    'bottom': { x: 50, name: 'B' }
  };
  
  const config = positions[position];
  if (!config) {
    throw new Error(`지원하지 않는 커넥터 위치: ${position}`);
  }
  
  return {
    id: generateConnectorId(blockId, customName || config.name, position),
    name: customName || config.name,
    x: config.x,
    y: 50, // 실제 y는 boxSize/2로 교체됨
    position: position,
    actions: []
  };
}

// 새 블록 생성
export function createNewBlock(name, existingBlocks = [], settings = { boxSize: 100 }) {
  const id = generateBlockId(existingBlocks);
  
  // 블록 위치 계산 (그리드 형태로 배치)
  const gridCols = 5;
  const col = (existingBlocks.length) % gridCols;
  const row = Math.floor(existingBlocks.length / gridCols);
  const spacing = 50;
  
  const x = col * (settings.boxSize + spacing) + 50;
  const y = row * (settings.boxSize + spacing) + 150;
  
  return {
    id: id,
    name: name,
    x: x + (Math.random() * 20 - 10), // 약간의 랜덤 오프셋
    y: y + (Math.random() * 20 - 10),
    width: settings.boxSize,
    height: settings.boxSize,
    maxCapacity: 1,
    actions: [],
    connectionPoints: [
      createStandardConnector(id, 'left'),
      createStandardConnector(id, 'right')
    ]
  };
}

// 블록에 커넥터 추가
export function addConnectorToBlock(block, position, customName = null, settings = { boxSize: 100 }) {
  if (!block.connectionPoints) {
    block.connectionPoints = [];
  }
  
  const newConnector = createStandardConnector(block.id, position, customName);
  
  // 위치 조정
  if (position === 'left') {
    newConnector.x = 0;
    newConnector.y = settings.boxSize / 2;
  } else if (position === 'right') {
    newConnector.x = settings.boxSize;
    newConnector.y = settings.boxSize / 2;
  } else if (position === 'top') {
    newConnector.x = settings.boxSize / 2;
    newConnector.y = 0;
  } else if (position === 'bottom') {
    newConnector.x = settings.boxSize / 2;
    newConnector.y = settings.boxSize;
  }
  
  block.connectionPoints.push(newConnector);
  return newConnector;
}

// 블록에 사용자 정의 커넥터 추가 (새로운 함수)
export function addCustomConnectorToBlock(block, connectorData) {
  if (!block.connectionPoints) {
    block.connectionPoints = [];
  }
  
  // 커넥터 데이터 검증 및 기본값 설정
  const newConnector = {
    id: connectorData.id || `connector-${Date.now()}`,
    name: connectorData.name || `연결점${block.connectionPoints.length + 1}`,
    x: connectorData.x || 50,
    y: connectorData.y || 50,
    actions: connectorData.actions || []
  };
  
  block.connectionPoints.push(newConnector);
  return newConnector;
}

// 블록 찾기 (ID 또는 이름으로)
export function findBlockById(blocks, id) {
  return blocks.find(block => String(block.id) === String(id));
}

export function findBlockByName(blocks, name) {
  return blocks.find(block => block.name === name);
}

// 커넥터 찾기
export function findConnectorById(block, connectorId) {
  if (!block || !block.connectionPoints) return null;
  return block.connectionPoints.find(cp => String(cp.id) === String(connectorId));
}

export function findConnectorByName(block, connectorName) {
  if (!block || !block.connectionPoints) return null;
  return block.connectionPoints.find(cp => cp.name === connectorName);
}

// 커넥터 ID를 이름으로 변환
export function connectorIdToName(connectorId, block = null) {
  if (!connectorId) return connectorId;
  
  // 블록이 제공된 경우 실제 커넥터에서 이름 찾기
  if (block) {
    const connector = findConnectorById(block, connectorId);
    if (connector && connector.name) {
      return connector.name;
    }
  }
  
  // ID 패턴에서 이름 추출
  if (connectorId.includes('left') || connectorId.includes('input') || connectorId.includes('load')) {
    return 'L';
  } else if (connectorId.includes('right') || connectorId.includes('output') || connectorId.includes('unload')) {
    return 'R';
  } else if (connectorId.includes('top') || connectorId.includes('up')) {
    return 'T';
  } else if (connectorId.includes('bottom') || connectorId.includes('down')) {
    return 'B';
  }
  
  return connectorId;
}

// 블록/커넥터 참조 업데이트
export function updateBlockReferences(blocks, oldBlockName, newBlockName) {
  blocks.forEach(block => {
    // 블록 액션 업데이트
    if (block.actions) {
      block.actions.forEach(action => {
        updateActionBlockReferences(action, oldBlockName, newBlockName);
      });
    }
    
    // 커넥터 액션 업데이트
    if (block.connectionPoints) {
      block.connectionPoints.forEach(connector => {
        if (connector.actions) {
          connector.actions.forEach(action => {
            updateActionBlockReferences(action, oldBlockName, newBlockName);
          });
        }
      });
    }
  });
}

export function updateConnectorReferences(blocks, blockName, oldConnectorName, newConnectorName) {
  blocks.forEach(block => {
    // 블록 액션 업데이트
    if (block.actions) {
      block.actions.forEach(action => {
        updateActionConnectorReferences(action, blockName, oldConnectorName, newConnectorName);
      });
    }
    
    // 커넥터 액션 업데이트
    if (block.connectionPoints) {
      block.connectionPoints.forEach(connector => {
        if (connector.actions) {
          connector.actions.forEach(action => {
            updateActionConnectorReferences(action, blockName, oldConnectorName, newConnectorName);
          });
        }
      });
    }
  });
}

// 헬퍼 함수들
function updateActionBlockReferences(action, oldBlockName, newBlockName) {
  if (!action || !action.type) return;
  
  if (action.type === 'conditional_branch' && action.parameters?.script) {
    let script = action.parameters.script;
    
    // go to 블록이름.커넥터 패턴 업데이트
    const goToRegex = new RegExp(`(go\\s+to\\s+)${escapeRegExp(oldBlockName)}(\\.[\\w-]+)`, 'g');
    script = script.replace(goToRegex, `$1${newBlockName}$2`);
    
    // 신호 이름에서 블록 이름 참조 업데이트
    const signalRegex = new RegExp(`(^|\\s|=\\s*)${escapeRegExp(oldBlockName)}(\\s+\\w+)`, 'g');
    script = script.replace(signalRegex, `$1${newBlockName}$2`);
    
    action.parameters.script = script;
  }
}

function updateActionConnectorReferences(action, blockName, oldConnectorName, newConnectorName) {
  if (!action || !action.type) return;
  
  if (action.type === 'conditional_branch' && action.parameters?.script) {
    let script = action.parameters.script;
    
    // go to 블록이름.커넥터이름 패턴 업데이트
    const goToRegex = new RegExp(`(go\\s+to\\s+${escapeRegExp(blockName)}\\.)${escapeRegExp(oldConnectorName)}\\b`, 'g');
    script = script.replace(goToRegex, `$1${newConnectorName}`);
    
    action.parameters.script = script;
  }
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// 스크립트 변환 유틸리티
export function convertActionToScript(action, context = {}) {
  if (!action || !action.type) {
    return `// 행동 타입이 정의되지 않음`;
  }
  
  try {
    switch (action.type) {
      case 'delay':
        const duration = action.parameters?.duration || 5;
        return `delay ${duration}`;
        
      case 'signal_check':
        const checkSignal = action.parameters?.signal_name || '신호명';
        const expectedValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `if ${checkSignal} = ${expectedValue}`;
        
      case 'signal_update':
        const updateSignal = action.parameters?.signal_name || '신호명';
        const newValue = action.parameters?.value === true ? 'true' : 'false';
        return `${updateSignal} = ${newValue}`;
        
      case 'signal_wait':
        const waitSignal = action.parameters?.signal_name || '신호명';
        const waitValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `wait ${waitSignal} = ${waitValue}`;
        
      case 'route_to_connector':
        return convertRouteActionToScript(action, context);
        
      case 'action_jump':
        const targetActionName = action.parameters?.target_action_name;
        if (targetActionName && context.editableActions) {
          const targetIndex = context.editableActions.findIndex(a => a.name === targetActionName);
          if (targetIndex !== -1) {
            return `jump to ${targetIndex + 1}`;
          }
        }
        return `// jump to ${targetActionName || '대상 없음'} (대상을 찾을 수 없음)`;
        
      case 'block_entry':
        // 블록으로 이동 액션을 스크립트로 변환
        const blockName = action.parameters?.target_block_name || '블록명';
        const entryDelay = action.parameters?.delay || '1';
        return `go to self.${blockName},${entryDelay}`;
        
      case 'conditional_branch':
        const script = action.parameters?.script || '';
        if (script.trim()) {
          // 원본 스크립트를 그대로 반환 (들여쓰기 추가하지 않음)
          return script;
        }
        return `// 조건부 실행 스크립트가 정의되지 않음`;
        
      case 'script_error':
        // 오류 액션은 원래 스크립트 라인을 그대로 반환하되 주석 처리
        const originalLine = action.parameters?.originalLine || '';
        const error = action.parameters?.error || '알 수 없는 오류';
        return `// ❌ 오류: ${error}\n// ${originalLine}`;
        
      case 'script':
        // script 타입 액션은 저장된 스크립트를 그대로 반환
        const savedScript = action.parameters?.script || '';
        if (savedScript.trim()) {
          return savedScript;
        }
        return `// 스크립트가 비어있음`;
        
      default:
        return `// ${action.type} 타입은 스크립트 변환을 지원하지 않음`;
    }
  } catch (error) {
    console.error(`액션 변환 오류:`, error);
    return `// 변환 오류: ${action.name || '이름없음'}`;
  }
}

function convertRouteActionToScript(action, context) {
  if (action.parameters?.target_block_id && action.parameters?.target_connector_id) {
    // 다른 블록으로 이동
    const targetBlockId = action.parameters.target_block_id;
    const targetConnectorId = action.parameters.target_connector_id;
    const delay = action.parameters?.delay || 0;
    
    // 저장된 이름이 있으면 우선 사용
    const blockName = action.parameters?.target_block_name || 
                     (context.allBlocks ? findBlockById(context.allBlocks, targetBlockId)?.name : null) || 
                     `블록${targetBlockId}`;
                     
    const connectorName = action.parameters?.target_connector_name || 
                         connectorIdToName(targetConnectorId, context.allBlocks ? findBlockById(context.allBlocks, targetBlockId) : null);
    
    if (targetConnectorId === 'self') {
      return delay > 0 ? `go to ${blockName},${delay}` : `go to ${blockName}`;
    } else {
      return delay > 0 ? `go to ${blockName}.${connectorName},${delay}` : `go to ${blockName}.${connectorName}`;
    }
  } else if (action.parameters?.connector_id) {
    // 현재 블록 내 연결점으로 이동
    const connectorId = action.parameters.connector_id;
    const delay = action.parameters?.delay || 0;
    
    if (connectorId === 'self') {
      const currentBlockName = context.currentBlockName || 'block';
      return delay > 0 ? `go to self.${currentBlockName},${delay}` : `go to self.${currentBlockName}`;
    } else {
      // 저장된 커넥터 이름이 있으면 우선 사용
      const connectorName = action.parameters?.target_connector_name || 
                           connectorIdToName(connectorId, context.currentBlock);
      return delay > 0 ? `go to self.${connectorName},${delay}` : `go to self.${connectorName}`;
    }
  }
  
  return `// go to 대상이 명확하지 않음`;
} 
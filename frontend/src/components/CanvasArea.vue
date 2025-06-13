<template>
  <div class="canvas-area" ref="canvasContainerRef">
    <div id="konva-container"></div>
    <div class="zoom-controls">
      <button @click="zoomIn">확대 (+)</button>
      <button @click="zoomOut">축소 (-)</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, toRaw, nextTick } from 'vue';
import Konva from 'konva';
import { computed } from 'vue';

// Props for settings
const props = defineProps({
  blocks: {
    type: Array,
    default: () => []
  },
  connections: {
    type: Array,
    default: () => []
  },
  currentSettings: {
    type: Object,
    default: () => ({ boxSize: 100, fontSize: 14 })
  },
  blocksWithErrors: {
    type: Map,
    default: () => new Map()
  },
  activeEntityStates: {
    type: Array,
    default: () => []
  },
  selectedBlockId: {
    type: [Number, String, null],
    default: null
  },
  selectedConnectorInfo: {
    type: Object,
    default: null
  },
  showBlockSettingsPopup: {
    type: Boolean,
    default: false
  },
  showConnectorSettingsPopup: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits([
  'select-block',
  'select-connector',
  'update-block-position',
  'update-connector-position',
]);

const canvasContainerRef = ref(null);
let stage = null;
let layer = null;
let gridLayer = null;
const zoomFactor = 1.1;

const entityTextGroup = ref(null);

// RAF 최적화를 위한 변수
let drawScheduled = false;
let gridDrawScheduled = false;

// 전역 엔티티 ID -> 번호 매핑
const globalEntityIdToNumber = new Map();
let globalNextEntityNumber = 1;

function initKonva() {
  
  if (!canvasContainerRef.value) {
    return;
  }

  // 기존 stage가 있으면 제거
  if (stage) {
    stage.destroy();
    stage = null;
  }

  // 컨테이너 내부의 기존 Konva 요소들 정리
  const container = canvasContainerRef.value;
  if (container) {
    // konva로 생성된 div들 제거
    const existingKonvaContainers = container.querySelectorAll('div[style*="position"]');
    existingKonvaContainers.forEach(el => {
      if (el !== container && !el.classList.contains('zoom-controls')) {
        el.remove();
      }
    });
  }

  // 컨테이너의 실제 크기 확인 - 여러 방법으로 시도
  const containerRect = container.getBoundingClientRect();
  let width = Math.max(
    container.clientWidth || 0,
    container.offsetWidth || 0, 
    containerRect.width || 0,
    800 // 최소값
  );
  let height = Math.max(
    container.clientHeight || 0,
    container.offsetHeight || 0,
    containerRect.height || 0,
    600 // 최소값
  );
  
  
  // 크기가 여전히 0이면 부모 크기 기반 계산
  if (width <= 0 || height <= 0) {
    const parent = container.parentElement;
    if (parent) {
      width = Math.max(parent.clientWidth - 50, 800);
      height = Math.max(parent.clientHeight - 50, 600);
    }
  }
  

  try {
    stage = new Konva.Stage({
      container: container,
      width: width,
      height: height,
      draggable: true, // Stage 드래그 활성화
    });


    // Stage 컨테이너 스타일 설정
    const stageContainer = stage.container();
    if (stageContainer) {
      stageContainer.style.zIndex = '1';
      stageContainer.style.position = 'relative';
      stageContainer.style.width = '100%';
      stageContainer.style.height = '100%';
      stageContainer.style.display = 'block';
      
      // Canvas 요소 확인 (디버깅용 색상 제거)
      setTimeout(() => {
        const canvas = stageContainer.querySelector('canvas');
        if (canvas) {
        } else {
        }
      }, 100);
    }
    
    return true; // 성공
  } catch (error) {
    return false; // 실패
  }
}

// 성능 최적화: 부분 렌더링을 위한 상태 관리
const blockNodes = ref(new Map())
const connectionNodes = ref(new Map())
const entityNodes = ref(new Map())
const dirtyFlags = ref({
  blocks: new Set(), // 변경된 블록 ID들
  connections: new Set(), // 변경된 연결 ID들
  entities: new Set(), // 변경된 엔티티 ID들
  all: false // 전체 다시 그리기 필요 여부
})

// 이전 상태 저장 (변경 감지용)
const previousStates = ref({
  blocks: new Map(),
  entities: new Map()
})

// 드래그 중인 커넥터의 임시 위치 저장
const temporaryConnectorPositions = ref(new Map())

function drawCanvasContent() {
  
  if (!layer || !stage) {
    return;
  }
  
  // 엔티티 그룹 초기화 (한 번만 필요)
  if (!entityTextGroup.value) {
    entityTextGroup.value = new Konva.Group();
    layer.add(entityTextGroup.value);
    entityTextGroup.value.moveToTop();
  }

  // 전체 다시 그리기가 필요한 경우
  if (dirtyFlags.value.all) {
    updateBlocks();
    updateEntities();
    updateConnections();
    dirtyFlags.value.all = false;
    dirtyFlags.value.blocks.clear();
    dirtyFlags.value.entities.clear();
    dirtyFlags.value.connections.clear();
  } else {
    // 변경된 블록만 업데이트
    if (dirtyFlags.value.blocks.size > 0) {
      dirtyFlags.value.blocks.forEach(blockId => {
        const blockData = props.blocks.find(b => String(b.id) === String(blockId));
        if (blockData) {
          updateSingleBlock(blockData);
        }
      });
      dirtyFlags.value.blocks.clear();
    }
    
    // 변경된 엔티티만 업데이트
    if (dirtyFlags.value.entities.size > 0) {
      updateEntities(); // TODO: 개별 엔티티 업데이트로 최적화
      dirtyFlags.value.entities.clear();
    }
    
    // 변경된 연결만 업데이트
    if (dirtyFlags.value.connections.size > 0) {
      updateConnections(); // TODO: 개별 연결 업데이트로 최적화
      dirtyFlags.value.connections.clear();
    }
  }
  
  if (props.blocks.length === 0) {
    scheduleLayerDraw();
    return;
  }
  
  // 레이어 순서 재정렬: 연결선 -> 블록 -> 엔티티
  ensureLayerOrder();
  
  // RAF를 사용한 배치 드로우
  scheduleLayerDraw();
}

// RequestAnimationFrame을 사용한 레이어 드로우 스케줄링
function scheduleLayerDraw() {
  if (!drawScheduled && layer) {
    drawScheduled = true;
    requestAnimationFrame(() => {
      if (layer) {
        layer.draw();
      }
      drawScheduled = false;
    });
  }
}

// RequestAnimationFrame을 사용한 그리드 드로우 스케줄링
function scheduleGridDraw() {
  if (!gridDrawScheduled && gridLayer) {
    gridDrawScheduled = true;
    requestAnimationFrame(() => {
      if (gridLayer) {
        gridLayer.draw();
      }
      gridDrawScheduled = false;
    });
  }
}

// 변경 감지 및 더티 플래그 설정
function detectChanges() {
  // 블록 변경 감지
  props.blocks.forEach(block => {
    const blockId = String(block.id);
    const prevBlock = previousStates.value.blocks.get(blockId);
    
    if (!prevBlock || hasBlockChanged(prevBlock, block)) {
      dirtyFlags.value.blocks.add(blockId);
      // 블록 상태 저장
      previousStates.value.blocks.set(blockId, {
        ...block,
        status: block.status,
        totalProcessed: block.totalProcessed,
        backgroundColor: block.backgroundColor,
        textColor: block.textColor,
        warnings: block.warnings ? [...block.warnings] : []
      });
    }
  });
  
  // 제거된 블록 찾기
  previousStates.value.blocks.forEach((prevBlock, blockId) => {
    if (!props.blocks.find(b => String(b.id) === blockId)) {
      dirtyFlags.value.blocks.add(blockId);
      previousStates.value.blocks.delete(blockId);
    }
  });
  
  // 엔티티 변경 감지
  const currentEntityMap = new Map();
  props.activeEntityStates.forEach(entity => {
    currentEntityMap.set(entity.id, entity);
  });
  
  // 새로운 또는 변경된 엔티티
  currentEntityMap.forEach((entity, entityId) => {
    const prevEntity = previousStates.value.entities.get(entityId);
    if (!prevEntity || hasEntityChanged(prevEntity, entity)) {
      dirtyFlags.value.entities.add(entityId);
      // 관련 블록도 더티로 표시
      if (prevEntity && prevEntity.current_block_id !== entity.current_block_id) {
        dirtyFlags.value.blocks.add(String(prevEntity.current_block_id));
        dirtyFlags.value.blocks.add(String(entity.current_block_id));
      }
    }
  });
  
  // 제거된 엔티티
  previousStates.value.entities.forEach((prevEntity, entityId) => {
    if (!currentEntityMap.has(entityId)) {
      dirtyFlags.value.entities.add(entityId);
      dirtyFlags.value.blocks.add(String(prevEntity.current_block_id));
    }
  });
  
  // 현재 상태 저장
  previousStates.value.entities = currentEntityMap;
}

// 블록 변경 감지 헬퍼
function hasBlockChanged(oldBlock, newBlock) {
  return oldBlock.x !== newBlock.x ||
         oldBlock.y !== newBlock.y ||
         oldBlock.status !== newBlock.status ||
         oldBlock.totalProcessed !== newBlock.totalProcessed ||
         oldBlock.backgroundColor !== newBlock.backgroundColor ||
         oldBlock.textColor !== newBlock.textColor ||
         JSON.stringify(oldBlock.warnings) !== JSON.stringify(newBlock.warnings);
}

// 엔티티 변경 감지 헬퍼
function hasEntityChanged(oldEntity, newEntity) {
  return oldEntity.current_block_id !== newEntity.current_block_id ||
         oldEntity.state !== newEntity.state ||
         oldEntity.color !== newEntity.color ||
         JSON.stringify(oldEntity.custom_attributes) !== JSON.stringify(newEntity.custom_attributes);
}

// 레이어 순서를 보장하는 함수
function ensureLayerOrder() {
  // 1. 모든 블록을 맨 아래로
  blockNodes.value.forEach(blockGroup => {
    blockGroup.moveToBottom();
  });
  
  // 2. 엔티티 그룹을 블록 위로
  if (entityTextGroup.value) {
    entityTextGroup.value.moveToTop();
  }
  
  // 3. 모든 연결선을 최상단으로
  connectionNodes.value.forEach(arrow => {
    arrow.moveToTop();
  });
}

function updateBlocks() {
  
  // 기존 블록 중 더 이상 존재하지 않는 것들 제거
  const currentBlockIds = new Set(props.blocks.map(b => b.id.toString()));
  for (const [blockId, blockGroup] of blockNodes.value) {
    if (!currentBlockIds.has(blockId)) {
      // 레이어에서 이 블록의 커넥터들도 제거
      if (layer) {
        const connectorsToRemove = [];
        layer.children.forEach(child => {
          if (child.attrs && String(child.attrs.blockId) === String(blockId) && 
              (child.attrs.connectorId || child.attrs.isDragHandle)) {
            connectorsToRemove.push(child);
          }
        });
        connectorsToRemove.forEach(child => child.destroy());
      }
      
      blockGroup.destroy();
      blockNodes.value.delete(blockId);
    }
  }
  
  // 새로운 블록 또는 변경된 블록 업데이트
  props.blocks.forEach(blockData => {
    updateSingleBlock(blockData);
  });
}

function updateSingleBlock(blockData) {
  const blockId = blockData.id.toString();
  let blockGroup = blockNodes.value.get(blockId);
  
  // 디버그: totalProcessed 값 확인
  if (blockData.totalProcessed !== undefined) {
    // totalProcessed 값이 설정됨
  }
  
  if (!blockGroup) {
    // 새 블록 생성
    blockGroup = createBlockGroup(blockData);
    blockNodes.value.set(blockId, blockGroup);
    layer.add(blockGroup);
  } else {
    // 기존 블록 업데이트
    updateBlockGroup(blockGroup, blockData);
  }
}

function createBlockGroup(blockData) {
  
  const isBlockSelected = props.selectedBlockId && String(props.selectedBlockId) === String(blockData.id);
  
  const blockGroup = new Konva.Group({
    id: 'block-' + blockData.id.toString(),
    x: blockData.x,
    y: blockData.y,
    draggable: false, // 초기에는 드래그 불가능
  });

  // 블록 사각형
  const rect = new Konva.Rect({
    width: blockData.width || props.currentSettings.boxSize,
    height: blockData.height || props.currentSettings.boxSize,
    fill: blockData.backgroundColor || '#cfdff7',
    stroke: 'black',
    strokeWidth: 2,
  });
  blockGroup.add(rect);
  
  // 블록 내용 추가
  addBlockContent(blockGroup, blockData);
  
  // 이벤트 리스너 추가
  addBlockEventListeners(blockGroup, blockData);
  
  return blockGroup;
}

function updateBlockGroup(blockGroup, blockData) {
  // 위치 업데이트
  blockGroup.x(blockData.x);
  blockGroup.y(blockData.y);
  
  // 선택 상태에 따라 드래그 설정
  const isBlockSelected = props.selectedBlockId && String(props.selectedBlockId) === String(blockData.id);
  blockGroup.draggable(isBlockSelected);
  
  // 레이어에서 이 블록의 커넥터들 정리 (선택된 커넥터가 레이어에 있을 수 있음)
  if (layer) {
    const connectorsToRemove = [];
    layer.children.forEach(child => {
      if (child.attrs && String(child.attrs.blockId) === String(blockData.id) && 
          (child.attrs.connectorId || child.attrs.isDragHandle)) {
        connectorsToRemove.push(child);
      }
    });
    connectorsToRemove.forEach(child => child.destroy());
  }
  
  // 내용 업데이트
  blockGroup.destroyChildren();
  addBlockContent(blockGroup, blockData);
  
  // 블록 이벤트 리스너 재설정
  addBlockEventListeners(blockGroup, blockData);
}

function addBlockContent(blockGroup, blockData) {
  // 블록 선택 상태 확인
  const isBlockSelected = props.selectedBlockId && String(props.selectedBlockId) === String(blockData.id);
  
  // 블록 사각형 - 색상은 선택 상태와 무관하게 유지
  const rect = new Konva.Rect({
    width: blockData.width || props.currentSettings.boxSize,
    height: blockData.height || props.currentSettings.boxSize,
    fill: blockData.backgroundColor || '#cfdff7',
    stroke: isBlockSelected ? '#2196F3' : 'black', // 선택된 경우 파란색 테두리
    strokeWidth: isBlockSelected ? 3 : 2, // 선택된 경우 더 두껍게
  });
  blockGroup.add(rect);

  // 선택된 블록인 경우 드래그 가능 표시 (파란색 점선)
  if (isBlockSelected) {
    const highlightRect = new Konva.Rect({
      width: (blockData.width || props.currentSettings.boxSize) + 8,
      height: (blockData.height || props.currentSettings.boxSize) + 8,
      x: -4,
      y: -4,
      fill: 'transparent',
      stroke: '#4A90E2', // 파란색으로 변경
      strokeWidth: 3,
      dash: [8, 4],
      opacity: 0.8
    });
    blockGroup.add(highlightRect);
    
    
    // 선택 인디케이터 (모서리 점)
    const corners = [
      { x: -6, y: -6 }, // 왼쪽 위
      { x: (blockData.width || props.currentSettings.boxSize) + 2, y: -6 }, // 오른쪽 위
      { x: -6, y: (blockData.height || props.currentSettings.boxSize) + 2 }, // 왼쪽 아래
      { x: (blockData.width || props.currentSettings.boxSize) + 2, y: (blockData.height || props.currentSettings.boxSize) + 2 } // 오른쪽 아래
    ];
    
    corners.forEach(corner => {
      const cornerSquare = new Konva.Rect({
        x: corner.x,
        y: corner.y,
        width: 8,
        height: 8,
        fill: '#FF6B35',
        stroke: 'white',
        strokeWidth: 1
      });
      blockGroup.add(cornerSquare);
    });
  }

  // 블록 제목
  const blockTitle = new Konva.Text({
    text: blockData.name,
    fontSize: props.currentSettings.fontSize,
    fill: blockData.textColor || '#000000',
    align: 'center',
    width: blockData.width || props.currentSettings.boxSize,
    x: 0,
    y: 5,
  });
  blockGroup.add(blockTitle);

  // 용량 정보 - 엔티티 수/최대 용량
  const entitiesInThisBlock = props.activeEntityStates.filter(entity => 
    String(entity.current_block_id) === String(blockData.id)
  );
  
  
  const capacityTextString = `${entitiesInThisBlock.length}/${blockData.maxCapacity || 1}`;
  
  const capacityText = new Konva.Text({
    text: capacityTextString,
    fontSize: props.currentSettings.fontSize * 0.6,
    fill: entitiesInThisBlock.length >= (blockData.maxCapacity || 1) ? 'red' : 'gray',
    align: 'center',
    width: blockData.width || props.currentSettings.boxSize,
    x: 0,
    y: (props.currentSettings.fontSize + 5),
  });
  blockGroup.add(capacityText);
  
  // 블록 상태 표시 (status) - 블록 상단에 표시
  if (blockData.status) {
    const statusText = new Konva.Text({
      text: `[${blockData.status}]`,
      fontSize: props.currentSettings.fontSize * 0.7,
      fill: '#666',
      align: 'center',
      width: blockData.width || props.currentSettings.boxSize,
      x: 0,
      y: -20,  // 블록 상단 위에 표시
      fontStyle: 'italic'
    });
    blockGroup.add(statusText);
  }
  
  // 처리된 엔티티 수 표시 - 블록 내부 하단에 표시하도록 변경
  if (blockData.totalProcessed !== undefined && blockData.totalProcessed > 0) {
    // Block has totalProcessed value
    const blockHeight = blockData.height || props.currentSettings.boxSize;
    const blockWidth = blockData.width || props.currentSettings.boxSize;
    
    // 배경 사각형 - 블록 내부 하단에 표시
    const bgRect = new Konva.Rect({
      x: 5,
      y: blockHeight - 30,
      width: blockWidth - 10,
      height: 25,
      fill: '#E8F5E9',
      stroke: '#2E7D32',
      strokeWidth: 1,
      cornerRadius: 3
    });
    blockGroup.add(bgRect);
    
    const processedText = new Konva.Text({
      text: `처리: ${blockData.totalProcessed}`,
      fontSize: props.currentSettings.fontSize * 0.9,
      fill: '#1B5E20', // 진한 녹색
      align: 'center',
      width: blockWidth - 10,
      x: 5,
      y: blockHeight - 25,
      fontStyle: 'bold'
    });
    blockGroup.add(processedText);
    
    // Added processed text display
  }

  // 경고 메시지 표시 (용량 초과 등)
  if (blockData.warnings && blockData.warnings.length > 0) {
    const latestWarning = blockData.warnings[blockData.warnings.length - 1]; // 가장 최근 경고
    // 경고 메시지는 블록 내부 하단에 표시
    const warningYPos = (props.currentSettings.fontSize * 1.8 + 10);
      
    const warningText = new Konva.Text({
      text: `⚠️ 용량 초과`,
      fontSize: props.currentSettings.fontSize * 0.5,
      fill: 'red',
      align: 'center',
      width: blockData.width || props.currentSettings.boxSize,
      x: 0,
      y: warningYPos,
      fontStyle: 'bold'
    });
    blockGroup.add(warningText);
    
    // 경고 배경 (선택적)
    const warningBg = new Konva.Rect({
      width: (blockData.width || props.currentSettings.boxSize) - 4,
      height: props.currentSettings.fontSize * 0.7,
      x: 2,
      y: warningYPos - 2,
      fill: 'rgba(255, 0, 0, 0.1)',
      stroke: 'red',
      strokeWidth: 1,
      cornerRadius: 3
    });
    blockGroup.add(warningBg);
    // 경고 텍스트를 배경 위에 올리기
    warningText.moveToTop();
  }

  // 스크립트 오류 표시
  const blockError = props.blocksWithErrors.get(blockData.id);
  if (blockError) {
    // 오류가 있는 블록의 테두리를 빨간색으로 변경
    rect.stroke('red');
    rect.strokeWidth(3);
    
    // 오류 아이콘 표시
    const errorIcon = new Konva.Text({
      text: '❌',
      fontSize: props.currentSettings.fontSize * 0.8,
      fill: 'red',
      x: (blockData.width || props.currentSettings.boxSize) - 20,
      y: 5,
      fontStyle: 'bold'
    });
    blockGroup.add(errorIcon);
    
    // 오류 개수 표시
    const errorCountText = new Konva.Text({
      text: `${blockError.errorCount}개 오류`,
      fontSize: props.currentSettings.fontSize * 0.4,
      fill: 'red',
      x: (blockData.width || props.currentSettings.boxSize) - 40,
      y: 25,
      fontStyle: 'bold'
    });
    blockGroup.add(errorCountText);
    
    // 오류 툴팁 (마우스 오버 시 표시용 데이터 추가)
    blockGroup.errorDetails = blockError.errors;
  }

  // 커넥터 추가
  if (blockData.connectionPoints) {
    blockData.connectionPoints.forEach(cp => {
      // 선택된 커넥터인지 확인
      const isSelected = props.selectedConnectorInfo && 
                        String(props.selectedConnectorInfo.blockId) === String(blockData.id) && 
                        String(props.selectedConnectorInfo.connectorId) === String(cp.id);
      
      // 현재 커넥터의 실제 위치 찾기 (이동했을 수 있으므로)
      const currentBlock = props.blocks.find(b => String(b.id) === String(blockData.id));
      const currentConnector = currentBlock?.connectionPoints?.find(conn => String(conn.id) === String(cp.id));
      
      // 임시 위치가 있으면 그것을 사용, 없으면 props에서 가져오기
      const tempPosKey = `${blockData.id}-${cp.id}`;
      const tempPos = temporaryConnectorPositions.value.get(tempPosKey);
      const connectorX = tempPos?.x ?? currentConnector?.x ?? cp.x;
      const connectorY = tempPos?.y ?? currentConnector?.y ?? cp.y;
      
      
      const connectorCircle = new Konva.Circle({
        x: connectorX,
        y: connectorY,
        radius: isSelected ? 12 : 8, // 선택된 경우 더 크게
        fill: isSelected ? '#FF6B35' : 'orange', // 선택된 경우 다른 색상
        stroke: isSelected ? '#D63031' : 'darkorange',
        strokeWidth: isSelected ? 3 : 2, // 선택된 경우 더 두꺿게
        draggable: false, // 초기에는 드래그 불가능 (나중에 레이어에서 활성화)
        stopPropagation: false, // 이벤트 전파 허용
        connectorId: cp.id, // 커넥터 ID 저장
        blockId: blockData.id, // 블록 ID 저장
      });
      
      // 커서 스타일 설정
      connectorCircle.on('mouseenter', () => {
        if (isSelected) {
          document.body.style.cursor = 'move';
        } else {
          document.body.style.cursor = 'pointer';
        }
      });
      
      connectorCircle.on('mouseleave', () => {
        document.body.style.cursor = 'default';
      });
      
      // 선택된 커넥터에만 추가 설정
      if (isSelected) {
        // 수동 드래그 구현을 위한 변수
        let isManualDragging = false;
        let dragStartMousePos = null;
        let dragStartConnectorPos = null;
        
        // 이벤트 핸들러 함수들을 저장하여 나중에 제거할 수 있도록 함
        const mouseMoveHandler = function() {
          if (isManualDragging && dragStartMousePos && dragStartConnectorPos) {
            const currentMousePos = stage.getPointerPosition();
            if (currentMousePos) {
              const deltaX = currentMousePos.x - dragStartMousePos.x;
              const deltaY = currentMousePos.y - dragStartMousePos.y;
              
              const newX = dragStartConnectorPos.x + deltaX;
              const newY = dragStartConnectorPos.y + deltaY;
              
              connectorCircle.position({
                x: newX,
                y: newY
              });
              
              // 드래그 핸들(파란 점선)도 함께 이동
              if (layer) {
                const dragHandle = layer.children.find(child => 
                  child.attrs && child.attrs.isDragHandle && 
                  String(child.attrs.connectorId) === String(cp.id) && 
                  String(child.attrs.blockId) === String(blockData.id)
                );
                if (dragHandle) {
                  dragHandle.position({
                    x: newX,
                    y: newY
                  });
                }
              }
              
              // 라벨과 배경도 함께 이동 (블록 기준 상대 좌표로 변환)
              if (connectorCircle.connectorLabel && connectorCircle.labelBg) {
                const relativePos = {
                  x: newX - blockGroup.x(),
                  y: newY - blockGroup.y()
                };
                connectorCircle.labelBg.x(relativePos.x - 18);
                connectorCircle.labelBg.y(relativePos.y - 28);
                connectorCircle.connectorLabel.x(relativePos.x - 15);
                connectorCircle.connectorLabel.y(relativePos.y - 25);
              }
              
              // 연결선 실시간 업데이트
              updateConnectionsForBlock(blockData.id);
              scheduleLayerDraw();
            }
          }
        };
        
        const mouseUpHandler = function() {
          if (isManualDragging) {
            isManualDragging = false;
            document.body.style.cursor = 'move';
            
            // 여기서 영역 제한과 자석 효과 적용
            applyConstraintsAndSnap();
            
            // 커넥터 드래그 완료 후 stage 드래그 다시 활성화
            stage.draggable(true);
            
            // 이벤트 리스너 제거
            stage.off('mousemove', mouseMoveHandler);
            stage.off('mouseup', mouseUpHandler);
          }
        };
        
        // 커넥터 hover 이벤트
        connectorCircle.on('mouseenter', () => {
          document.body.style.cursor = 'move';
        });
        
        connectorCircle.on('mouseleave', () => {
          if (!isManualDragging) {
            document.body.style.cursor = 'default';
          }
        });
        
        // 마우스 다운 - 수동 드래그 시작
        connectorCircle.on('mousedown', function(e) {
          e.cancelBubble = true;
          if (stage) {
            isManualDragging = true;
            dragStartMousePos = stage.getPointerPosition();
            dragStartConnectorPos = connectorCircle.position();
            document.body.style.cursor = 'grabbing';
            
            // 커넥터 드래그 중에는 stage 드래그 비활성화
            stage.draggable(false);
            
            // 이벤트 리스너 추가
            stage.on('mousemove', mouseMoveHandler);
            stage.on('mouseup', mouseUpHandler);
          }
        });
        
        // 영역 제한과 자석 효과를 적용하는 함수
        function applyConstraintsAndSnap() {
          const blockSize = blockData.width || props.currentSettings.boxSize;
          const snapThreshold = 25;
          const margin = 20;
          
          const currentBlock = props.blocks.find(b => String(b.id) === String(blockData.id));
          const blockX = currentBlock?.x || blockData.x || 0;
          const blockY = currentBlock?.y || blockData.y || 0;
          
          const currentPos = connectorCircle.position();
          let constrainedX = currentPos.x;
          let constrainedY = currentPos.y;
          
          // 1단계: 영역 제한
          const relativeX = currentPos.x - blockX;
          const relativeY = currentPos.y - blockY;
          
          if (relativeX < -margin) {
            constrainedX = blockX - margin;
          } else if (relativeX > blockSize + margin) {
            constrainedX = blockX + blockSize + margin;
          }
          
          if (relativeY < -margin) {
            constrainedY = blockY - margin;
          } else if (relativeY > blockSize + margin) {
            constrainedY = blockY + blockSize + margin;
          }
          
          // 2단계: 자석 효과
          const constrainedRelativeX = constrainedX - blockX;
          const constrainedRelativeY = constrainedY - blockY;
          
          const distToLeft = Math.abs(constrainedRelativeX);
          const distToRight = Math.abs(constrainedRelativeX - blockSize);
          const distToTop = Math.abs(constrainedRelativeY);
          const distToBottom = Math.abs(constrainedRelativeY - blockSize);
          
          let finalX = constrainedX;
          let finalY = constrainedY;
          
          if (distToLeft < snapThreshold && distToLeft <= Math.min(distToRight, distToTop, distToBottom)) {
            finalX = blockX;
            finalY = blockY + Math.max(0, Math.min(blockSize, constrainedRelativeY));
          } else if (distToRight < snapThreshold && distToRight <= Math.min(distToLeft, distToTop, distToBottom)) {
            finalX = blockX + blockSize;
            finalY = blockY + Math.max(0, Math.min(blockSize, constrainedRelativeY));
          } else if (distToTop < snapThreshold && distToTop <= Math.min(distToLeft, distToRight, distToBottom)) {
            finalY = blockY;
            finalX = blockX + Math.max(0, Math.min(blockSize, constrainedRelativeX));
          } else if (distToBottom < snapThreshold && distToBottom <= Math.min(distToLeft, distToRight, distToTop)) {
            finalY = blockY + blockSize;
            finalX = blockX + Math.max(0, Math.min(blockSize, constrainedRelativeX));
          }
          
          
          // 임시 위치 저장 (블록 기준 상대 좌표)
          const tempPosKey = `${blockData.id}-${cp.id}`;
          const finalRelativePos = {
            x: finalX - blockX,
            y: finalY - blockY
          };
          temporaryConnectorPositions.value.set(tempPosKey, finalRelativePos);
          
          // 최종 위치로 모든 요소 이동
          connectorCircle.position({
            x: finalX,
            y: finalY
          });
          
          // 드래그 핸들도 최종 위치로 이동
          if (layer) {
            const dragHandle = layer.children.find(child => 
              child.attrs && child.attrs.isDragHandle && 
              String(child.attrs.connectorId) === String(cp.id) && 
              String(child.attrs.blockId) === String(blockData.id)
            );
            if (dragHandle) {
              dragHandle.position({
                x: finalX,
                y: finalY
              });
            }
          }
          
          // 라벨과 배경도 최종 위치로 이동
          if (connectorCircle.connectorLabel && connectorCircle.labelBg) {
            connectorCircle.labelBg.x(finalRelativePos.x - 18);
            connectorCircle.labelBg.y(finalRelativePos.y - 28);
            connectorCircle.connectorLabel.x(finalRelativePos.x - 15);
            connectorCircle.connectorLabel.y(finalRelativePos.y - 25);
          }
          
          
          // emit을 통해 부모 컴포넌트에 위치 업데이트 요청
          emit('update-connector-position', {
            blockId: blockData.id,
            connectorId: cp.id,
            x: finalRelativePos.x,
            y: finalRelativePos.y
          });
          
          // 연결선 업데이트
          updateConnectionsForBlock(blockData.id);
          
          // 강제로 다시 그리기
          scheduleLayerDraw();
          
          // props 업데이트 후 임시 위치 정리
          setTimeout(() => {
            temporaryConnectorPositions.value.delete(tempPosKey);
          }, 100);
        }
      }
      
            // 드래그 관련 변수
      let isDragging = false;
      let connectorLabel = null;
      let labelBg = null;
      let dragHandleCircle = null; // 드래그 핸들
      
      // 마우스 이벤트로 클릭과 드래그 구분
      connectorCircle.on('mousedown', (e) => {
        e.cancelBubble = true;
        if (e.evt) e.evt.stopPropagation(); // 블록 이벤트 방지
      });
      
      connectorCircle.on('mouseup', (e) => {
        e.cancelBubble = true;
        if (e.evt) e.evt.stopPropagation(); // 블록 이벤트 방지
      });
      
      // 커넥터 클릭 이벤트 - 활성화/비활성화
      connectorCircle.on('click', (e) => {
        e.cancelBubble = true;
        if (e.evt) e.evt.stopPropagation(); // 블록 이벤트 방지
        emit('select-connector', {
          blockId: blockData.id,
          connectorId: cp.id
        });
      });
      // 선택된 커넥터에 드래그 핸들 추가
      if (isSelected) {
        // 드래그 핸들 표시 (파란색 테두리)
        dragHandleCircle = new Konva.Circle({
          x: cp.x,
          y: cp.y,
          radius: 14,
          stroke: '#4A90E2',
          strokeWidth: 2,
          fill: 'transparent',
          dash: [2, 2],
          isDragHandle: true, // 정리 시 식별용
          listening: false // 이벤트 받지 않음
        });
        
        // 커넥터에 드래그 핸들 참조 저장
        connectorCircle.dragHandleCircle = dragHandleCircle;
      }
      
      // 기존 Konva 드래그 이벤트는 선택된 커넥터에서는 사용하지 않음
      
      // 선택된 커넥터는 레이어에 직접 추가하여 독립적으로 드래그 가능하게 함
      if (isSelected && layer) {
        // 이미 레이어에 같은 커넥터가 있는지 확인
        const existingConnector = layer.children.find(child => 
          child.attrs && String(child.attrs.connectorId) === String(cp.id) && 
          String(child.attrs.blockId) === String(blockData.id)
        );
        
        if (!existingConnector) {
          // 현재 커넥터 위치 저장 (제거되기 전에)
          const currentPos = connectorCircle.position();
          const currentAbsX = blockGroup.x() + currentPos.x;
          const currentAbsY = blockGroup.y() + currentPos.y;
          
          // 커넥터를 블록그룹에서 제거
          connectorCircle.remove();
          
          // 절대 위치로 설정
          connectorCircle.position({
            x: currentAbsX,
            y: currentAbsY
          });
          
          // 커넥터에 블록 참조 저장 (dragBoundFunc에서 사용)
          connectorCircle.blockGroup = blockGroup;
          
          // 레이어에 직접 추가
          layer.add(connectorCircle);
          connectorCircle.moveToTop(); // 최상단으로 이동
          
          // 수동 드래그를 사용하므로 기본 드래그 비활성화
          connectorCircle.draggable(false);
          connectorCircle.listening(true);
          
          // 드래그 가능한 영역 표시를 위한 설정
          connectorCircle.perfectDrawEnabled(false); // 성능 향상
          
          // 레이어 다시 그리기 강제 실행
          scheduleLayerDraw();
        }
      } else {
        // 선택되지 않은 커넥터는 그룹에 추가
        blockGroup.add(connectorCircle);
      }
      
      // 드래그 핸들 추가
      if (dragHandleCircle) {
        if (isSelected && layer) {
          // 이미 레이어에 드래그 핸들이 있는지 확인
          const existingHandle = layer.children.find(child => 
            child.attrs && child.attrs.isDragHandle && 
            String(child.attrs.connectorId) === String(cp.id) && 
            String(child.attrs.blockId) === String(blockData.id)
          );
          
          if (!existingHandle) {
            // 현재 커넥터의 실제 위치 찾기 (임시 위치 포함)
            const currentBlock = props.blocks.find(b => String(b.id) === String(blockData.id));
            const currentConnector = currentBlock?.connectionPoints?.find(conn => String(conn.id) === String(cp.id));
            
            // 임시 위치가 있으면 그것을 사용, 없으면 props에서 가져오기
            const tempPosKey = `${blockData.id}-${cp.id}`;
            const tempPos = temporaryConnectorPositions.value.get(tempPosKey);
            const connectorX = tempPos?.x ?? currentConnector?.x ?? cp.x;
            const connectorY = tempPos?.y ?? currentConnector?.y ?? cp.y;
            
            // 선택된 커넥터의 드래그 핸들도 레이어에 직접 추가
            dragHandleCircle.position({
              x: blockGroup.x() + connectorX,
              y: blockGroup.y() + connectorY
            });
            dragHandleCircle.attrs.connectorId = cp.id;
            dragHandleCircle.attrs.blockId = blockData.id;
            layer.add(dragHandleCircle);
            dragHandleCircle.moveToTop();
          }
        } else {
          blockGroup.add(dragHandleCircle);
        }
      }
      
      // 커넥터 라벨 추가 (항상 표시)
      if (cp.name) {
        // 이름이 4글자를 넘으면 잘라서 표시
        const displayName = cp.name.length > 4 ? cp.name.substring(0, 4) : cp.name;
        
        connectorLabel = new Konva.Text({
          x: cp.x - 15,
          y: cp.y - 25,
          text: displayName,
          fontSize: 9,
          fill: '#2D3436',
          fontStyle: 'bold',
          align: 'center',
          width: 30,
          // 배경 색상
          padding: 2,
        });
        
        // 라벨 배경
        labelBg = new Konva.Rect({
          x: cp.x - 18,
          y: cp.y - 28,
          width: 36,
          height: 16,
          fill: 'white',
          stroke: '#DDD',
          strokeWidth: 1,
          cornerRadius: 3,
          opacity: 0.9
        });
        
        // 커넥터에 라벨과 배경 참조 저장
        connectorCircle.labelBg = labelBg;
        connectorCircle.connectorLabel = connectorLabel;
        
        blockGroup.add(labelBg);
        blockGroup.add(connectorLabel);
      }
      
    });
  }
}

function addBlockEventListeners(blockGroup, blockData) {
  let isDragging = false;
  let dragStartPos = null;
  let mouseDownTime = 0;
  let mouseDownPos = null;

  // 마우스 다운 - 드래그와 클릭의 시작점
  blockGroup.on('mousedown', (e) => {
    // 커넥터에서 발생한 이벤트는 무시
    if (e.target !== blockGroup && e.target.getClassName() === 'Circle') {
      return;
    }
    
    isDragging = false;
    mouseDownTime = Date.now();
    mouseDownPos = stage.getPointerPosition();
    dragStartPos = { x: blockGroup.x(), y: blockGroup.y() };
  });

  // 마우스 업 - 클릭 감지를 위한 최종 검증
  blockGroup.on('mouseup', (e) => {
    // 커넥터에서 발생한 이벤트는 무시
    if (e.target !== blockGroup && e.target.getClassName() === 'Circle') {
      return;
    }
    
    const clickDuration = Date.now() - mouseDownTime;
    const currentMousePos = stage.getPointerPosition();
    
    // 마우스 이동 거리 계산
    let mouseMoveDistance = 0;
    if (mouseDownPos && currentMousePos) {
      mouseMoveDistance = Math.sqrt(
        Math.pow(currentMousePos.x - mouseDownPos.x, 2) + 
        Math.pow(currentMousePos.y - mouseDownPos.y, 2)
      );
    }
    
    // 클릭으로 판단: 시간이 짧고(500ms 이하), 마우스 이동이 적고(10px 이하), 드래그 중이 아닌 경우
    if (clickDuration < 500 && mouseMoveDistance < 10 && !isDragging) {
      emit('select-block', blockData.id);
      // 블록이 선택되면 드래그 가능하도록 설정
      if (!blockGroup.draggable()) {
        blockGroup.draggable(true);
      }
    } else {
    }
  });

  // 드래그 시작
  blockGroup.on('dragstart', () => {
    // 드래그가 실제로 시작되면 즉시 드래그 상태로 설정
    isDragging = true;
  });

  // 드래그 중
  blockGroup.on('dragmove', () => {
    const currentPos = { x: blockGroup.x(), y: blockGroup.y() };
    if (dragStartPos && (
      Math.abs(currentPos.x - dragStartPos.x) > 5 || 
      Math.abs(currentPos.y - dragStartPos.y) > 5
    )) {
      isDragging = true;
      
      // 선택된 커넥터가 레이어에 있다면 함께 이동
      if (props.selectedConnectorInfo && 
          String(props.selectedConnectorInfo.blockId) === String(blockData.id)) {
        const connectorId = props.selectedConnectorInfo.connectorId;
        const connector = blockData.connectionPoints?.find(cp => String(cp.id) === String(connectorId));
        
        if (connector && layer) {
          // 레이어에서 해당 커넥터와 드래그 핸들 찾기
          const layerChildren = layer.children;
          layerChildren.forEach(child => {
            // 커넥터 이동
            if (child.attrs && child.attrs.connectorId === connectorId && 
                child.attrs.blockId === blockData.id) {
              child.x(currentPos.x + connector.x);
              child.y(currentPos.y + connector.y);
            }
            // 드래그 핸들 이동
            if (child.attrs && child.attrs.isDragHandle && 
                child.attrs.connectorId === connectorId && 
                child.attrs.blockId === blockData.id) {
              child.x(currentPos.x + connector.x);
              child.y(currentPos.y + connector.y);
            }
          });
        }
      }
      
      // 실시간 연결선 업데이트 (성능을 위해 throttle)
      if (!blockGroup._dragMoveThrottle) {
        blockGroup._dragMoveThrottle = setTimeout(() => {
          updateConnections();
          scheduleLayerDraw();
          blockGroup._dragMoveThrottle = null;
        }, 16); // 60fps
      }
    }
  });

  // 드래그 종료
  blockGroup.on('dragend', () => {
    const newPos = { x: blockGroup.x(), y: blockGroup.y() };
    emit('update-block-position', { 
      id: blockData.id, 
      x: newPos.x, 
      y: newPos.y 
    });
    
    // 드래그 종료 후 연결선 업데이트
    setTimeout(() => {
      updateConnections();
      scheduleLayerDraw();
    }, 10);
    
    // 드래그 상태 즉시 리셋 (setTimeout 제거)
    isDragging = false;
  });

  // 기존 클릭 이벤트는 백업용으로 유지하되 더 엄격한 조건 적용
  blockGroup.on('click', (e) => {
    // 커넥터에서 발생한 이벤트는 무시
    if (e.target !== blockGroup && e.target.getClassName() === 'Circle') {
      return;
    }
    
    if (!isDragging) {
      emit('select-block', blockData.id);
    }
  });

  // 마우스 오버 시 오류 정보 표시
  let errorTooltip = null;
  
  blockGroup.on('mouseenter', () => {
    if (blockGroup.errorDetails && blockGroup.errorDetails.length > 0) {
      // 기존 툴팁이 있다면 제거
      if (errorTooltip) {
        errorTooltip.destroy();
      }
      
      // 오류 툴팁 생성
      const tooltip = new Konva.Label({
        x: 10,
        y: -50,
        opacity: 0.95
      });
      
      tooltip.add(new Konva.Tag({
        fill: '#fff',
        stroke: '#ff0000',
        strokeWidth: 1,
        shadowColor: 'black',
        shadowBlur: 6,
        shadowOffset: { x: 3, y: 3 },
        shadowOpacity: 0.3,
        cornerRadius: 5,
        pointerDirection: 'down',
        pointerWidth: 10,
        pointerHeight: 10
      }));
      
      const errorText = `스크립트 오류 (${blockGroup.errorDetails.length}개):\n` + 
                       blockGroup.errorDetails.slice(0, 3).join('\n') +
                       (blockGroup.errorDetails.length > 3 ? '\n...' : '');
      
      tooltip.add(new Konva.Text({
        text: errorText,
        fontFamily: 'Arial',
        fontSize: 11,
        padding: 8,
        fill: '#333',
        width: 250,
        wrap: 'word'
      }));
      
      blockGroup.add(tooltip);
      errorTooltip = tooltip;
      scheduleLayerDraw();
    }
  });
  
  blockGroup.on('mouseleave', () => {
    if (errorTooltip) {
      errorTooltip.destroy();
      errorTooltip = null;
      scheduleLayerDraw();
    }
  });
}

function updateConnectionsForBlock(blockId) {
  
  // 해당 블록과 관련된 연결선만 찾아서 업데이트
  props.connections.forEach(conn => {
    const fromBlockId = conn.from_block_id || conn.fromBlockId;
    const toBlockId = conn.to_block_id || conn.toBlockId;
    
    // 이 블록과 관련된 연결만 처리
    if (String(fromBlockId) === String(blockId) || String(toBlockId) === String(blockId)) {
      const connectionKey = `${fromBlockId}-${conn.from_connector_id || conn.fromConnectorId}-${toBlockId}-${conn.to_connector_id || conn.toConnectorId}`;
      const existingArrow = connectionNodes.value.get(connectionKey);
      
      if (existingArrow) {
        // 기존 화살표 업데이트
        const fromBlock = props.blocks.find(b => String(b.id) === String(fromBlockId));
        const toBlock = props.blocks.find(b => String(b.id) === String(toBlockId));
        
        if (fromBlock && toBlock) {
          const fromConnectorId = conn.from_connector_id || conn.fromConnectorId;
          const toConnectorId = conn.to_connector_id || conn.toConnectorId;
          
          let fromPointData, toPointData;
          
          if (fromConnectorId === 'block-action') {
            fromPointData = { x: (fromBlock.width || props.currentSettings.boxSize) / 2, y: (fromBlock.height || props.currentSettings.boxSize) / 2 };
          } else {
            fromPointData = (fromBlock.connectionPoints || []).find(p => p.id === fromConnectorId) || 
                          {x:(fromBlock.width || props.currentSettings.boxSize)/2, y:(fromBlock.height || props.currentSettings.boxSize)/2};
          }
          
          toPointData = (toBlock.connectionPoints || []).find(p => p.id === toConnectorId) || 
                        {x:(toBlock.width || props.currentSettings.boxSize)/2, y:(toBlock.height || props.currentSettings.boxSize)/2};
          
          const fromAbsX = fromBlock.x + fromPointData.x;
          const fromAbsY = fromBlock.y + fromPointData.y;
          const toAbsX = toBlock.x + toPointData.x;
          const toAbsY = toBlock.y + toPointData.y;
          
          // 연결선의 방향 벡터 계산
          const dx = toAbsX - fromAbsX;
          const dy = toAbsY - fromAbsY;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          // 연결선이 너무 짧은 경우 처리하지 않음
          if (distance < 20) {
            existingArrow.points([fromAbsX, fromAbsY, toAbsX, toAbsY]);
            return;
          }
          
          // 정규화된 방향 벡터
          const unitX = dx / distance;
          const unitY = dy / distance;
          
          // 커넥터 반지름 (8픽셀)
          const connectorRadius = 8;
          
          // 시작점과 끝점을 커넥터 외곽으로 조정
          let adjustedFromX = fromAbsX;
          let adjustedFromY = fromAbsY;
          let adjustedToX = toAbsX;
          let adjustedToY = toAbsY;
          
          // from_connector_id가 'block-action'이 아닌 경우에만 시작점 조정
          if (fromConnectorId !== 'block-action') {
            adjustedFromX = fromAbsX + unitX * connectorRadius;
            adjustedFromY = fromAbsY + unitY * connectorRadius;
          }
          
          // 끝점은 항상 커넥터 외곽으로 조정
          adjustedToX = toAbsX - unitX * connectorRadius;
          adjustedToY = toAbsY - unitY * connectorRadius;
          
          existingArrow.points([adjustedFromX, adjustedFromY, adjustedToX, adjustedToY]);
        }
      }
    }
  });
  
  scheduleLayerDraw();
}

function updateConnections() {
  
  // 기존 연결선 제거
  connectionNodes.value.forEach(node => node.destroy());
  connectionNodes.value.clear();
  
  // connections 배열만 사용하여 연결선 그리기 (중복 방지)
  props.connections.forEach(conn => {
    
    // 필드명 통일: from_block_id 또는 fromBlockId 모두 지원
    const fromBlockId = conn.from_block_id || conn.fromBlockId;
    const toBlockId = conn.to_block_id || conn.toBlockId;
    const fromConnectorId = conn.from_connector_id || conn.fromConnectorId;
    const toConnectorId = conn.to_connector_id || conn.toConnectorId;
    
    // 같은 블록 내에서 block-action에서 자기 연결점으로 가는 연결선은 그리지 않음
    if (String(fromBlockId) === String(toBlockId) && fromConnectorId === 'block-action') {
      return;
    }
    
    const fromBlock = props.blocks.find(b => String(b.id) === String(fromBlockId));
    const toBlock = props.blocks.find(b => String(b.id) === String(toBlockId));

    if (fromBlock && toBlock) {
      
      let fromPointData, toPointData;
      
      // from_connector_id가 'block-action'인 경우 블록 중앙에서 시작
      if (fromConnectorId === 'block-action') {
        fromPointData = { x: (fromBlock.width || props.currentSettings.boxSize) / 2, y: (fromBlock.height || props.currentSettings.boxSize) / 2 };
      } else {
        fromPointData = (fromBlock.connectionPoints || 
                               [{id:`${fromBlock.id}-conn-0`, x:fromBlock.width/2, y:fromBlock.height/2}])
                               .find(p => p.id === fromConnectorId) || {x:(fromBlock.width || props.currentSettings.boxSize)/2, y:(fromBlock.height || props.currentSettings.boxSize)/2};
      }
      
      toPointData = (toBlock.connectionPoints || 
                             [{id:`${toBlock.id}-conn-0`,x:toBlock.width/2, y:toBlock.height/2}])
                             .find(p => p.id === toConnectorId) || {x:(toBlock.width || props.currentSettings.boxSize)/2, y:(toBlock.height || props.currentSettings.boxSize)/2};

      const fromAbsX = fromBlock.x + fromPointData.x;
      const fromAbsY = fromBlock.y + fromPointData.y;
      const toAbsX = toBlock.x + toPointData.x;
      const toAbsY = toBlock.y + toPointData.y;
      
      // 연결선의 방향 벡터 계산
      const dx = toAbsX - fromAbsX;
      const dy = toAbsY - fromAbsY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      // 연결선이 너무 짧은 경우 그리지 않음
      if (distance < 20) return;
      
      // 정규화된 방향 벡터
      const unitX = dx / distance;
      const unitY = dy / distance;
      
      // 커넥터 반지름 (8픽셀)
      const connectorRadius = 8;
      
      // 시작점과 끝점을 커넥터 외곽으로 조정
      let adjustedFromX = fromAbsX;
      let adjustedFromY = fromAbsY;
      let adjustedToX = toAbsX;
      let adjustedToY = toAbsY;
      
      // from_connector_id가 'block-action'이 아닌 경우에만 시작점 조정
      if (fromConnectorId !== 'block-action') {
        adjustedFromX = fromAbsX + unitX * connectorRadius;
        adjustedFromY = fromAbsY + unitY * connectorRadius;
      }
      
      // 끝점은 항상 커넥터 외곽으로 조정
      adjustedToX = toAbsX - unitX * connectorRadius;
      adjustedToY = toAbsY - unitY * connectorRadius;
      
      // 모든 연결선을 동일한 색상으로 표시 (조건부/일반 구분 없이)
      const arrow = new Konva.Arrow({
        points: [adjustedFromX, adjustedFromY, adjustedToX, adjustedToY],
        pointerLength: 10,
        pointerWidth: 10,
        fill: 'black',
        stroke: 'black',
        strokeWidth: 3,
      });
      
      // connectionNodes에 저장하여 나중에 제거 가능하도록 함
      const connectionKey = `${fromBlockId}-${fromConnectorId}-${toBlockId}-${toConnectorId}`;
      connectionNodes.value.set(connectionKey, arrow);
      layer.add(arrow);
    } else {
    }
  });
}

function displayTransitEntity(entity, index) {
  
  // 🔥 연결선 중앙에 transit 엔티티 표시
  // 엔티티의 current_block_name에서 어떤 연결선을 사용할지 판단
  if (props.connections.length > 0) {
    // 모든 연결선을 검사하여 적절한 연결선 찾기
    let connection = null;
    
    // 엔티티의 current_block_name이 "투입→공정1" 형태라면 해당 연결선 찾기
    if (entity.current_block_name && entity.current_block_name.includes('→')) {
      const [fromName, toName] = entity.current_block_name.split('→');
      
      connection = props.connections.find(conn => {
        const fromBlock = props.blocks.find(b => String(b.id) === String(conn.from_block_id || conn.fromBlockId));
        const toBlock = props.blocks.find(b => String(b.id) === String(conn.to_block_id || conn.toBlockId));
        const matches = fromBlock && toBlock && fromBlock.name === fromName && toBlock.name === toName;
        if (matches) {
        }
        return matches;
      });
    }
    
    // 적절한 연결선을 찾지 못했다면 fallback 로직
    if (!connection) {
      
      // 가능한 모든 연결선 중에서 첫 번째 사용
      connection = props.connections[0];
    }
    const fromBlockId = connection.from_block_id || connection.fromBlockId;
    const toBlockId = connection.to_block_id || connection.toBlockId;
    
    const fromBlock = props.blocks.find(b => String(b.id) === String(fromBlockId));
    const toBlock = props.blocks.find(b => String(b.id) === String(toBlockId));
    
    if (fromBlock && toBlock) {
      // 연결선의 중앙점 계산
      const fromCenterX = fromBlock.x + (fromBlock.width || props.currentSettings.boxSize) / 2;
      const fromCenterY = fromBlock.y + (fromBlock.height || props.currentSettings.boxSize) / 2;
      const toCenterX = toBlock.x + (toBlock.width || props.currentSettings.boxSize) / 2;
      const toCenterY = toBlock.y + (toBlock.height || props.currentSettings.boxSize) / 2;
      
      // 중앙점에서 약간 오프셋을 적용하여 여러 엔티티 표시
      const middleX = (fromCenterX + toCenterX) / 2 + (index * 30); // 30px씩 옆으로 이동
      const middleY = (fromCenterY + toCenterY) / 2 + (index * 5);  // 5px씩 아래로 이동
      
      // 엔티티 색상 매핑
      const colorMap = {
        'gray': '#808080',
        'blue': '#0000FF',
        'green': '#00FF00',
        'red': '#FF0000',
        'black': '#000000',
        'white': '#FFFFFF',
      };
      
      // transit 상태일 때 기본 색상은 보라색, 하지만 entity에 색상이 지정되어 있으면 그것을 사용
      const entityColor = entity.color && colorMap[entity.color] ? colorMap[entity.color] : '#9B59B6';
      
      // 🔥 transit 엔티티 표시 - 더 눈에 잘 띄는 스타일
      const entitySize = 35;
      const transitRect = new Konva.Rect({
        x: middleX - entitySize / 2,
        y: middleY - entitySize / 2,
        width: entitySize,
        height: entitySize,
        fill: entityColor,
        stroke: '#8E44AD', // 진한 보라색 테두리
        strokeWidth: 3,
        cornerRadius: 5, // 모서리 둥글게
        shadowColor: 'black',
        shadowBlur: 4,
        shadowOffset: { x: 2, y: 2 },
        shadowOpacity: 0.5
      });
      
      // 엔티티 번호 텍스트 - 전역 매핑에서 번호 가져오기
      const entityNumber = globalEntityIdToNumber.get(entity.id) || 0;
      
      // 텍스트 색상 결정
      const darkColors = ['black', 'blue', 'red'];
      const textColor = (entity.color && darkColors.includes(entity.color)) ? 'white' : 
                       (entity.color === 'white' || entity.color === 'green') ? 'black' : 'white';
      
      const transitText = new Konva.Text({
        x: middleX - entitySize / 2,
        y: middleY - entitySize / 2,
        text: String(entityNumber),
        fontSize: 14,
        fill: textColor,
        fontStyle: 'bold',
        width: entitySize,
        height: entitySize,
        align: 'center',
        verticalAlign: 'middle'
      });
      
      // "TRANSIT" 라벨 추가
      const transitLabel = new Konva.Text({
        x: middleX - 20,
        y: middleY + entitySize / 2 + 5,
        text: 'TRANSIT',
        fontSize: 8,
        fill: '#9B59B6',
        fontStyle: 'bold',
        align: 'center',
        width: 40
      });
      
      entityTextGroup.value.add(transitRect);
      entityTextGroup.value.add(transitText);
      entityTextGroup.value.add(transitLabel);
      
    }
  } else {
    // 연결선이 없는 경우 화면 중앙에 표시
    const centerX = (stage?.width() || 800) / 2;
    const centerY = (stage?.height() || 600) / 2;
    
    const entitySize = 35;
    const transitRect = new Konva.Rect({
      x: centerX - entitySize / 2 + (index * 40),
      y: centerY - entitySize / 2,
      width: entitySize,
      height: entitySize,
      fill: '#E74C3C', // 빨간색 - 문제 상황
      stroke: '#C0392B',
      strokeWidth: 3,
      cornerRadius: 5
    });
    
    let entityNumber;
    const idMatch = entity.id.match(/-e(\d+)$/);
    if (idMatch) {
      entityNumber = parseInt(idMatch[1]);
    } else {
      entityNumber = index + 1;
    }
    
    const transitText = new Konva.Text({
      x: centerX - entitySize / 2 + (index * 40),
      y: centerY - entitySize / 2,
      text: String(entityNumber),
      fontSize: 14,
      fill: 'white',
      fontStyle: 'bold',
      width: entitySize,
      height: entitySize,
      align: 'center',
      verticalAlign: 'middle'
    });
    
    entityTextGroup.value.add(transitRect);
    entityTextGroup.value.add(transitText);
    
  }
}

function updateEntities() {
  
  if (!entityTextGroup.value) {
    entityTextGroup.value = new Konva.Group();
    layer.add(entityTextGroup.value);
    // 엔티티 그룹을 최상단으로 이동하여 다른 요소들 위에 표시되도록 함
    entityTextGroup.value.moveToTop();
  }
  
  entityTextGroup.value.destroyChildren();
  
  // 블록별로 엔티티 그룹화
  const entitiesByBlock = new Map();
  props.activeEntityStates.forEach(entity => {
    const blockId = String(entity.current_block_id);
    if (!entitiesByBlock.has(blockId)) {
      entitiesByBlock.set(blockId, []);
    }
    entitiesByBlock.get(blockId).push(entity);
  });
  
  
  // 새로운 엔티티에 대해서만 번호 할당
  props.activeEntityStates.forEach(entity => {
    if (!globalEntityIdToNumber.has(entity.id)) {
      globalEntityIdToNumber.set(entity.id, globalNextEntityNumber++);
    }
  });
  
  
  
  // 각 블록에 엔티티 네모로 표시
  entitiesByBlock.forEach((entities, blockId) => {
    // 🔥 transit 상태 엔티티 처리
    if (blockId === "transit") {
      entities.forEach((entity, index) => {
        displayTransitEntity(entity, index);
      });
      return; // transit 엔티티 처리 완료
    }
    
    const block = props.blocks.find(b => String(b.id) === blockId);
    if (block) {
      const blockWidth = block.width || props.currentSettings.boxSize;
      const blockHeight = block.height || props.currentSettings.boxSize;
      
      entities.forEach((entity, index) => {
        let entitySize, entityX, entityY;
        
        if (entities.length === 1) {
          // 엔티티가 하나만 있을 때: 블록 중앙에 큰 사각형 - 크기 증가
          entitySize = 40; // 30 -> 40으로 증가
          entityX = blockWidth / 2 - entitySize / 2;
          entityY = blockHeight / 2 - entitySize / 2;
        } else {
          // 엔티티가 여러 개일 때: 그리드로 배치 - 크기 증가
          entitySize = 28; // 20 -> 28로 증가
          const padding = 5;
          const startX = padding;
          const startY = 35; // 블록 제목 아래부터 시작
          
          const col = index % 3; // 가로 최대 3개
          const row = Math.floor(index / 3); // 세로 배치
          
          entityX = startX + col * (entitySize + 3);
          entityY = startY + row * (entitySize + 3);
        }
        
        // 블록 바운드리 체크
        const padding = entities.length === 1 ? 5 : 2; // 하나일 때는 여유 공간, 여러 개일 때는 적은 여유 공간
        if (entityX >= padding && entityY >= padding && 
            entityX + entitySize <= blockWidth - padding && 
            entityY + entitySize <= blockHeight - padding) {
          
          // 엔티티 색상 매핑
          const colorMap = {
            'gray': '#808080',
            'blue': '#0000FF',
            'green': '#00FF00',
            'red': '#FF0000',
            'black': '#000000',
            'white': '#FFFFFF',
          };
          
          // 엔티티 색상 결정 (color 속성이 있으면 사용, 없으면 기본 주황색)
          const entityColor = entity.color && colorMap[entity.color] ? colorMap[entity.color] : '#FF6B35';
          
          // 엔티티 네모 - 더 눈에 잘 띄도록 스타일 강화
          const entityRect = new Konva.Rect({
            x: block.x + entityX,
            y: block.y + entityY,
            width: entitySize,
            height: entitySize,
            fill: entityColor,
            stroke: '#D63031', // 진한 빨간색 테두리
            strokeWidth: 2,
            cornerRadius: 1,
            shadowColor: 'black',
            shadowBlur: 2,
            shadowOffset: { x: 1, y: 1 },
            shadowOpacity: 0.3
          });
          
          // 엔티티 번호 텍스트 - 전역 매핑에서 번호 가져오기
          const entityNumber = globalEntityIdToNumber.get(entity.id) || 0;
          const fontSize = entities.length === 1 ? 16 : 12; // 14->16, 10->12로 증가
          
          // 텍스트 색상 결정 (어두운 배경은 흰색, 밝은 배경은 검은색)
          const darkColors = ['black', 'blue', 'red'];
          const textColor = (entity.color && darkColors.includes(entity.color)) ? 'white' : 
                           (entity.color === 'white' || entity.color === 'green') ? 'black' : 'white';
          
          const entityText = new Konva.Text({
            x: block.x + entityX,
            y: block.y + entityY,
            text: String(entityNumber),
            fontSize: fontSize,
            fill: textColor,
            fontStyle: 'bold',
            width: entitySize,
            height: entitySize,
            align: 'center',
            verticalAlign: 'middle'
          });
          
          entityTextGroup.value.add(entityRect);
          entityTextGroup.value.add(entityText);
        } else {
        }
      });
    } else {
      // 🔥 블록을 찾을 수 없는 경우 로그 출력 및 임시 표시
      
      // transit이 아닌데 블록이 없는 경우에도 연결선 위에 표시
      entities.forEach((entity, index) => {
        displayTransitEntity(entity, index);
      });
    }
  });
  
  // 엔티티 그룹을 다시 최상단으로 이동하여 확실히 보이도록 함
  if (entityTextGroup.value) {
    entityTextGroup.value.moveToTop();
  }
  
  // Force redraw after updating entities
  scheduleLayerDraw();
}

function drawGrid() {
  if (!gridLayer || !stage) return;
  gridLayer.destroyChildren();

  const gridSize = 20;
  const stageWidth = stage.width() / stage.scaleX();
  const stageHeight = stage.height() / stage.scaleY();
  const stageX = -stage.x() / stage.scaleX();
  const stageY = -stage.y() / stage.scaleY();

  for (let i = Math.floor(stageX / gridSize) * gridSize; i < stageX + stageWidth; i += gridSize) {
    const line = new Konva.Line({
      points: [i, stageY, i, stageY + stageHeight],
      stroke: '#ddd',
      strokeWidth: 0.5,
      listening: false,
    });
    gridLayer.add(line);
  }

  for (let j = Math.floor(stageY / gridSize) * gridSize; j < stageY + stageHeight; j += gridSize) {
    const line = new Konva.Line({
      points: [stageX, j, stageX + stageWidth, j],
      stroke: '#ddd',
      strokeWidth: 0.5,
      listening: false,
    });
    gridLayer.add(line);
  }
  scheduleGridDraw();
}

function zoom(scaleMultiplier) {
  if (!stage) return;
  const oldScale = stage.scaleX();
  const newScale = oldScale * scaleMultiplier;
  
  const pointer = stage.getPointerPosition();
  if (!pointer) {
      const center = {
          x: stage.width() / 2,
          y: stage.height() / 2,
      };
      const mousePointTo = {
        x: (center.x - stage.x()) / oldScale,
        y: (center.y - stage.y()) / oldScale,
      };
      stage.scale({ x: newScale, y: newScale });
      const newPos = {
        x: center.x - mousePointTo.x * newScale,
        y: center.y - mousePointTo.y * newScale,
      };
      stage.position(newPos);
  } else {
      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };
      stage.scale({ x: newScale, y: newScale });
      const newPos = {
        x: pointer.x - mousePointTo.x * newScale,
        y: pointer.y - mousePointTo.y * newScale,
      };
      stage.position(newPos);
  }
  stage.batchDraw();
  drawGrid();
}

function zoomIn() {
  zoom(zoomFactor);
}

function zoomOut() {
  zoom(1 / zoomFactor);
}

// 캔버스 크기 재조정 함수
function resizeCanvas() {
  if (!stage || !canvasContainerRef.value) return;
  
  const container = canvasContainerRef.value;
  const containerRect = container.getBoundingClientRect();
  const width = Math.max(container.clientWidth || container.offsetWidth || containerRect.width, 200);
  const height = Math.max(container.clientHeight || container.offsetHeight || containerRect.height, 200);
  
  
  // 현재 Stage 크기와 비교해서 변경된 경우만 업데이트
  const currentWidth = stage.width();
  const currentHeight = stage.height();
  
  if (Math.abs(currentWidth - width) > 1 || Math.abs(currentHeight - height) > 1) {
    
    // Stage 크기 업데이트
    stage.width(width);
    stage.height(height);
    
    // Stage 컨테이너도 확실히 업데이트
    const stageContainer = stage.container();
    if (stageContainer) {
      stageContainer.style.width = '100%';
      stageContainer.style.height = '100%';
    }
    
    // 캔버스 요소도 강제로 크기 업데이트
    const canvas = stageContainer?.querySelector('canvas');
    if (canvas) {
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      
      // Canvas의 실제 픽셀 크기도 강제 설정
      canvas.width = width;
      canvas.height = height;
      
    }
    
    drawGrid();
    stage.batchDraw();
  }
}

// ResizeObserver를 위한 변수
let resizeObserver = null;

// 디바운스된 리사이즈 함수
let resizeTimeout = null;
function debouncedResize() {
  if (resizeTimeout) {
    clearTimeout(resizeTimeout);
  }
  resizeTimeout = setTimeout(() => {
    resizeCanvas();
  }, 16); // 60fps에 맞춰 16ms 디바운스
}

// 블록들을 화면 중앙에 보이도록 뷰 조정
function centerViewOnBlocks() {
  if (!stage || !props.blocks.length) return;
  
  // 모든 블록의 경계 계산
  let minX = Infinity, minY = Infinity;
  let maxX = -Infinity, maxY = -Infinity;
  
  props.blocks.forEach(block => {
    minX = Math.min(minX, block.x);
    minY = Math.min(minY, block.y);
    maxX = Math.max(maxX, block.x + (block.width || 100));
    maxY = Math.max(maxY, block.y + (block.height || 100));
  });
  
  // 블록들의 중심점
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  
  // 스테이지 중심점
  const stageCenterX = stage.width() / 2;
  const stageCenterY = stage.height() / 2;
  
  // 카메라 위치 조정 (블록 중심을 화면 중앙으로)
  const newX = stageCenterX - centerX;
  const newY = stageCenterY - centerY;
  
  
  stage.position({ x: newX, y: newY });
  stage.batchDraw();
  drawGrid();
}

// Stage 이벤트 리스너 추가
function addStageEventListeners() {
  if (!stage) return;
  
  // 배경 클릭 처리
  stage.on('mousedown', (e) => {
    // 배경 클릭 감지 (Stage 자체를 클릭한 경우)
    if (e.target === stage) {
      // 커서를 기본값으로 리셋
      document.body.style.cursor = 'default';
      
      // 선택 해제를 위해 부모 컴포넌트에 이벤트 전송
      setTimeout(() => {
        if (props.selectedBlockId || props.selectedConnectorInfo) {
          emit('select-block', null); // null을 전달하여 선택 해제 신호
        }
      }, 50); // 다른 클릭 이벤트가 처리된 후 실행
    }
  });
}

// Wheel 이벤트 리스너 추가
function addWheelEventListener() {
  if (!stage) return;
  
  const container = stage.container();
  if (container) {
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const oldScale = stage.scaleX();
      const pointer = stage.getPointerPosition();

      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };

      let direction = e.deltaY > 0 ? -1 : 1;
      const newScale = direction > 0 ? oldScale * zoomFactor : oldScale / zoomFactor;
      stage.scale({ x: newScale, y: newScale });

      const newPos = {
        x: pointer.x - mousePointTo.x * newScale,
        y: pointer.y - mousePointTo.y * newScale,
      };
      stage.position(newPos);
      stage.batchDraw();
      drawGrid();
    }, { passive: false });
    
  }
}

watch(() => props.currentSettings.boxSize, () => {
  if (stage) {
    drawCanvasContent();
    drawGrid();
  }
});

watch(() => props.currentSettings.fontSize, () => {
  if (stage) {
    drawCanvasContent();
    drawGrid();
  }
});

// 성능 최적화된 watch - 분리된 감시
watch(() => props.blocks, (newBlocks, oldBlocks) => {
  
  if (stage) {
    // 최초 로드 또는 블록이 없다가 생긴 경우
    const isInitialLoad = !oldBlocks || oldBlocks.length === 0;
    
    if (isInitialLoad) {
      // 초기 로드 시 전체 다시 그리기
      dirtyFlags.value.all = true;
    } else {
      // 변경 감지 실행
      detectChanges();
      
      // 위치 변경이 있으면 연결선도 업데이트 필요
      let positionChanged = false;
      dirtyFlags.value.blocks.forEach(blockId => {
        const newBlock = newBlocks.find(b => String(b.id) === blockId);
        const oldBlock = oldBlocks?.find(b => String(b.id) === blockId);
        if (oldBlock && newBlock && (oldBlock.x !== newBlock.x || oldBlock.y !== newBlock.y)) {
          positionChanged = true;
        }
      });
      
      if (positionChanged) {
        dirtyFlags.value.connections.add('all'); // 모든 연결 업데이트
      }
    }
    
    drawCanvasContent();
    
    // 최초 로드 시에만 뷰 조정
    if (isInitialLoad && props.blocks.length > 0) {
      setTimeout(() => {
        centerViewOnBlocks();
      }, 100);
    }
  }
}, { deep: true, flush: 'post' });

watch(() => props.connections, () => {
  if (stage) {
    // 모든 연결 업데이트 필요
    dirtyFlags.value.connections.add('all');
    drawCanvasContent();
  }
}, { deep: true, flush: 'post' });

watch(() => props.currentSettings, () => {
  if (stage) {
    // 설정 변경 시 전체 다시 그리기
    dirtyFlags.value.all = true;
    drawCanvasContent();
    drawGrid();
  }
}, { deep: true, flush: 'post' });

watch(() => props.activeEntityStates, () => {
  
  // 엔티티가 모두 사라지면 전역 매핑 초기화 (리셋)
  if (props.activeEntityStates.length === 0) {
    globalEntityIdToNumber.clear();
    globalNextEntityNumber = 1;
  }
  
  if (stage && layer) {
    // 변경 감지 실행
    detectChanges();
    drawCanvasContent();
  }
}, { deep: true });

// 레이어에서 선택된 커넥터 정리
function cleanupSelectedConnectors() {
  if (!layer) return;
  
  // 레이어의 자식 요소 중 커넥터와 관련 요소들 제거
  const children = layer.children.slice(); // 복사본 생성
  children.forEach(child => {
    // 커넥터 원, 드래그 핸들, 라벨 등 모두 제거
    if (child.attrs && (child.attrs.connectorId || child.attrs.isDragHandle)) {
      child.destroy();
    }
    // Circle 타입이면서 파란색 점선인 경우도 제거 (드래그 핸들)
    if (child.className === 'Circle' && child.attrs.stroke === '#4A90E2') {
      child.destroy();
    }
  });
  
  scheduleLayerDraw();
}

// 선택 상태 변경 시 즉시 화면 업데이트 - 더 빠른 반응을 위해 sync 플러시 사용
watch(() => [props.selectedBlockId, props.selectedConnectorInfo], ([newBlockId, newConnectorInfo], [oldBlockId, oldConnectorInfo]) => {
  if (stage) {
    // 항상 이전 선택을 정리
    cleanupSelectedConnectors();
    
    // 커넥터가 선택 해제되었으면 커서 리셋
    if (oldConnectorInfo && !newConnectorInfo) {
      document.body.style.cursor = 'default';
    }
    
    // 선택 상태만 변경되었으므로 모든 블록 업데이트
    dirtyFlags.value.all = true;
    drawCanvasContent();
    
    // 커넥터가 선택된 경우 해당 블록 강제 업데이트
    if (props.selectedConnectorInfo && props.selectedConnectorInfo.blockId) {
      const blockId = String(props.selectedConnectorInfo.blockId);
      const block = props.blocks.find(b => String(b.id) === blockId);
      if (block) {
        updateSingleBlock(block);
      }
    }
  }
}, { deep: true, flush: 'sync' });

// 캔버스 컨테이너 크기에 영향을 주는 요소들 감시
watch(() => [props.showBlockSettingsPopup, props.showConnectorSettingsPopup], () => {
  // 설정창 표시 상태가 변경되면 약간의 지연 후 리사이즈
  setTimeout(() => {
    debouncedResize();
  }, 350); // 트랜지션 완료 후 리사이즈
}, { flush: 'post' });

function getStage() {
    return stage;
}

defineExpose({ getStage });

onMounted(() => {
  
  // 초기화 재시도 로직
  let retryCount = 0;
  const maxRetries = 5;
  
  function tryInitialize() {
    
    const success = initKonva();
    
    if (success && stage) {
      
      // 레이어 생성 및 추가
      layer = new Konva.Layer();
      stage.add(layer);

      gridLayer = new Konva.Layer();
      stage.add(gridLayer);
      gridLayer.moveToBottom();
      drawGrid();

      // 초기 블록이 있으면 전체 다시 그리기
      if (props.blocks.length > 0) {
        dirtyFlags.value.all = true;
      }
      
      drawCanvasContent();
      
      // 이벤트 리스너 추가
      addStageEventListeners();
      
      // 블록들이 있으면 화면에 맞게 초기 위치 조정
      setTimeout(() => {
        if (props.blocks.length > 0) {
          centerViewOnBlocks();
        }
      }, 300);
      
      // wheel 이벤트 리스너 추가
      addWheelEventListener();
      
    } else {
      retryCount++;
      if (retryCount < maxRetries) {
        setTimeout(tryInitialize, 500 * retryCount);
      } else {
      }
    }
  }
  
  // 첫 번째 시도 - DOM이 완전히 준비될 때까지 대기
  setTimeout(tryInitialize, 200);
  
  // ResizeObserver 설정 - 컨테이너 크기 변화를 정확히 감지
  setTimeout(() => {
    if (window.ResizeObserver && canvasContainerRef.value) {
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          debouncedResize();
        }
      });
      
      resizeObserver.observe(canvasContainerRef.value);
    }
  }, 300);
  
  // window resize 이벤트 리스너 추가 (ResizeObserver 백업용)
  const handleResize = () => {
    debouncedResize();
  };
  
  window.addEventListener('resize', handleResize);
  
  // 컴포넌트 언마운트 시 정리
  onUnmounted(() => {
    // ResizeObserver 정리
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    
    // 타이머 정리
    if (resizeTimeout) {
      clearTimeout(resizeTimeout);
    }
    
    window.removeEventListener('resize', handleResize);
    if (stage) {
      stage.destroy();
    }
  });
});

</script>

<style scoped>
.canvas-area {
  width: 100%;
  height: 100%;
  min-width: 200px; /* 최소 너비 보장 */
  min-height: 200px; /* 최소 높이 보장 */
  background-color: #e9ecef; /* 원래 회색으로 복원 */
  position: relative;
  overflow: hidden;
  flex: 1; /* flex 속성 추가 */
}

#konva-container {
  width: 100%;
  height: 100%;
  min-width: inherit; /* 부모의 최소 크기 상속 */
  min-height: inherit; /* 부모의 최소 크기 상속 */
  position: relative;
  display: block;
  /* 배경색 제거 - 원래대로 투명 */
}

.zoom-controls {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 5px;
  border-radius: 5px;
}

.zoom-controls button {
  margin-left: 5px;
}
</style> 
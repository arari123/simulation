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
]);

const canvasContainerRef = ref(null);
let stage = null;
let layer = null;
let gridLayer = null;
const zoomFactor = 1.1;

const entityTextGroup = ref(null);

function initKonva() {
  console.log("[CanvasArea] initKonva 시작");
  console.log("[CanvasArea] canvasContainerRef.value:", canvasContainerRef.value);
  
  if (!canvasContainerRef.value) {
    console.error("[CanvasArea] canvasContainerRef가 없습니다!");
    return;
  }

  // 기존 stage가 있으면 제거
  if (stage) {
    console.log("[CanvasArea] 기존 Stage 제거");
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
  
  console.log("[CanvasArea] 컨테이너 크기 감지:", { 
    clientSize: { width: container.clientWidth, height: container.clientHeight },
    offsetSize: { width: container.offsetWidth, height: container.offsetHeight },
    boundingRect: { width: containerRect.width, height: containerRect.height },
    finalSize: { width, height }
  });
  
  // 크기가 여전히 0이면 부모 크기 기반 계산
  if (width <= 0 || height <= 0) {
    const parent = container.parentElement;
    if (parent) {
      width = Math.max(parent.clientWidth - 50, 800);
      height = Math.max(parent.clientHeight - 50, 600);
      console.log("[CanvasArea] 부모 크기 기반 계산:", { width, height });
    }
  }
  
  console.log("[CanvasArea] 최종 캔버스 크기:", { width, height });

  try {
    stage = new Konva.Stage({
      container: container,
      width: width,
      height: height,
      draggable: true,
    });

    console.log("[CanvasArea] Stage 생성 성공:", stage);

    // Stage 컨테이너 스타일 설정
    const stageContainer = stage.container();
    if (stageContainer) {
      stageContainer.style.zIndex = '1';
      stageContainer.style.position = 'relative';
      stageContainer.style.width = '100%';
      stageContainer.style.height = '100%';
      stageContainer.style.display = 'block';
      console.log("[CanvasArea] Stage 컨테이너 스타일 설정 완료");
      
      // Canvas 요소 확인 (디버깅용 색상 제거)
      setTimeout(() => {
        const canvas = stageContainer.querySelector('canvas');
        if (canvas) {
          console.log("[CanvasArea] Canvas 요소 감지:", {
            canvasWidth: canvas.width,
            canvasHeight: canvas.height,
            canvasStyleWidth: canvas.style.width,
            canvasStyleHeight: canvas.style.height
          });
        } else {
          console.error("[CanvasArea] Canvas 요소를 찾을 수 없습니다!");
        }
      }, 100);
    }
    
    return true; // 성공
  } catch (error) {
    console.error("[CanvasArea] Stage 생성 실패:", error);
    return false; // 실패
  }
}

// 성능 최적화: 부분 렌더링을 위한 상태 관리
const blockNodes = ref(new Map())
const connectionNodes = ref(new Map())
const dirtyFlags = ref({
  blocks: true,
  connections: true,
  entities: true
})

function drawCanvasContent() {
  console.log("[CanvasArea] drawCanvasContent 시작 - 부분 렌더링 모드");
  
  if (!layer || !stage) {
    console.error("[CanvasArea] layer 또는 stage가 없습니다!");
    return;
  }
  
  // 엔티티 그룹 초기화 (한 번만 필요)
  if (!entityTextGroup.value) {
    console.log("[CanvasArea] Creating entityTextGroup in drawCanvasContent");
    entityTextGroup.value = new Konva.Group();
    layer.add(entityTextGroup.value);
    entityTextGroup.value.moveToTop();
  }

  // 블록이 변경된 경우 또는 엔티티가 변경된 경우 업데이트
  if (dirtyFlags.value.blocks || dirtyFlags.value.entities) {
    updateBlocks();
    // 엔티티 업데이트 추가
    updateEntities();
    dirtyFlags.value.blocks = false;
    dirtyFlags.value.entities = false;
  }
  
  // 연결이 변경된 경우만 업데이트
  if (dirtyFlags.value.connections) {
    updateConnections();
    dirtyFlags.value.connections = false;
  }
  
  if (props.blocks.length === 0) {
    console.warn("[CanvasArea] 블록이 없습니다!");
    layer.draw();
    return;
  }
  
  layer.draw();
}

function updateBlocks() {
  console.log("[CanvasArea] 블록 부분 업데이트");
  
  // 기존 블록 중 더 이상 존재하지 않는 것들 제거
  const currentBlockIds = new Set(props.blocks.map(b => b.id.toString()));
  for (const [blockId, blockGroup] of blockNodes.value) {
    if (!currentBlockIds.has(blockId)) {
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
  console.log(`[CanvasArea] 새 블록 생성: ${blockData.id} (${blockData.name})`);
  
  const blockGroup = new Konva.Group({
    id: 'block-' + blockData.id.toString(),
    x: blockData.x,
    y: blockData.y,
    draggable: true,
  });

  // 블록 사각형
  const rect = new Konva.Rect({
    width: blockData.width || props.currentSettings.boxSize,
    height: blockData.height || props.currentSettings.boxSize,
    fill: 'lightblue',
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
  
  // 내용 업데이트
  blockGroup.destroyChildren();
  addBlockContent(blockGroup, blockData);
}

function addBlockContent(blockGroup, blockData) {
  // 블록 선택 상태 확인
  const isBlockSelected = props.selectedBlockId && String(props.selectedBlockId) === String(blockData.id);
  
  // 블록 사각형 - 선택 상태에 따라 스타일 변경
  const rect = new Konva.Rect({
    width: blockData.width || props.currentSettings.boxSize,
    height: blockData.height || props.currentSettings.boxSize,
    fill: isBlockSelected ? '#E3F2FD' : 'lightblue', // 선택된 경우 더 밝은 색
    stroke: isBlockSelected ? '#2196F3' : 'black', // 선택된 경우 파란색 테두리
    strokeWidth: isBlockSelected ? 3 : 2, // 선택된 경우 더 두꺿게
  });
  blockGroup.add(rect);

  // 선택된 블록인 경우 하이라이트 테두리 추가
  if (isBlockSelected) {
    const highlightRect = new Konva.Rect({
      width: (blockData.width || props.currentSettings.boxSize) + 8,
      height: (blockData.height || props.currentSettings.boxSize) + 8,
      x: -4,
      y: -4,
      fill: 'transparent',
      stroke: '#FF6B35',
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
    fill: 'black',
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
  
  console.log(`[CanvasArea] Block ${blockData.name}(${blockData.id}) - activeEntityStates:`, props.activeEntityStates);
  console.log(`[CanvasArea] Block ${blockData.name}(${blockData.id}) - entitiesInThisBlock:`, entitiesInThisBlock);
  
  const capacityTextString = `${entitiesInThisBlock.length}/${blockData.maxCapacity || 1}`;
  console.log(`[CanvasArea] Block ${blockData.name}(${blockData.id}) - capacityText: ${capacityTextString}`);
  
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

  // 커넥터 추가
  if (blockData.connectionPoints) {
    blockData.connectionPoints.forEach(cp => {
      // 선택된 커넥터인지 확인
      const isSelected = props.selectedConnectorInfo && 
                        String(props.selectedConnectorInfo.blockId) === String(blockData.id) && 
                        String(props.selectedConnectorInfo.connectorId) === String(cp.id);
      
      const connectorCircle = new Konva.Circle({
        x: cp.x,
        y: cp.y,
        radius: isSelected ? 12 : 8, // 선택된 경우 더 크게
        fill: isSelected ? '#FF6B35' : 'orange', // 선택된 경우 다른 색상
        stroke: isSelected ? '#D63031' : 'darkorange',
        strokeWidth: isSelected ? 3 : 2, // 선택된 경우 더 두꺿게
        draggable: false,
      });
      
      // 선택된 커넥터에 후광 효과 추가
      if (isSelected) {
        const haloCircle = new Konva.Circle({
          x: cp.x,
          y: cp.y,
          radius: 16,
          fill: 'transparent',
          stroke: '#FF6B35',
          strokeWidth: 2,
          dash: [4, 4],
          opacity: 0.7
        });
        blockGroup.add(haloCircle);
      }
      
      // 커넥터 클릭 이벤트 - 더 안정적인 이벤트 처리
      connectorCircle.on('click', (e) => {
        e.cancelBubble = true; // 이벤트 버블링 방지
        e.evt?.stopPropagation(); // 네이티브 이벤트 전파도 중단
        console.log(`[CanvasArea] 커넥터 클릭됨: Block ${blockData.id}, Connector ${cp.id}`);
        console.log(`[CanvasArea] Emitting select-connector`);
        emit('select-connector', {
          blockId: blockData.id,
          connectorId: cp.id
        });
      });
      
      // 마우스다운/업 이벤트로 클릭 상태 추적
      let connectorMouseDownTime = 0;
      connectorCircle.on('mousedown', (e) => {
        e.cancelBubble = true;
        e.evt?.stopPropagation();
        connectorMouseDownTime = Date.now();
        console.log(`[CanvasArea] 커넥터 마우스다운: Block ${blockData.id}, Connector ${cp.id}`);
      });
      
      connectorCircle.on('mouseup', (e) => {
        e.cancelBubble = true;
        e.evt?.stopPropagation();
        const clickDuration = Date.now() - connectorMouseDownTime;
        // 짧은 클릭만 처리 (300ms 이하)
        if (clickDuration < 300) {
          console.log(`[CanvasArea] 커넥터 마우스업 (클릭): Block ${blockData.id}, Connector ${cp.id}`);
          emit('select-connector', {
            blockId: blockData.id,
            connectorId: cp.id
          });
        }
      });
      
      blockGroup.add(connectorCircle);
      
      // 커넥터 라벨 추가 (항상 표시)
      if (cp.name) {
        // 이름이 4글자를 넘으면 잘라서 표시
        const displayName = cp.name.length > 4 ? cp.name.substring(0, 4) : cp.name;
        
        const connectorLabel = new Konva.Text({
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
        const labelBg = new Konva.Rect({
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
    console.log(`[CanvasArea] Block ${blockData.name} mousedown - 드래그 상태 초기화`);
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
      console.log(`[CanvasArea] Block ${blockData.name} 클릭 감지됨 (duration: ${clickDuration}ms, distance: ${mouseMoveDistance}px)`);
      emit('select-block', blockData.id);
    } else {
      console.log(`[CanvasArea] Block ${blockData.name} 클릭이 아님 (duration: ${clickDuration}ms, distance: ${mouseMoveDistance}px, dragging: ${isDragging})`);
    }
  });

  // 드래그 시작
  blockGroup.on('dragstart', () => {
    console.log(`[CanvasArea] Block ${blockData.name} 드래그 시작`);
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
      
      // 실시간 연결선 업데이트 (성능을 위해 throttle)
      if (!blockGroup._dragMoveThrottle) {
        blockGroup._dragMoveThrottle = setTimeout(() => {
          updateConnections();
          layer.draw();
          blockGroup._dragMoveThrottle = null;
        }, 16); // 60fps
      }
    }
  });

  // 드래그 종료
  blockGroup.on('dragend', () => {
    console.log(`[CanvasArea] Block ${blockData.name} 드래그 종료`);
    const newPos = { x: blockGroup.x(), y: blockGroup.y() };
    emit('update-block-position', { 
      id: blockData.id, 
      x: newPos.x, 
      y: newPos.y 
    });
    
    // 드래그 종료 후 연결선 업데이트
    setTimeout(() => {
      updateConnections();
      layer.draw();
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
    
    console.log(`[CanvasArea] Block ${blockData.name} 클릭 이벤트 (백업), isDragging: ${isDragging}`);
    if (!isDragging) {
      console.log(`[CanvasArea] Emitting select-block for ${blockData.id} (백업 이벤트)`);
      emit('select-block', blockData.id);
    }
  });
}

function updateConnections() {
  console.log("[CanvasArea] 연결 부분 업데이트 - connections 배열 기반");
  
  // 기존 연결선 제거
  connectionNodes.value.forEach(node => node.destroy());
  connectionNodes.value.clear();
  
  // connections 배열만 사용하여 연결선 그리기 (중복 방지)
  props.connections.forEach(conn => {
    console.log("[CanvasArea] Processing connection:", conn);
    
    // 필드명 통일: from_block_id 또는 fromBlockId 모두 지원
    const fromBlockId = conn.from_block_id || conn.fromBlockId;
    const toBlockId = conn.to_block_id || conn.toBlockId;
    const fromConnectorId = conn.from_connector_id || conn.fromConnectorId;
    const toConnectorId = conn.to_connector_id || conn.toConnectorId;
    
    // 같은 블록 내에서 block-action에서 자기 연결점으로 가는 연결선은 그리지 않음
    if (String(fromBlockId) === String(toBlockId) && fromConnectorId === 'block-action') {
      console.log(`[CanvasArea] Skipping self-connection: ${fromBlockId}(${fromConnectorId}) -> ${toBlockId}(${toConnectorId})`);
      return;
    }
    
    const fromBlock = props.blocks.find(b => String(b.id) === String(fromBlockId));
    const toBlock = props.blocks.find(b => String(b.id) === String(toBlockId));

    if (fromBlock && toBlock) {
      console.log(`[CanvasArea] Drawing connection: ${fromBlock.name}(${fromConnectorId}) -> ${toBlock.name}(${toConnectorId})`);
      
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
      
      // 모든 연결선을 동일한 색상으로 표시 (조건부/일반 구분 없이)
      const arrow = new Konva.Arrow({
        points: [fromAbsX, fromAbsY, toAbsX, toAbsY],
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
      console.log(`[CanvasArea] Arrow added: ${fromBlock.name} -> ${toBlock.name}`);
    } else {
      console.warn(`[CanvasArea] Block not found for connection:`, conn, "fromBlock:", fromBlock, "toBlock:", toBlock);
    }
  });
}

function displayTransitEntity(entity, index) {
  console.log(`[CanvasArea] Displaying transit entity: ${entity.id}`, entity);
  
  // 🔥 연결선 중앙에 transit 엔티티 표시
  // 엔티티의 current_block_name에서 어떤 연결선을 사용할지 판단
  if (props.connections.length > 0) {
    // 모든 연결선을 검사하여 적절한 연결선 찾기
    let connection = null;
    
    // 엔티티의 current_block_name이 "투입→공정1" 형태라면 해당 연결선 찾기
    if (entity.current_block_name && entity.current_block_name.includes('→')) {
      const [fromName, toName] = entity.current_block_name.split('→');
      console.log(`[CanvasArea] Transit from "${fromName}" to "${toName}"`);
      
      connection = props.connections.find(conn => {
        const fromBlock = props.blocks.find(b => String(b.id) === String(conn.from_block_id || conn.fromBlockId));
        const toBlock = props.blocks.find(b => String(b.id) === String(conn.to_block_id || conn.toBlockId));
        const matches = fromBlock && toBlock && fromBlock.name === fromName && toBlock.name === toName;
        if (matches) {
          console.log(`[CanvasArea] Found matching connection: ${fromBlock.name} → ${toBlock.name}`);
        }
        return matches;
      });
    }
    
    // 적절한 연결선을 찾지 못했다면 fallback 로직
    if (!connection) {
      console.log(`[CanvasArea] Could not find matching connection, using fallback logic`);
      console.log(`[CanvasArea] Available connections:`, props.connections);
      console.log(`[CanvasArea] Available blocks:`, props.blocks.map(b => ({id: b.id, name: b.name})));
      
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
      
      // 🔥 transit 엔티티 표시 - 더 눈에 잘 띄는 스타일
      const entitySize = 35;
      const transitRect = new Konva.Rect({
        x: middleX - entitySize / 2,
        y: middleY - entitySize / 2,
        width: entitySize,
        height: entitySize,
        fill: '#9B59B6', // 보라색 - transit 상태 구분
        stroke: '#8E44AD', // 진한 보라색 테두리
        strokeWidth: 3,
        cornerRadius: 5, // 모서리 둥글게
        shadowColor: 'black',
        shadowBlur: 4,
        shadowOffset: { x: 2, y: 2 },
        shadowOpacity: 0.5
      });
      
      // 엔티티 번호 텍스트
      let entityNumber;
      const idMatch = entity.id.match(/-e(\d+)$/);
      if (idMatch) {
        entityNumber = parseInt(idMatch[1]);
      } else {
        entityNumber = index + 1;
      }
      
      const transitText = new Konva.Text({
        x: middleX - entitySize / 2,
        y: middleY - entitySize / 2,
        text: String(entityNumber),
        fontSize: 14,
        fill: 'white',
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
      
      console.log(`[CanvasArea] Added transit entity #${entityNumber} (${entity.id}) at connection middle (${middleX}, ${middleY})`);
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
    
    console.log(`[CanvasArea] Added transit entity #${entityNumber} (${entity.id}) at screen center`);
  }
}

function updateEntities() {
  console.log("[CanvasArea] updateEntities called with", props.activeEntityStates.length, "entities");
  console.log("[CanvasArea] activeEntityStates detail:", JSON.stringify(props.activeEntityStates, null, 2));
  
  if (!entityTextGroup.value) {
    console.log("[CanvasArea] Creating entityTextGroup");
    entityTextGroup.value = new Konva.Group();
    layer.add(entityTextGroup.value);
    // 엔티티 그룹을 최상단으로 이동하여 다른 요소들 위에 표시되도록 함
    entityTextGroup.value.moveToTop();
    console.log("[CanvasArea] EntityTextGroup moved to top");
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
  
  console.log("[CanvasArea] Entities by block:", entitiesByBlock);
  
  // 전역 엔티티 번호 카운터
  let globalEntityNumber = 1;
  
  // 각 블록에 엔티티 네모로 표시
  entitiesByBlock.forEach((entities, blockId) => {
    // 🔥 transit 상태 엔티티 처리
    if (blockId === "transit") {
      console.log(`[CanvasArea] Found ${entities.length} transit entities - will display on connections`);
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
          console.log(`[CanvasArea] Creating entity rect for ${entity.id} at (${block.x + entityX}, ${block.y + entityY})`);
          
          // 엔티티 네모 - 더 눈에 잘 띄도록 스타일 강화
          const entityRect = new Konva.Rect({
            x: block.x + entityX,
            y: block.y + entityY,
            width: entitySize,
            height: entitySize,
            fill: '#FF6B35', // 주황색
            stroke: '#D63031', // 진한 빨간색 테두리
            strokeWidth: 2,
            cornerRadius: 1,
            shadowColor: 'black',
            shadowBlur: 2,
            shadowOffset: { x: 1, y: 1 },
            shadowOpacity: 0.3
          });
          
          // 엔티티 번호 텍스트 - ID에서 숫자 추출 또는 전역 카운터 사용
          let entityNumber;
          
          // 엔티티 ID에서 번호 추출 시도 (예: "1-e1" -> "1", "1-e2" -> "2")
          console.log(`[CanvasArea] Processing entity ID: ${entity.id}`);
          const idMatch = entity.id.match(/-e(\d+)$/);
          if (idMatch) {
            entityNumber = parseInt(idMatch[1]);
            console.log(`[CanvasArea] Extracted number from ID: ${entityNumber}`);
          } else {
            // ID에서 번호를 추출할 수 없으면 전역 카운터 사용
            entityNumber = globalEntityNumber++;
            console.log(`[CanvasArea] Using global counter: ${entityNumber}`);
          }
          const fontSize = entities.length === 1 ? 16 : 12; // 14->16, 10->12로 증가
          const entityText = new Konva.Text({
            x: block.x + entityX,
            y: block.y + entityY,
            text: String(entityNumber),
            fontSize: fontSize,
            fill: 'white',
            fontStyle: 'bold',
            width: entitySize,
            height: entitySize,
            align: 'center',
            verticalAlign: 'middle'
          });
          
          entityTextGroup.value.add(entityRect);
          entityTextGroup.value.add(entityText);
          console.log(`[CanvasArea] Added entity #${entityNumber} (${entity.id}) rect and text to group at position (${block.x + entityX}, ${block.y + entityY}) in block ${block.name}`);
        } else {
          console.warn(`[CanvasArea] Entity ${entity.id} out of bounds: entityX=${entityX}, entityY=${entityY}, blockWidth=${blockWidth}, blockHeight=${blockHeight}`);
        }
      });
    } else {
      // 🔥 블록을 찾을 수 없는 경우 로그 출력 및 임시 표시
      console.warn(`[CanvasArea] Block not found for blockId: ${blockId}, entities:`, entities);
      
      // transit이 아닌데 블록이 없는 경우에도 연결선 위에 표시
      entities.forEach((entity, index) => {
        console.log(`[CanvasArea] Displaying unmatched entity ${entity.id} on connections`);
        displayTransitEntity(entity, index);
      });
    }
  });
  
  // 엔티티 그룹을 다시 최상단으로 이동하여 확실히 보이도록 함
  if (entityTextGroup.value) {
    entityTextGroup.value.moveToTop();
    console.log(`[CanvasArea] Entity update complete. Group children count: ${entityTextGroup.value.children.length}`);
    console.log(`[CanvasArea] EntityTextGroup z-index position: ${entityTextGroup.value.zIndex()}`);
  }
  
  // Force redraw after updating entities
  layer.draw();
  console.log("[CanvasArea] Layer redraw completed after entity update");
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
  gridLayer.batchDraw();
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
  
  console.log("[CanvasArea] resizeCanvas - 새로운 크기:", { width, height, containerRect });
  
  // 현재 Stage 크기와 비교해서 변경된 경우만 업데이트
  const currentWidth = stage.width();
  const currentHeight = stage.height();
  
  if (Math.abs(currentWidth - width) > 1 || Math.abs(currentHeight - height) > 1) {
    console.log("[CanvasArea] 크기 변경 감지:", { 
      from: { width: currentWidth, height: currentHeight }, 
      to: { width, height } 
    });
    
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
      
      console.log("[CanvasArea] Canvas 강제 크기 설정 완료:", {
        canvasWidth: canvas.width,
        canvasHeight: canvas.height,
        canvasStyleWidth: canvas.style.width,
        canvasStyleHeight: canvas.style.height,
        containerSize: { width, height }
      });
    }
    
    drawGrid();
    stage.batchDraw();
    console.log("[CanvasArea] 캔버스 크기 업데이트 완료:", { width, height });
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
  
  console.log(`[CanvasArea] 블록 중심: (${centerX}, ${centerY}), 스테이지 이동: (${newX}, ${newY})`);
  
  stage.position({ x: newX, y: newY });
  stage.batchDraw();
  drawGrid();
}

// Stage 이벤트 리스너 추가
function addStageEventListeners() {
  if (!stage) return;
  
  // 배경 클릭 처리
  stage.on('mousedown', (e) => {
    console.log(`[CanvasArea] 🎯 스테이지 마우스다운 - 대상:`, e.target?.constructor?.name || 'unknown');
    
    // 배경 클릭 감지 (Stage 자체를 클릭한 경우)
    if (e.target === stage) {
      console.log(`[CanvasArea] 배경 클릭 감지 - 선택 해제`);
      // 선택 해제를 위해 부모 컴포넌트에 이벤트 전송
      setTimeout(() => {
        if (props.selectedBlockId || props.selectedConnectorInfo) {
          emit('select-block', null); // null을 전달하여 선택 해제 신호
        }
      }, 50); // 다른 클릭 이벤트가 처리된 후 실행
    }
  });

  stage.on('dragstart', (e) => {
    console.log(`[CanvasArea] 🎯 스테이지 드래그 시작 - 대상:`, e.target?.constructor?.name || 'unknown');
  });

  stage.on('dragmove', (e) => {
    console.log(`[CanvasArea] 🎯 스테이지 드래그무브 - 대상:`, e.target?.constructor?.name || 'unknown');
  });

  console.log("[CanvasArea] Stage 이벤트 리스너 설정 완료");
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
    });
    
    console.log("[CanvasArea] Wheel 이벤트 리스너 설정 완료");
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
  console.log("[CanvasArea] blocks 변경됨");
  
  // 블록 위치가 변경되었는지 확인
  let positionChanged = false;
  if (oldBlocks && newBlocks.length === oldBlocks.length) {
    for (let i = 0; i < newBlocks.length; i++) {
      const newBlock = newBlocks[i];
      const oldBlock = oldBlocks.find(b => b.id === newBlock.id);
      if (oldBlock && (oldBlock.x !== newBlock.x || oldBlock.y !== newBlock.y)) {
        positionChanged = true;
        console.log(`[CanvasArea] Block ${newBlock.name} 위치 변경: (${oldBlock.x},${oldBlock.y}) → (${newBlock.x},${newBlock.y})`);
        break;
      }
    }
  }
  
  dirtyFlags.value.blocks = true;
  if (positionChanged) {
    dirtyFlags.value.connections = true;
  }
  
  if (stage) {
    drawCanvasContent();
    drawGrid();
    
    // 최초 로드 시에만 뷰 조정 (블록 개수가 증가한 경우)
    const isInitialLoad = !oldBlocks || oldBlocks.length === 0;
    if (isInitialLoad && props.blocks.length > 0) {
      setTimeout(() => {
        centerViewOnBlocks();
      }, 100);
    }
  }
}, { deep: true, flush: 'post' });

watch(() => props.connections, () => {
  console.log("[CanvasArea] connections 변경됨");
  dirtyFlags.value.connections = true;
  if (stage) {
    drawCanvasContent();
    drawGrid();
  }
}, { deep: true, flush: 'post' });

watch(() => props.currentSettings, () => {
  console.log("[CanvasArea] Settings changed");
  dirtyFlags.value.blocks = true;
  dirtyFlags.value.connections = true;
  if (stage) {
    drawCanvasContent();
    drawGrid();
  }
}, { deep: true, flush: 'post' });

watch(() => props.activeEntityStates, () => {
  console.log("[CanvasArea] activeEntityStates 변경됨:", props.activeEntityStates);
  dirtyFlags.value.entities = true;
  if (stage && layer) {
    drawCanvasContent();
  }
}, { deep: true });

// 선택 상태 변경 시 즉시 화면 업데이트 - 더 빠른 반응을 위해 sync 플러시 사용
watch(() => [props.selectedBlockId, props.selectedConnectorInfo], () => {
  console.log("[CanvasArea] Selection changed - blockId:", props.selectedBlockId, "connectorInfo:", props.selectedConnectorInfo);
  if (stage) {
    // 선택 상태만 변경되었으므로 블록 부분만 업데이트
    dirtyFlags.value.blocks = true;
    updateBlocks();
    layer.draw();
  }
}, { deep: true, flush: 'sync' }); // sync로 변경하여 즉시 반응

// 캔버스 컨테이너 크기에 영향을 주는 요소들 감시
watch(() => [props.showBlockSettingsPopup, props.showConnectorSettingsPopup], () => {
  console.log("[CanvasArea] Settings sidebar visibility changed");
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
  console.log("[CanvasArea] onMounted 시작");
  console.log("[CanvasArea] 받은 props:", {
    blocksCount: props.blocks.length,
    connectionsCount: props.connections.length,
    currentSettings: props.currentSettings
  });
  console.log("[CanvasArea] DOM 요소 상태:");
  console.log("  - canvasContainerRef:", canvasContainerRef.value);
  console.log("  - canvasContainerRef 부모:", canvasContainerRef.value?.parentElement);
  console.log("  - canvasContainerRef 클래스:", canvasContainerRef.value?.className);
  console.log("  - canvasContainerRef 크기:", {
    offsetWidth: canvasContainerRef.value?.offsetWidth,
    offsetHeight: canvasContainerRef.value?.offsetHeight,
    clientWidth: canvasContainerRef.value?.clientWidth,
    clientHeight: canvasContainerRef.value?.clientHeight,
    scrollWidth: canvasContainerRef.value?.scrollWidth,
    scrollHeight: canvasContainerRef.value?.scrollHeight
  });
  
  // 초기화 재시도 로직
  let retryCount = 0;
  const maxRetries = 5;
  
  function tryInitialize() {
    console.log(`[CanvasArea] 초기화 시도 ${retryCount + 1}/${maxRetries}`);
    
    const success = initKonva();
    
    if (success && stage) {
      console.log("[CanvasArea] Stage 생성 성공, 레이어 추가");
      
      // 레이어 생성 및 추가
      layer = new Konva.Layer();
      stage.add(layer);

      gridLayer = new Konva.Layer();
      stage.add(gridLayer);
      gridLayer.moveToBottom();
      drawGrid();

      console.log("[CanvasArea] 레이어 추가 완료, 컨텐츠 그리기");
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
      
      console.log("[CanvasArea] 캔버스 초기화 완전히 완료!");
    } else {
      retryCount++;
      if (retryCount < maxRetries) {
        console.log(`[CanvasArea] 초기화 실패, ${500 * retryCount}ms 후 재시도...`);
        setTimeout(tryInitialize, 500 * retryCount);
      } else {
        console.error("[CanvasArea] 최대 재시도 횟수 초과, 초기화 실패!");
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
          console.log("[CanvasArea] ResizeObserver 감지:", entry.contentRect);
          debouncedResize();
        }
      });
      
      resizeObserver.observe(canvasContainerRef.value);
      console.log("[CanvasArea] ResizeObserver 설정 완료");
    }
  }, 300);
  
  // window resize 이벤트 리스너 추가 (ResizeObserver 백업용)
  const handleResize = () => {
    console.log("[CanvasArea] window resize 이벤트");
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
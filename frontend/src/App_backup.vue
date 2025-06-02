<template>
  <div id="layout">
    <ControlPanel 
      :currentDispatchedProducts="dispatchedProductsFromSim"
      :currentProcessTime="processTimeFromSim" 
      :currentStepCount="currentStepCount"
      :initialSettings="currentSettings"
      :globalSignals="globalSignals"
      :isSimulationEnded="isSimulationEnded"
      :isFullExecutionRunning="isFullExecutionRunning"
      :isGlobalSignalPanelVisible="showGlobalSignalPanel"
      @step-simulation="handleStepSimulation"
      @step-based-run="handleStepBasedRun"
      @stop-full-execution="stopFullExecution"
      @reset-simulation-display="resetSimulationDisplay"
      @previous-step="handlePreviousStep"
      @update-settings="handleUpdateSettings" 
      @add-process-block="addNewBlockToCanvas"
      @export-configuration="handleExportConfiguration"
      @import-configuration="handleImportConfiguration"
      @toggle-global-signal-panel="toggleGlobalSignalPanelVisibility"
    />
    
    <div class="main-content">
      <div class="canvas-container">
        <CanvasArea 
          :blocks="blocks"
          :connections="connections"
          :current-settings="currentSettings"
          :selectedBlockId="selectedBlockId"
          :selectedConnectorInfo="selectedConnectorInfo"
          :active-entity-states="activeEntityStates"
          ref="canvasAreaRef"
          @select-block="handleBlockClicked"
          @select-connector="handleConnectorClicked"
          @update-block-position="handleUpdateBlockPosition"
        />
        
        <!-- 디버그 정보 표시 -->
        <div class="debug-info" v-if="showDebugInfo">
          <p>블록 수: {{ blocks.length }}</p>
          <p>연결 수: {{ connections.length }}</p>
          <p>박스 크기: {{ currentSettings.boxSize }}</p>
          <button @click="showDebugInfo = false">닫기</button>
        </div>
        
        <button class="debug-button" @click="toggleDebugInfo">🐛</button>
      </div>
      
      <div 
        class="settings-sidebar" 
        :class="{ collapsed: !showBlockSettingsPopup && !showConnectorSettingsPopup }">
        
        <!-- 블록 설정 팝업 - 더 안전한 조건부 렌더링 -->
        <template v-if="showBlockSettingsPopup && selectedBlockData">
          <BlockSettingsPopup 
            :key="`block-${selectedBlockData.id}`"
            :block-data="selectedBlockData" 
            :all-signals="getAllSignalNames() || []"
            :all-blocks="blocks || []"
            :is-sidebar="true"
            @close-popup="closeBlockSettingsPopup" 
            @save-block-settings="saveBlockSettings"
            @copy-block="handleCopyBlock"
            @delete-block="handleDeleteBlock"
            @add-connector="handleAddConnector"
            @change-block-name="handleChangeBlockName"
          />
        </template>
        
        <!-- 커넥터 설정 팝업 -->
        <template v-if="showConnectorSettingsPopup && selectedConnectorInfo">
          <ConnectorSettingsPopup
            :connector-info="selectedConnectorInfo"
            :all-signals="getAllSignalNames() || []"
            :all-blocks="blocks"
            :is-sidebar="true"
            @close-popup="closeConnectorSettingsPopup"
            @save-connector-settings="saveConnectorSettings"
            @change-connector-name="handleChangeConnectorName"
          />
        </template>
      </div>
    </div>
    
    <GlobalSignalPanel
      :signals="globalSignals"
      :is-visible="showGlobalSignalPanel" 
      @close-panel="handleCloseGlobalSignalPanel"
      @add-signal="handleAddGlobalSignal"
      @remove-signal="handleRemoveGlobalSignal"
      @update-signal-value="handleUpdateGlobalSignalValue"
      @edit-signal="handleEditGlobalSignal"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import ControlPanel from './components/ControlPanel.vue'
import CanvasArea from './components/CanvasArea.vue'
import BlockSettingsPopup from './components/BlockSettingsPopup.vue'
import ConnectorSettingsPopup from './components/ConnectorSettingsPopup.vue'
import GlobalSignalPanel from './components/GlobalSignalPanel.vue'

// 새로운 BlockManager 유틸리티 import
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
} from './utils/BlockManager.js'

const currentSettings = ref({
  boxSize: 100, // 기본 박스 크기
  fontSize: 14,  // 기본 폰트 크기
  deadlockTimeout: 20  // 데드락 감지 타임아웃 (초)
})

const canvasAreaRef = ref(null) // CanvasArea 컴포넌트의 참조
const showBlockSettingsPopup = ref(false)
const selectedBlockId = ref(null)

const showConnectorSettingsPopup = ref(false)
const selectedConnectorInfo = ref(null)

// App.vue에서 블록 및 연결 데이터 직접 관리
const blocks = ref([])
const connections = ref([])

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

const globalSignals = ref([])
const showGlobalSignalPanel = ref(true)

// 시뮬레이션 결과 표시용 상태 추가
const dispatchedProductsFromSim = ref(0)
const processTimeFromSim = ref(0)
const currentStepCount = ref(0)
const isFirstStep = ref(true) // 첫 스텝 실행 여부
const activeEntityStates = ref([]) // 활성 엔티티 상태 저장

// 스텝 히스토리 저장용 변수들 추가
const stepHistory = ref([]) // 각 스텝의 상태를 저장하는 배열
const maxHistorySize = 100 // 최대 히스토리 저장 개수
const isSimulationEnded = ref(false) // 시뮬레이션 종료 상태

// 디버그 정보 표시 변수
const showDebugInfo = ref(false)

// 스텝 기반 전체 실행
const isFullExecutionRunning = ref(false); // 전체 실행 상태 추가
const shouldStopFullExecution = ref(false); // 일시 정지 요청 플래그 추가

// 전역 신호는 base.json에서 로드됨
// globalSignals.value는 setupInitialScenario()에서 초기화됨

// App.vue에서 초기 시나리오 데이터를 설정
async function setupInitialScenario() {
  console.log("[App] Setting up initial scenario from base.json...");
  
  try {
    // base.json 파일에서 설정 로드
    const response = await fetch('http://localhost:8000/simulation/load-base-config');
    
    if (!response.ok) {
      throw new Error(`Failed to load base config: ${response.status}`);
    }
    
    const baseConfig = await response.json();
    console.log("[App] Base config loaded:", baseConfig);
    
    // 설정 적용
    if (baseConfig.settings) {
      currentSettings.value = { ...currentSettings.value, ...baseConfig.settings };
    }
    
    // 블록 설정 적용 (base.json의 원본 데이터를 그대로 사용)
    if (baseConfig.blocks) {
      blocks.value = baseConfig.blocks.map(block => ({
        ...block,
        // base.json에 width/height가 있으면 그대로 사용, 없으면 현재 설정 사용
        width: block.width || currentSettings.value.boxSize,
        height: block.height || currentSettings.value.boxSize,
        // connectionPoints는 base.json의 원본 위치 정보를 그대로 사용
        connectionPoints: (block.connectionPoints || []).map(cp => ({
          ...cp,
          // base.json에서 정의된 위치를 그대로 사용
          x: cp.x !== undefined ? cp.x : (cp.name === 'R' ? currentSettings.value.boxSize : 0),
          y: cp.y !== undefined ? cp.y : currentSettings.value.boxSize / 2
        }))
      }));
    }
    
    // 연결선 설정 적용
    if (baseConfig.connections) {
      connections.value = JSON.parse(JSON.stringify(baseConfig.connections));
    } else {
      connections.value = [];
    }
    
    // 전역 신호 설정 적용
    if (baseConfig.globalSignals) {
      globalSignals.value = baseConfig.globalSignals.map(signal => ({
        ...signal,
        initialValue: signal.initialValue !== undefined ? signal.initialValue : signal.value
      }));
    }
    
    console.log("[App] Initial configuration applied from base.json");
    console.log("[App] Blocks:", JSON.parse(JSON.stringify(blocks.value)));
    console.log("[App] Global signals:", JSON.parse(JSON.stringify(globalSignals.value)));
    
    // 조건부 실행 액션에서 연결선 자동 생성
    updateConnectionsFromRouteActions();
    
  } catch (error) {
    console.error("[App] Failed to load base config, using default:", error);
    
    // 실패 시 기본 설정 사용 (빈 설정)
    blocks.value = [];
    connections.value = [];
    globalSignals.value = [];
    
    alert("base.json 파일을 불러오는데 실패했습니다. 빈 화면으로 시작합니다.");
  }
}

function handleUpdateSettings(newSettings) {
  currentSettings.value = { ...currentSettings.value, ...newSettings }
  
  // 데드락 타임아웃 설정이 변경된 경우 백엔드에 전송
  if (newSettings.deadlockTimeout !== undefined) {
    updateBackendSettings({ deadlockTimeout: newSettings.deadlockTimeout });
  }
  
  // 블록 크기 변경 시 기존 블록들의 width/height 및 연결점 위치도 업데이트
  blocks.value = blocks.value.map(b => ({
    ...b,
    width: currentSettings.value.boxSize,
    height: currentSettings.value.boxSize,
    connectionPoints: (b.connectionPoints || []).map(cp => {
      let newX = cp.x, newY = cp.y
      if (cp.name === 'R') { newX = currentSettings.value.boxSize; newY = currentSettings.value.boxSize / 2 }
      else if (cp.name === 'L') { newX = 0; newY = currentSettings.value.boxSize / 2 }
      // TODO: T, B 및 기타 커넥터 위치 업데이트 로직 추가
      return { ...cp, x: newX, y: newY }
    })
  }))
}

// 백엔드 설정 업데이트 함수
async function updateBackendSettings(settings) {
  try {
    const response = await fetch('http://localhost:8000/simulation/update-settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings)
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('백엔드 설정 업데이트 성공:', result);
    } else {
      console.error('백엔드 설정 업데이트 실패:', response.status);
    }
  } catch (error) {
    console.error('백엔드 설정 업데이트 오류:', error);
  }
}

function addNewBlockToCanvas(name) {
  // 이름 유효성 검사
  const validation = validateBlockName(name, blocks.value);
  if (!validation.valid) {
    alert(validation.error);
    return;
  }
  
  // BlockManager를 사용하여 새 블록 생성
  const newBlock = createNewBlock(name, blocks.value, currentSettings.value);
  blocks.value.push(newBlock);
  
  console.log(`새 블록 생성됨: ${newBlock.name} (ID: ${newBlock.id})`);
  
  // 연결선 업데이트
  updateConnectionsFromRouteActions();
}

function handleBlockClicked(blockId) {
  console.log("[handleBlockClicked] 블록 선택/해제:", blockId);
  console.log("[handleBlockClicked] 현재 showBlockSettingsPopup:", showBlockSettingsPopup.value);
  
  try {
    // null이 전달된 경우 선택 해제
    if (blockId === null) {
      console.log("[handleBlockClicked] 선택 해제 요청");
      closeBlockSettingsPopup();
      closeConnectorSettingsPopup();
      return;
    }
    
    // 블록 존재 여부 확인
    const targetBlock = blocks.value.find(b => b.id === blockId);
    if (!targetBlock) {
      console.error("[handleBlockClicked] 블록을 찾을 수 없음:", blockId);
      return;
    }
    
    // 즉시 선택 상태 업데이트 (setTimeout 제거)
    selectedBlockId.value = blockId;
    selectedConnectorInfo.value = null; // 커넥터 선택 해제
    
    // 다른 팝업들을 닫고 블록 팝업 열기 (즉시 실행)
    showConnectorSettingsPopup.value = false;
    showBlockSettingsPopup.value = true;
    
    console.log("[handleBlockClicked] 즉시 설정 완료 - showBlockSettingsPopup:", showBlockSettingsPopup.value);
    console.log("[handleBlockClicked] 선택된 블록 데이터:", selectedBlockData.value);
    
  } catch (error) {
    console.error("[handleBlockClicked] 에러 발생:", error);
    closeBlockSettingsPopup();
  }
}

function handleUpdateBlockPosition({ id, x, y }) {
  console.log(`[App] 🔄 handleUpdateBlockPosition 호출됨 - 블록 ID: ${id}, 새 위치: (${x}, ${y})`);
  
  const block = blocks.value.find(b => b.id === id);
  if (block) {
    console.log(`[App] 🔄 블록 찾음: ${block.name}, 이전 위치: (${block.x}, ${block.y})`);
    block.x = x;
    block.y = y;
    console.log(`[App] ✅ 블록 위치 업데이트 완료: ${block.name}, 새 위치: (${block.x}, ${block.y})`);
    
    // 블록 위치 변경 후 연결선도 즉시 업데이트
    updateConnectionsFromRouteActions();
    console.log(`[App] 🔗 연결선 업데이트 완료`);
  } else {
    console.error(`[App] ❌ 블록을 찾을 수 없음: ID ${id}`);
    console.log(`[App] ❌ 현재 블록 목록:`, blocks.value.map(b => ({ id: b.id, name: b.name })));
  }
}

function closeBlockSettingsPopup() {
  console.log("[closeBlockSettingsPopup] 블록 팝업 닫기");
  try {
    showBlockSettingsPopup.value = false;
    selectedBlockId.value = null; // 즉시 선택 해제
  } catch (error) {
    console.error("[closeBlockSettingsPopup] 에러 발생:", error);
  }
}

function saveBlockSettings(blockId, newActions, maxCapacity, blockName) {
  const block = blocks.value.find(b => b.id === blockId)
  if (block) {
    block.actions = newActions
    if (maxCapacity !== undefined) {
      block.maxCapacity = maxCapacity;
    }
    if (blockName !== undefined && blockName.trim()) {
      block.name = blockName.trim();
    }
  }
  
  // route_to_connector 액션 변경 시 connections 배열 자동 업데이트
  updateConnectionsFromRouteActions();
  
  // 자동저장이므로 팝업을 닫지 않음
}

function handleConnectorClicked({ blockId, connectorId }) {
  console.log("[handleConnectorClicked] 커넥터 선택됨:", { blockId, connectorId });
  
  try {
    const block = blocks.value.find(b => b.id === blockId);
    if (!block || !block.connectionPoints) {
      console.error("[handleConnectorClicked] 블록 또는 커넥터를 찾을 수 없음:", { blockId, connectorId });
      return;
    }
    
    const connector = block.connectionPoints.find(cp => cp.id === connectorId);
    if (!connector) {
      console.error("[handleConnectorClicked] 커넥터를 찾을 수 없음:", connectorId);
      return;
    }
    
    // 즉시 선택 상태 업데이트 (setTimeout 제거)
    selectedBlockId.value = null; // 블록 선택 해제
    selectedConnectorInfo.value = {
      blockId: blockId,
      blockName: block.name,
      connectorId: connectorId,
      connectorName: connector.name || connector.id,
      actions: JSON.parse(JSON.stringify(connector.actions || [])),
      availableBlocks: blocks.value.filter(b => b.id !== blockId) // blocks.value 사용
    };
    
    // 다른 팝업들을 닫고 커넥터 팝업 열기 (즉시 실행)
    showBlockSettingsPopup.value = false;
    showConnectorSettingsPopup.value = true;
    
    console.log("[handleConnectorClicked] 즉시 설정 완료 - showConnectorSettingsPopup:", showConnectorSettingsPopup.value);
    
  } catch (error) {
    console.error("[handleConnectorClicked] 에러 발생:", error);
    closeConnectorSettingsPopup();
  }
}

function closeConnectorSettingsPopup() {
  console.log("[closeConnectorSettingsPopup] 커넥터 팝업 닫기");
  try {
    showConnectorSettingsPopup.value = false;
    selectedConnectorInfo.value = null; // 즉시 선택 해제
  } catch (error) {
    console.error("[closeConnectorSettingsPopup] 에러 발생:", error);
  }
}

function saveConnectorSettings(blockId, connectorId, newActions, newName) {
  const block = blocks.value.find(b => b.id === blockId)
  if (block) {
    const connector = (block.connectionPoints || []).find(cp => cp.id === connectorId)
    if (connector) {
      connector.actions = newActions
      if (newName) {
        connector.name = newName
      }
    }
  }
  
  // route_to_connector 액션을 기반으로 connections 배열 자동 업데이트
  updateConnectionsFromRouteActions();
  
  // 자동저장이므로 팝업을 닫지 않음 (블록 설정창과 동일하게 처리)
}

function toggleGlobalSignalPanelVisibility() {
  showGlobalSignalPanel.value = !showGlobalSignalPanel.value
}

function handleCloseGlobalSignalPanel() {
  showGlobalSignalPanel.value = false
}

function handleAddGlobalSignal(signal) {
  if (!globalSignals.value.find(s => s.name === signal.name)) {
    // 새 신호 추가 시 현재 값을 initialValue로도 설정
    const newSignal = { 
      ...signal, 
      initialValue: signal.value 
    };
    globalSignals.value.push(newSignal);
    console.log("Global signal added:", newSignal, "All global signals:", globalSignals.value)
  } else {
    alert("이미 존재하는 전역 신호 이름입니다.")
  }
}

function handleRemoveGlobalSignal(signalName) {
  globalSignals.value = globalSignals.value.filter(s => s.name !== signalName)
  console.log("Global signal removed:", signalName, "All global signals:", globalSignals.value)
}

function handleUpdateGlobalSignalValue(data) {
  console.log('[App] 전역 신호 값 업데이트:', data);
  const signal = globalSignals.value.find(s => s.name === data.name);
  if (signal) {
    signal.value = data.value;
  }
}

function handleEditGlobalSignal(data) {
  console.log('[App] 전역 신호 수정:', data);
  const signalIndex = globalSignals.value.findIndex(s => s.name === data.originalName);
  if (signalIndex !== -1) {
    // 신호 이름과 값 업데이트
    globalSignals.value[signalIndex].name = data.newName;
    globalSignals.value[signalIndex].value = data.newValue;
    
    // TODO: 7번 항목 - 이름 변경 시 모든 참조 업데이트
    if (data.originalName !== data.newName) {
      updateSignalReferences(data.originalName, data.newName);
    }
  }
}

function updateSignalReferences(oldName, newName) {
  // 모든 블록의 액션에서 신호 이름 참조 업데이트
  blocks.value.forEach(block => {
    // 블록 액션 업데이트
    if (block.actions) {
      block.actions.forEach(action => {
        updateActionSignalReferences(action, oldName, newName);
      });
    }
    
    // 연결점 액션 업데이트
    if (block.connectionPoints) {
      block.connectionPoints.forEach(cp => {
        if (cp.actions) {
          cp.actions.forEach(action => {
            updateActionSignalReferences(action, oldName, newName);
          });
        }
      });
    }
  });
}

function updateActionSignalReferences(action, oldName, newName) {
  // 신호 관련 액션의 파라미터 업데이트
  if (action.parameters) {
    if (action.parameters.signal_name === oldName) {
      action.parameters.signal_name = newName;
    }
    
    // 조건부 실행 스크립트 내의 신호 이름 업데이트
    if (action.type === 'conditional_branch' && action.parameters.script) {
      let script = action.parameters.script;
      
      // 더 정확한 정규식으로 신호 이름만 교체
      // 1. if 문에서 "신호이름 = 값" 형태
      script = script.replace(
        new RegExp(`(if\\s+)${escapeRegExp(oldName)}(\\s*=\\s*(true|false))`, 'g'),
        `$1${newName}$2`
      );
      
      // 2. wait 문에서 "신호이름 = 값" 형태
      script = script.replace(
        new RegExp(`(wait\\s+)${escapeRegExp(oldName)}(\\s*=\\s*(true|false))`, 'g'),
        `$1${newName}$2`
      );
      
      // 3. 신호 업데이트 "신호이름 = 값" 형태 (줄 시작부터)
      script = script.replace(
        new RegExp(`(^|\\n|\\t)${escapeRegExp(oldName)}(\\s*=\\s*(true|false))`, 'g'),
        `$1${newName}$2`
      );
      
      action.parameters.script = script;
    }
  }
}

function getAllSignalNames() {
  const signalNames = new Set()
  // 전역 신호 추가
  globalSignals.value.forEach(gs => signalNames.add(gs.name))

  blocks.value.forEach(block => {
    if (Array.isArray(block.actions)) {
      block.actions.forEach(action => {
        if (action.type === 'signal_create' && action.parameters && action.parameters.signal_name) {
          signalNames.add(action.parameters.signal_name)
        }
      })
    }
    if (Array.isArray(block.connectionPoints)) {
      block.connectionPoints.forEach(cp => {
        if (Array.isArray(cp.actions)) {
          cp.actions.forEach(action => {
            if (action.type === 'signal_create' && action.parameters && action.parameters.signal_name) {
              signalNames.add(action.parameters.signal_name)
            }
          })
        }
      })
    }
  })
  return Array.from(signalNames)
}

function getSimulationSetupData() {
  // 블록 이름을 실제 커넥터 ID로 변환하는 함수
  function convertBlockConnectorNameToId(blockName, connectorName) {
    const targetBlock = blocks.value.find(block => 
      block.name.toLowerCase() === blockName.toLowerCase()
    );
    
    if (!targetBlock) {
      console.warn(`[getSimulationSetupData] 블록을 찾을 수 없음: ${blockName}`);
      return null;
    }
    
    const targetConnector = targetBlock.connectionPoints?.find(cp => 
      (cp.name && cp.name.toLowerCase() === connectorName.toLowerCase()) ||
      cp.id.toLowerCase().includes(connectorName.toLowerCase())
    );
    
    if (!targetConnector) {
      console.warn(`[getSimulationSetupData] 커넥터를 찾을 수 없음: ${blockName}.${connectorName}`);
      console.warn(`[getSimulationSetupData] 사용 가능한 커넥터들:`, targetBlock.connectionPoints?.map(cp => cp.name || cp.id));
      return null;
    }
    
    console.log(`[getSimulationSetupData] 변환됨: ${blockName}.${connectorName} -> ${targetConnector.id}`);
    return targetConnector.id;
  }
  
  // 조건부 실행 스크립트에서 'go to' 명령어를 실제 ID로 변환하는 함수
  function convertScriptGoToCommands(script) {
    if (!script) return script;
    
    const lines = script.split('\n');
    const convertedLines = lines.map(line => {
      const trimmedLine = line.trim();
      const originalIndent = line.length - trimmedLine.length;
      
      // 'go to' 명령어 찾기
      if (trimmedLine.startsWith('go to ')) {
        const target = trimmedLine.replace('go to ', '').trim();
        let targetPath = target;
        let delay = '';
        
        // 딜레이가 포함된 경우 분리
        if (target.includes(',')) {
          const parts = target.split(',');
          targetPath = parts[0].trim();
          delay = ',' + parts.slice(1).join(',');
        }
        
        if (targetPath.includes('.')) {
          const [blockName, connectorName] = targetPath.split('.');
          const convertedId = convertBlockConnectorNameToId(blockName.trim(), connectorName.trim());
          
          if (convertedId) {
            const indent = ' '.repeat(originalIndent);
            return `${indent}go to ${convertedId}${delay}`;
          } else {
            console.warn(`[getSimulationSetupData] 변환 실패, 원본 유지: ${line}`);
            return line;
          }
        }
      }
      
      return line;
    });
    
    // 백엔드 파싱을 위해 공백 들여쓰기를 탭으로 변환
    const normalizedScript = convertedLines.join('\n').replace(/^ +/gm, (match) => {
      // 공백 4개를 탭 1개로 변환 (또는 공백 개수에 따라 적절한 탭 개수로)
      const spaceCount = match.length;
      const tabCount = Math.floor(spaceCount / 4) || (spaceCount > 0 ? 1 : 0);
      return '\t'.repeat(tabCount);
    });
    
    return normalizedScript;
  }
  
  // 액션에서 조건부 실행 스크립트 변환
  function convertActionScript(action) {
    if (action.type === 'conditional_branch' && action.parameters?.script) {
      const convertedScript = convertScriptGoToCommands(action.parameters.script);
      return {
        ...action,
        parameters: {
          ...action.parameters,
          script: convertedScript
        }
      };
    }
    return action;
  }

  // 블록 데이터에서 불필요한 UI 관련 속성(x, y, width, height) 제외하고 actions만 추출
  const apiBlocks = blocks.value.map(block => {
    let blockActions = block.actions ? JSON.parse(JSON.stringify(block.actions)) : [];
    
    // 블록 액션들의 조건부 실행 스크립트 변환
    blockActions = blockActions.map(convertActionScript);
    
    // 연결점 액션들을 블록 액션 리스트의 뒤에 추가 (original_connector_id로 구분)
    if (block.connectionPoints) {
      block.connectionPoints.forEach(cp => {
        if (cp.actions && cp.actions.length > 0) {
          let cpActions = JSON.parse(JSON.stringify(cp.actions)).map(act => ({...act, original_connector_id: cp.id }));
          // 연결점 액션들의 조건부 실행 스크립트도 변환
          cpActions = cpActions.map(convertActionScript);
          blockActions = blockActions.concat(cpActions);
        }
      });
    }
    return {
      id: String(block.id), // ID는 문자열로 통일
      name: block.name,
      maxCapacity: block.maxCapacity || 1, // 최대 투입 수량 정보 추가
      actions: blockActions,
    };
  });

  // 현재 globalSignals의 모든 신호를 initial_signals에 포함
  const apiInitialSignals = {};
  globalSignals.value.forEach(signal => {
    apiInitialSignals[signal.name] = signal.value;
  });

  const simSetupData = {
    blocks: apiBlocks,
    connections: JSON.parse(JSON.stringify(connections.value)), // connections 명시적 추가
    initial_entities: 1, 
    initial_signals: apiInitialSignals
  };
  console.log("Prepared simulation setup data:", JSON.parse(JSON.stringify(simSetupData)));
  return simSetupData;
}

async function handleRunSimulation(options) {
  const setupData = getSimulationSetupData()
  if (!setupData) return

  const runOptions = {
    ...setupData,
    initial_entities: options.quantity || 1, 
  }
  
  const timeInSeconds = parseTimeToSeconds(options.time)
  if (timeInSeconds !== null) {
      runOptions.stop_time = timeInSeconds; 
  } else if (options.quantity > 0) {
      // stop_entities_processed는 백엔드에서 processed_entities_count를 기준으로 판단하므로, 
      // 프론트에서는 initial_entities를 충분히 크게 보내거나, stop_time을 적절히 설정.
      // 여기서는 initial_entities를 투입 수량으로 사용하고, 백엔드가 이를 처리하도록 함.
      // 만약 투입 수량만큼만 배출하고 멈추려면, 백엔드의 stop_entities_processed 로직 활용.
      // 여기서는 stop_time이 없으면, initial_entities만큼 소스에서 생성하고 알아서 멈추도록 기대.
      // 또는 명시적으로 stop_entities_processed를 설정하려면:
      // runOptions.stop_entities_processed = options.quantity;
  } else {
      alert("유효한 투입 수량 또는 진행 시간을 지정해주세요.")
      return
  }

  console.log("백엔드로 전달할 전체 실행 설정:", JSON.stringify(runOptions, null, 2))
  try {
    dispatchedProductsFromSim.value = 0
    processTimeFromSim.value = 0
    currentStepCount.value = 0 // 전체 실행 시 스텝 카운트도 초기화
    activeEntityStates.value = [] // 초기화
    isFirstStep.value = true // 전체 실행 후에는 다음 스텝이 첫 스텝이 되도록 설정

    const response = await fetch('http://localhost:8000/simulation/run', { 
        method: 'POST', 
        body: JSON.stringify(runOptions), 
        headers: {'Content-Type': 'application/json'} 
    })
    if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error ${response.status}`)
    }
    const result = await response.json()
    console.log("시뮬레이션 결과:", result)
    dispatchedProductsFromSim.value = result.total_entities_processed
    processTimeFromSim.value = parseFloat(result.final_time.toFixed(2))
    activeEntityStates.value = result.active_entities || [] // 엔티티 상태 업데이트
    alert(`시뮬레이션 완료: 최종 시간 ${result.final_time.toFixed(2)}, 처리된 엔티티 ${result.total_entities_processed}`)
  } catch (error) {
    console.error("시뮬레이션 실행 오류:", error)
    alert(`시뮬레이션 실행 중 오류 발생: ${error.message}`)
  }
}

async function handleStepSimulation() {
  // 현재 상태를 히스토리에 저장 (스텝 실행 전)
  saveCurrentStateToHistory();
  
  let requestBody = null;
  let headers = {'Content-Type': 'application/json'} ;

  if (isFirstStep.value) { // isFirstStep 플래그 다시 사용
    const setupData = getSimulationSetupData();
    if (!setupData) {
        alert("시뮬레이션 설정을 먼저 구성해야 합니다.");
        return;
    }
    // 첫 스텝에서는 initial_entities를 1로 설정하거나, 사용자가 지정한 값으로 설정할 수 있습니다.
    // 여기서는 기본 시나리오에 따라 1로 고정하거나, 또는 getSimulationSetupData에서 설정된 값을 그대로 사용합니다.
    // 현재 getSimulationSetupData는 initial_entities: 1 로 하드코딩 되어 있습니다.
    requestBody = JSON.stringify(setupData);
    console.log("백엔드로 전달할 첫 스텝 실행 설정:", setupData);
  } else {
    console.log("백엔드로 전달할 후속 스텝 실행 (setup 데이터 없음)");
    // 후속 스텝에서는 body를 보내지 않음 (백엔드 Optional[SimulationSetup] = None)
  }

  try {
    const fetchOptions = {
        method: 'POST',
        headers: headers
    };
    if (requestBody) {
        fetchOptions.body = requestBody;
    }

    const response = await fetch('http://localhost:8000/simulation/step', fetchOptions);
    
    if (!response.ok) {
        const errorData = await response.json();
        // 후속 스텝에서 에러 발생 시 isFirstStep을 true로 되돌릴지 고려
        if (response.status === 400 && errorData.detail && errorData.detail.includes("Simulation setup must be provided")) {
             isFirstStep.value = true; // 서버가 setup을 요구하면 다음번엔 setup을 보내도록 함
        }
        throw new Error(errorData.detail || `HTTP error ${response.status}`);
    }
    const result = await response.json();
    console.log("스텝 결과 (App.vue):", JSON.parse(JSON.stringify(result)));
    console.log("스텝 결과 - entities_processed_total (App.vue):", result.entities_processed_total);
    
    // 시뮬레이션 종료 체크
    if (result.event_description && result.event_description.includes("Simulation ended")) {
      console.log("시뮬레이션이 종료되었습니다:", result.event_description);
      isSimulationEnded.value = true;
    } else {
      isSimulationEnded.value = false;
    }
    
    currentStepCount.value++; 
    dispatchedProductsFromSim.value = result.entities_processed_total; 
    processTimeFromSim.value = parseFloat(result.time.toFixed(2));
    
    if (isFirstStep.value) { // 첫 스텝 성공 후 상태 변경
        isFirstStep.value = false; 
    }

    activeEntityStates.value = result.active_entities || [];
    
    // 백엔드로부터 받은 실시간 신호값을 globalSignals에 반영
    if (result.current_signals) {
      Object.entries(result.current_signals).forEach(([signalName, signalValue]) => {
        const existingSignalIndex = globalSignals.value.findIndex(s => s.name === signalName);
        if (existingSignalIndex !== -1) {
          // 기존 신호값 업데이트
          globalSignals.value[existingSignalIndex] = {
            ...globalSignals.value[existingSignalIndex],
            value: signalValue
          };
        } else {
          // 새로운 신호 추가 (백엔드에서 생성된 신호)
          globalSignals.value.push({
            name: signalName,
            value: signalValue
          });
        }
      });
    }
    
    console.log(`스텝 ${currentStepCount.value} 완료: 시간 ${result.time.toFixed(2)}, 배출 ${result.entities_processed_total}, ${result.event_description}`);
    
  } catch (error) {
    console.error("스텝 실행 오류:", error);
    alert(`스텝 실행 중 오류 발생: ${error.message}`);
  }
}

// 현재 상태를 히스토리에 저장하는 함수
function saveCurrentStateToHistory() {
  const currentState = {
    stepCount: currentStepCount.value,
    dispatchedProducts: dispatchedProductsFromSim.value,
    processTime: processTimeFromSim.value,
    globalSignals: JSON.parse(JSON.stringify(globalSignals.value)),
    activeEntityStates: JSON.parse(JSON.stringify(activeEntityStates.value)),
    isFirstStep: isFirstStep.value,
    timestamp: Date.now()
  };
  
  stepHistory.value.push(currentState);
  
  // 히스토리 크기 제한
  if (stepHistory.value.length > maxHistorySize) {
    stepHistory.value.shift(); // 가장 오래된 히스토리 제거
  }
  
  console.log(`스텝 히스토리 저장됨: 스텝 ${currentState.stepCount}, 히스토리 총 ${stepHistory.value.length}개`);
}

// 이전 스텝으로 되돌리는 함수
function handlePreviousStep() {
  if (stepHistory.value.length === 0) {
    alert("되돌릴 이전 상태가 없습니다.");
    return;
  }
  
  // 확인 팝업 제거하고 바로 실행
  // 가장 최근 히스토리 복원
  const previousState = stepHistory.value.pop();
  
  currentStepCount.value = previousState.stepCount;
  dispatchedProductsFromSim.value = previousState.dispatchedProducts;
  processTimeFromSim.value = previousState.processTime;
  globalSignals.value = JSON.parse(JSON.stringify(previousState.globalSignals));
  activeEntityStates.value = JSON.parse(JSON.stringify(previousState.activeEntityStates));
  isFirstStep.value = previousState.isFirstStep;
  
  console.log(`스텝 ${previousState.stepCount}으로 되돌렸습니다. 남은 히스토리: ${stepHistory.value.length}개`);
}

// 시간 문자열을 초로 변환하는 함수
function parseTimeToSeconds(timeStr) {
  const match = timeStr.match(/^(\d+)([smh])$/);
  if (!match) return null;
  
  const value = parseInt(match[1]);
  const unit = match[2];
  
  if (unit === 's') return value;
  if (unit === 'm') return value * 60;
  if (unit === 'h') return value * 3600;
  
  return null;
}

function resetSimulationDisplay() {
    dispatchedProductsFromSim.value = 0;
    processTimeFromSim.value = 0;
    currentStepCount.value = 0; 
    isFirstStep.value = true; // 시뮬레이션 초기화 시 첫 스텝으로 리셋 (복원)
    activeEntityStates.value = []; 
    stepHistory.value = []; // 히스토리도 초기화
    isSimulationEnded.value = false; // 종료 상태 리셋
    
    // 전역 신호들을 각각의 초기값으로 리셋
    globalSignals.value.forEach(signal => {
      if (signal.initialValue !== undefined) {
        signal.value = signal.initialValue;
      }
    });
    
    console.log("시뮬레이션 표시 상태가 초기화되었습니다. 전역 신호들이 초기값으로 리셋되었습니다.");
}

// 스텝 기반 전체 실행
async function handleStepBasedRun(options) {
  console.log("스텝 기반 전체 실행 시작:", options);
  
  isFullExecutionRunning.value = true; // 전체 실행 시작
  shouldStopFullExecution.value = false; // 정지 플래그 초기화
  
  try {
    if (options.mode === 'quantity') {
      // 수량 기반 실행
      const targetQuantity = options.value;
      const startingProducts = dispatchedProductsFromSim.value;
      
      console.log(`목표 수량: ${targetQuantity}, 시작 배출량: ${startingProducts}`);
      
      let attempts = 0;
      
      while (dispatchedProductsFromSim.value - startingProducts < targetQuantity && !shouldStopFullExecution.value) {
        attempts++;
        await handleStepSimulation();
        
        // 매 10스텝마다 잠시 대기 (UI 업데이트를 위해)
        if (attempts % 10 === 0) {
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      }
      
      console.log(`수량 기반 실행 완료: ${attempts}스텝 실행, 배출량 ${dispatchedProductsFromSim.value}`);
      
    } else if (options.mode === 'time') {
      // 시간 기반 실행
      const targetTimeSeconds = parseTimeToSeconds(options.value);
      if (!targetTimeSeconds) {
        alert("잘못된 시간 형식입니다. 예: 100s, 30m, 1h");
        return;
      }
      
      const startingTime = processTimeFromSim.value;
      console.log(`목표 시간: ${targetTimeSeconds}초, 시작 시간: ${startingTime}`);
      
      let attempts = 0;
      
      while (processTimeFromSim.value - startingTime < targetTimeSeconds && !shouldStopFullExecution.value) {
        attempts++;
        await handleStepSimulation();
        
        // 매 10스텝마다 잠시 대기 (UI 업데이트를 위해)
        if (attempts % 10 === 0) {
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      }
      
      console.log(`시간 기반 실행 완료: ${attempts}스텝 실행, 진행 시간 ${processTimeFromSim.value.toFixed(2)}초`);
    }
    
  } catch (error) {
    console.error('스텝 기반 전체 실행 중 오류:', error);
    alert('전체 실행 중 오류가 발생했습니다: ' + error.message);
  } finally {
    isFullExecutionRunning.value = false; // 전체 실행 종료
    shouldStopFullExecution.value = false; // 정지 플래그 초기화
  }
}

// 전체 실행 일시 정지 함수 추가
function stopFullExecution() {
  shouldStopFullExecution.value = true;
  console.log("전체 실행 일시 정지 요청됨");
}

// 설정 파일 다운로드
function handleExportConfiguration() {
  const config = {
    settings: currentSettings.value,
    blocks: JSON.parse(JSON.stringify(blocks.value)),
    connections: JSON.parse(JSON.stringify(connections.value)),
    globalSignals: JSON.parse(JSON.stringify(globalSignals.value)),
    simulationState: {
      dispatchedProducts: dispatchedProductsFromSim.value,
      processTime: processTimeFromSim.value,
      currentStepCount: currentStepCount.value,
      isFirstStep: isFirstStep.value
    },
    timestamp: new Date().toISOString(),
    version: "1.0"
  };
  
  const configStr = JSON.stringify(config, null, 2);
  const blob = new Blob([configStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = `simulation-config-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  console.log("설정 파일이 다운로드되었습니다.");
}

// 설정 파일 업로드
function handleImportConfiguration(config) {
  try {
    console.log("불러온 설정:", config);
    
    // 버전 확인
    if (config.version !== "1.0") {
      if (!confirm("다른 버전의 설정 파일입니다. 계속하시겠습니까?")) {
        return;
      }
    }
    
    // 설정 적용
    if (config.settings) {
      currentSettings.value = { ...currentSettings.value, ...config.settings };
    }
    
    if (config.blocks) {
      blocks.value = JSON.parse(JSON.stringify(config.blocks));
    }
    
    if (config.connections) {
      connections.value = JSON.parse(JSON.stringify(config.connections));
    }
    
    if (config.globalSignals) {
      // 불러온 신호들에 initialValue가 없으면 현재 value를 initialValue로 설정
      const processedSignals = config.globalSignals.map(signal => ({
        ...signal,
        initialValue: signal.initialValue !== undefined ? signal.initialValue : signal.value
      }));
      globalSignals.value = JSON.parse(JSON.stringify(processedSignals));
    }
    
    // 설정 불러오기 후 route_to_connector 액션 기반으로 connections 재구성
    updateConnectionsFromRouteActions();
    
    // 시뮬레이션 상태 복원 (선택사항)
    if (config.simulationState) {
      const shouldRestoreSimState = confirm("시뮬레이션 진행 상태도 복원하시겠습니까? (아니오를 선택하면 초기 상태로 시작됩니다)");
      if (shouldRestoreSimState) {
        dispatchedProductsFromSim.value = config.simulationState.dispatchedProducts || 0;
        processTimeFromSim.value = config.simulationState.processTime || 0;
        currentStepCount.value = config.simulationState.currentStepCount || 0;
        isFirstStep.value = config.simulationState.isFirstStep !== undefined ? config.simulationState.isFirstStep : true;
      } else {
        resetSimulationDisplay();
      }
    } else {
      resetSimulationDisplay();
    }
    
    console.log("설정이 성공적으로 적용되었습니다.");
    
  } catch (error) {
    console.error("설정 적용 중 오류:", error);
    alert("설정을 적용하는 중 오류가 발생했습니다: " + error.message);
  }
}

// route_to_connector 액션을 기반으로 connections 배열 자동 업데이트
function updateConnectionsFromRouteActions() {
  console.log("[updateConnectionsFromRouteActions] 시작 - 현재 블록 수:", blocks.value.length);
  const newConnections = [];
  
  // 조건부 실행 스크립트에서 라우팅 액션 추출하는 함수
  function extractRoutingFromScript(script, fromBlock, fromConnector) {
    console.log(`[extractRoutingFromScript] 스크립트 분석 시작 - 블록: ${fromBlock.name}, 커넥터: ${fromConnector.id || fromConnector.name}`);
    console.log(`[extractRoutingFromScript] 스크립트 내용:`, script);
    
    if (!script) return [];
    
    const lines = script.split('\n');
    const routings = [];
    
    lines.forEach((line, lineIndex) => {
      // 원본 라인과 트림된 라인 모두 체크
      const trimmedLine = line.trim();
      
      // go to 명령어 찾기 (탭이나 들여쓰기와 관계없이)
      if (trimmedLine.startsWith('go to ')) {
        console.log(`[extractRoutingFromScript] 'go to' 명령어 발견 (라인 ${lineIndex + 1}):`, trimmedLine);
        
        const target = trimmedLine.replace('go to ', '').trim();
        
        // 딜레이가 포함된 경우 제거
        let targetPath = target;
        if (target.includes(',')) {
          targetPath = target.split(',')[0].trim();
        }
        
        if (targetPath.includes('.')) {
          const [blockName, connectorName] = targetPath.split('.');
          const cleanBlockName = blockName.trim();
          const cleanConnectorName = connectorName.trim();
          
          console.log(`[extractRoutingFromScript] 파싱된 대상: 블록="${cleanBlockName}", 커넥터="${cleanConnectorName}"`);
          
          // self가 아닌 경우에만 연결선 생성
          if (cleanBlockName !== 'self') {
            // 블록 이름으로 대상 블록 찾기
            const targetBlock = blocks.value.find(block => 
              block.name.toLowerCase() === cleanBlockName.toLowerCase()
            );
            
            if (targetBlock) {
              console.log(`[extractRoutingFromScript] 대상 블록 찾음:`, targetBlock.name);
              
              // 커넥터 이름으로 대상 커넥터 찾기
              const targetConnector = targetBlock.connectionPoints?.find(cp => 
                (cp.name && cp.name.toLowerCase() === cleanConnectorName.toLowerCase()) ||
                cp.id.toLowerCase().includes(cleanConnectorName.toLowerCase())
              );
              
              if (targetConnector) {
                console.log(`[extractRoutingFromScript] 대상 커넥터 찾음:`, targetConnector.name || targetConnector.id);
                
                routings.push({
                  from_block_id: String(fromBlock.id),
                  from_connector_id: fromConnector.id || fromConnector.name || 'block-action',
                  to_block_id: String(targetBlock.id),
                  to_connector_id: targetConnector.id,
                  from_conditional_script: true // 조건부 스크립트에서 생성된 연결선임을 표시
                });
                console.log(`[extractRoutingFromScript] 연결선 추가됨: ${fromBlock.name}.${fromConnector.name || fromConnector.id} -> ${targetBlock.name}.${targetConnector.name || targetConnector.id}`);
              } else {
                console.warn(`[extractRoutingFromScript] 연결점을 찾을 수 없음: ${cleanBlockName}.${cleanConnectorName}`);
                console.warn(`[extractRoutingFromScript] 사용 가능한 연결점들:`, targetBlock.connectionPoints?.map(cp => cp.name || cp.id));
              }
            } else {
              console.warn(`[extractRoutingFromScript] 블록을 찾을 수 없음: ${cleanBlockName}`);
              console.warn(`[extractRoutingFromScript] 사용 가능한 블록들:`, blocks.value.map(b => b.name));
            }
          } else {
            console.log(`[extractRoutingFromScript] self 라우팅은 연결선을 생성하지 않음`);
          }
        } else {
          console.warn(`[extractRoutingFromScript] 잘못된 go to 형식 (라인 ${lineIndex + 1}):`, targetPath);
        }
      }
    });
    
    console.log(`[extractRoutingFromScript] 총 ${routings.length}개의 라우팅 추출됨`);
    return routings;
  }
  
  blocks.value.forEach(fromBlock => {
    console.log(`[updateConnectionsFromRouteActions] 블록 ${fromBlock.name} 검사 중...`);
    
    // 블록 액션 검사
    (fromBlock.actions || []).forEach((action, index) => {
      console.log(`[updateConnectionsFromRouteActions] 블록 액션 ${index} 검사:`, action.type);
      
      if (action.type === 'route_to_connector' && 
          action.parameters && 
          action.parameters.target_block_id && 
          action.parameters.target_connector_id &&
          action.parameters.target_connector_id !== 'self') {
        
        const connection = {
          from_block_id: String(fromBlock.id),
          from_connector_id: 'block-action', // 블록 액션의 경우 특별한 ID 사용
          to_block_id: String(action.parameters.target_block_id),
          to_connector_id: action.parameters.target_connector_id
        };
        
        newConnections.push(connection);
        console.log(`[updateConnectionsFromRouteActions] 블록 액션에서 연결선 추가:`, connection);
      } else if (action.type === 'conditional_branch' && action.parameters?.script) {
        console.log(`[updateConnectionsFromRouteActions] 블록 액션에서 조건부 실행 발견:`, action);
        // 조건부 실행에서 라우팅 추출 (블록 액션에서)
        const conditionalRoutings = extractRoutingFromScript(
          action.parameters.script, 
          fromBlock, 
          { id: 'block-action', name: 'block-action' }
        );
        newConnections.push(...conditionalRoutings);
      }
    });
    
    // 커넥터 액션 검사
    (fromBlock.connectionPoints || []).forEach(fromCp => {
      console.log(`[updateConnectionsFromRouteActions] 커넥터 ${fromCp.id} 검사 중...`);
      
      (fromCp.actions || []).forEach((action, index) => {
        console.log(`[updateConnectionsFromRouteActions] 커넥터 액션 ${index} 검사:`, action.type);
        
        if (action.type === 'route_to_connector' && 
            action.parameters && 
            action.parameters.target_block_id && 
            action.parameters.target_connector_id &&
            action.parameters.target_connector_id !== 'self') {
          
          const connection = {
            from_block_id: String(fromBlock.id),
            from_connector_id: fromCp.id,
            to_block_id: String(action.parameters.target_block_id),
            to_connector_id: action.parameters.target_connector_id
          };
          
          newConnections.push(connection);
          console.log(`[updateConnectionsFromRouteActions] 커넥터 액션에서 연결선 추가:`, connection);
        } else if (action.type === 'conditional_branch' && action.parameters?.script) {
          console.log(`[updateConnectionsFromRouteActions] 커넥터 액션에서 조건부 실행 발견:`, action);
          // 조건부 실행에서 라우팅 추출 (커넥터 액션에서)
          const conditionalRoutings = extractRoutingFromScript(
            action.parameters.script, 
            fromBlock, 
            fromCp
          );
          newConnections.push(...conditionalRoutings);
        }
      });
    });
  });
  
  // 중복 연결 제거
  const uniqueConnections = [];
  newConnections.forEach(connection => {
    const isDuplicate = uniqueConnections.some(conn => 
      conn.from_block_id === connection.from_block_id &&
      conn.from_connector_id === connection.from_connector_id &&
      conn.to_block_id === connection.to_block_id &&
      conn.to_connector_id === connection.to_connector_id
    );
    
    if (!isDuplicate) {
      uniqueConnections.push(connection);
    }
  });
  
  connections.value = uniqueConnections;
  console.log("[updateConnectionsFromRouteActions] 완료 - 최종 연결선 수:", connections.value.length);
  console.log("[updateConnectionsFromRouteActions] 최종 연결선 목록:", JSON.parse(JSON.stringify(connections.value)));
}

// 블록 복사 기능
function handleCopyBlock(sourceBlockId) {
  const sourceBlock = blocks.value.find(b => b.id === sourceBlockId);
  if (!sourceBlock) {
    console.error("복사할 블록을 찾을 수 없습니다:", sourceBlockId);
    return;
  }

  // 새 블록 ID 생성
  const newId = blocks.value.length > 0 ? Math.max(...blocks.value.map(b => b.id)) + 1 : 1;
  
  // 복사된 블록 생성 (약간 오프셋된 위치에 배치)
  const copiedBlock = {
    id: newId,
    name: `${sourceBlock.name} 복사본`,
    x: sourceBlock.x + 50, // 오른쪽으로 50px 이동
    y: sourceBlock.y + 50, // 아래쪽으로 50px 이동
    width: sourceBlock.width,
    height: sourceBlock.height,
    maxCapacity: sourceBlock.maxCapacity || 1,
    actions: JSON.parse(JSON.stringify(sourceBlock.actions || [])), // 깊은 복사
    connectionPoints: []
  };

  // 연결점 복사 (ID 변경 필요)
  if (sourceBlock.connectionPoints) {
    copiedBlock.connectionPoints = sourceBlock.connectionPoints.map(cp => {
      const newConnectorId = cp.id.replace(String(sourceBlockId), String(newId));
      return {
        id: newConnectorId,
        name: cp.name,
        x: cp.x,
        y: cp.y,
        actions: JSON.parse(JSON.stringify(cp.actions || [])) // 깊은 복사
      };
    });
  }

  // 복사된 블록을 blocks 배열에 추가
  blocks.value.push(copiedBlock);
  
  // connections 배열 자동 업데이트
  updateConnectionsFromRouteActions();
  
  console.log(`블록 "${sourceBlock.name}" (ID: ${sourceBlockId})이 복사되어 새 블록 "${copiedBlock.name}" (ID: ${newId})으로 생성되었습니다.`);
}

// 블록 삭제 기능
function handleDeleteBlock(blockId) {
  const blockToDelete = blocks.value.find(b => b.id === blockId);
  if (!blockToDelete) {
    console.error("삭제할 블록을 찾을 수 없습니다:", blockId);
    return;
  }

  // 블록 배열에서 삭제
  blocks.value = blocks.value.filter(b => b.id !== blockId);
  
  // 삭제된 블록과 관련된 connections 제거
  connections.value = connections.value.filter(conn => 
    conn.from_block_id !== String(blockId) && 
    conn.to_block_id !== String(blockId)
  );
  
  // 다른 블록들의 route_to_connector 액션에서 삭제된 블록을 참조하는 경우 정리
  blocks.value.forEach(block => {
    // 블록 액션 정리
    if (block.actions) {
      block.actions = block.actions.filter(action => {
        if (action.type === 'route_to_connector' && 
            action.parameters && 
            action.parameters.target_block_id && 
            String(action.parameters.target_block_id) === String(blockId)) {
          console.warn(`블록 ${block.name}의 액션에서 삭제된 블록 ${blockId}에 대한 참조를 제거했습니다.`);
          return false;
        }
        return true;
      });
    }
    
    // 연결점 액션 정리
    if (block.connectionPoints) {
      block.connectionPoints.forEach(cp => {
        if (cp.actions) {
          cp.actions = cp.actions.filter(action => {
            if (action.type === 'route_to_connector' && 
                action.parameters && 
                action.parameters.target_block_id && 
                String(action.parameters.target_block_id) === String(blockId)) {
              console.warn(`블록 ${block.name}의 연결점 ${cp.name}에서 삭제된 블록 ${blockId}에 대한 참조를 제거했습니다.`);
              return false;
            }
            return true;
          });
        }
      });
    }
  });
  
  // connections 배열 자동 업데이트
  updateConnectionsFromRouteActions();
  
  console.log(`블록 "${blockToDelete.name}" (ID: ${blockId})이 삭제되었습니다. 관련 연결과 참조도 정리되었습니다.`);
  
  // 현재 선택된 블록이 삭제된 경우 팝업 닫기
  if (selectedBlockId.value === blockId) {
    closeBlockSettingsPopup();
  }
}

// 연결점 추가 기능
function handleAddConnector(blockId, connectorData) {
  const targetBlock = findBlockById(blocks.value, blockId);
  if (!targetBlock) {
    console.error("연결점을 추가할 블록을 찾을 수 없습니다:", blockId);
    return;
  }
  
  // 커넥터 이름 유효성 검사
  const validation = validateConnectorName(connectorData.name, targetBlock.connectionPoints || []);
  if (!validation.valid) {
    alert(validation.error);
    return;
  }
  
  // BlockManager를 사용하여 커넥터 추가
  if (!targetBlock.connectionPoints) {
    targetBlock.connectionPoints = [];
  }
  
  // 기존 방식 유지 (connectorData가 이미 완전한 형태로 전달됨)
  targetBlock.connectionPoints.push(connectorData);
  
  console.log(`블록 "${targetBlock.name}"에 연결점 "${connectorData.name}" (${connectorData.id})이 추가되었습니다.`);
  
  // connections 배열 자동 업데이트 (새 연결점으로 인한 라우팅 업데이트)
  updateConnectionsFromRouteActions();
}

// 디버그 정보 토글 함수
function toggleDebugInfo() {
  showDebugInfo.value = !showDebugInfo.value;
  console.log("[App] 디버그 정보 토글:", showDebugInfo.value);
  console.log("[App] 현재 상태:", {
    blocks: blocks.value.length,
    connections: connections.value.length,
    settings: currentSettings.value
  });
}

function handleChangeBlockName(blockId, oldName, newName) {
  console.log(`[App] 블록 이름 변경: ${oldName} -> ${newName} (블록 ID: ${blockId})`);
  
  // 이름 유효성 검사
  const validation = validateBlockName(newName, blocks.value, blockId);
  if (!validation.valid) {
    alert(validation.error);
    return;
  }
  
  // 블록 이름 업데이트
  const block = findBlockById(blocks.value, blockId);
  if (block) {
    block.name = newName;
    console.log(`[App] 블록 이름 업데이트 완료: ${block.name}`);
    
    // BlockManager를 사용하여 참조 업데이트
    updateBlockReferences(blocks.value, oldName, newName);
  } else {
    console.error(`[App] 블록을 찾을 수 없습니다: ${blockId}`);
  }
}

function handleChangeConnectorName(changeInfo) {
  console.log(`[App] 커넥터 이름 변경:`, changeInfo);
  
  const block = findBlockById(blocks.value, changeInfo.blockId);
  if (block && block.connectionPoints) {
    const connector = findConnectorById(block, changeInfo.connectorId);
    if (connector) {
      // 이름 유효성 검사
      const validation = validateConnectorName(changeInfo.newName, block.connectionPoints, changeInfo.connectorId);
      if (!validation.valid) {
        alert(validation.error);
        return;
      }
      
      const oldName = connector.name;
      connector.name = changeInfo.newName;
      console.log(`[App] 커넥터 이름 업데이트 완료: ${block.name}.${oldName} -> ${block.name}.${connector.name}`);
      
      // BlockManager를 사용하여 커넥터 참조 업데이트
      updateConnectorReferences(blocks.value, block.name, oldName, changeInfo.newName);
    } else {
      console.error(`[App] 커넥터를 찾을 수 없습니다: ${changeInfo.blockId}.${changeInfo.connectorId}`);
    }
  } else {
    console.error(`[App] 블록을 찾을 수 없습니다: ${changeInfo.blockId}`);
  }
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

onMounted(() => {
  console.log("[App] onMounted 시작");
  setupInitialScenario(); 
  
  // 초기 시나리오 설정 후 잠시 대기한 다음 상태 확인
  setTimeout(() => {
    console.log("[App] 초기화 완료 후 상태:");
    console.log("- blocks 개수:", blocks.value.length);
    console.log("- connections 개수:", connections.value.length);
    console.log("- blocks 데이터:", JSON.parse(JSON.stringify(blocks.value)));
    console.log("- connections 데이터:", JSON.parse(JSON.stringify(connections.value)));
    
    // 강제로 화면 업데이트 트리거
    if (blocks.value.length === 0) {
      console.log("[App] 블록이 없습니다. 초기 시나리오를 다시 설정합니다.");
      setupInitialScenario();
    }
  }, 100);
  
  // 키보드 단축키 지원
  const handleKeyDown = (event) => {
    // Ctrl+D: 선택된 블록 복사
    if (event.ctrlKey && event.key === 'd' && selectedBlockId.value) {
      event.preventDefault();
      handleCopyBlock(selectedBlockId.value);
    }
    // Delete: 선택된 블록 삭제
    if (event.key === 'Delete' && selectedBlockId.value) {
      event.preventDefault();
      handleDeleteBlock(selectedBlockId.value);
    }
  };
  
  document.addEventListener('keydown', handleKeyDown);
  
  // 컴포넌트 언마운트 시 이벤트 리스너 제거
  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown);
  });
});

</script>

<style scoped>
#layout {
  display: flex;
  width: 100%;
  height: 100vh;
  position: relative;
}

.main-content {
  display: flex;
  flex: 1;
  height: 100%;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  height: 100%;
}

.settings-sidebar {
  width: 450px;
  background-color: #f8f9fa;
  border-left: 1px solid #dee2e6;
  overflow-y: auto;
  transition: width 0.3s ease;
  z-index: 100;
}

.settings-sidebar.collapsed {
  width: 0;
  overflow: hidden;
}

.debug-info {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 10px;
  border-radius: 5px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.debug-button {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  font-size: 14px;
  cursor: pointer;
}
</style>

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
      @add-process-block="handleAddProcessBlock"
      @export-configuration="handleExportConfiguration"
      @import-configuration="handleImportConfiguration"
      @toggle-global-signal-panel="toggleGlobalSignalPanelVisibility"
      @panel-width-changed="handlePanelWidthChanged"
      @refresh-auto-connections="refreshAllAutoConnections"
    />
    
    <div class="main-content">
      <div class="canvas-container">
        <!-- 정보 텍스트 패널 -->
        <InfoTextPanel 
          :info-text="infoText"
          :control-panel-width="controlPanelWidth"
          :show-block-settings="showBlockSettingsPopup"
          @update:info-text="handleUpdateInfoText"
        />
        
        <CanvasArea 
          :blocks="blocks"
          :connections="connections"
          :current-settings="currentSettings"
          :selectedBlockId="selectedBlockId"
          :selectedConnectorInfo="selectedConnectorInfo"
          :active-entity-states="activeEntityStates"
          :showBlockSettingsPopup="showBlockSettingsPopup"
          :showConnectorSettingsPopup="showConnectorSettingsPopup"
          :blocks-with-errors="blocksWithErrors"
          ref="canvasAreaRef"
          @select-block="handleBlockClicked"
          @select-connector="handleConnectorClicked"
          @update-block-position="handleUpdateBlockPosition"
          @update-connector-position="handleUpdateConnectorPosition"
        />
        
        <!-- 디버그 정보 표시 -->
        <div class="debug-info" v-if="showDebugInfo">
          <p>블록 수: {{ blocks.length }}</p>
          <p>연결 수: {{ connections.length }}</p>
          <p>박스 크기: {{ currentSettings.boxSize }}</p>
          <p>제어판 너비: {{ controlPanelWidth }}px</p>
          <p>창 크기: {{ windowSize.width }}x{{ windowSize.height }}</p>
          <p>메인 컨텐츠 여백: {{ controlPanelWidth }}px</p>
          <div class="debug-colors">
            <div style="background: #f5f5f5; padding: 2px; margin: 1px; border: 1px solid #ccc;">⚪ main-content</div>
            <div style="background: #ffffff; padding: 2px; margin: 1px; border: 1px solid #ccc;">⚪ canvas-container</div>
            <div style="background: transparent; padding: 2px; margin: 1px; border: 1px solid #ccc;">⚪ konva-container</div>
            <div style="background: #e9ecef; padding: 2px; margin: 1px;">⚪ canvas-area</div>
          </div>
          <button @click="showDebugInfo = false">닫기</button>
        </div>
        
        <button class="debug-button" @click="toggleDebugInfo">🐛</button>
      </div>
      
      <div 
        v-if="showBlockSettingsPopup || showConnectorSettingsPopup"
        class="settings-sidebar">
        
        <!-- 블록 설정 팝업 -->
        <template v-if="showBlockSettingsPopup && selectedBlockData">
          <BlockSettingsPopup 
            :key="`block-${selectedBlockData.id}`"
            :block-data="selectedBlockData" 
            :all-signals="getAllSignalNamesFromBlocks(blocks)"
            :all-blocks="blocks"
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
            :all-signals="getAllSignalNamesFromBlocks(blocks)"
            :all-blocks="blocks"
            :is-sidebar="true"
            @close-popup="closeConnectorSettingsPopup"
            @save-connector-settings="saveConnectorSettings"
            @change-connector-name="handleChangeConnectorName"
            @delete-connector="handleDeleteConnector"
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
    
    <!-- 시뮬레이션 로그 패널 -->
    <LogPanel
      :logs="simulationLogs"
      :is-auto-scroll-enabled="isAutoScrollEnabled"
      :control-panel-width="controlPanelWidth"
      @clear-logs="clearSimulationLogs"
      @export-logs="exportSimulationLogs"
      @toggle-auto-scroll="toggleAutoScroll"
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
import InfoTextPanel from './components/InfoTextPanel.vue'
import LogPanel from './components/LogPanel.vue'

// Composables
import { useSimulation } from './composables/useSimulation.js'
import { useBlocks } from './composables/useBlocks.js'
import { useSimulationLogs } from './composables/useSimulationLogs.js'
import { useSignals } from './composables/useSignals.js'

// Services
import SimulationApi from './services/SimulationApi.js'

// 기본 설정
const currentSettings = ref({
  boxSize: 100,
  fontSize: 14,
  deadlockTimeout: 20
})

// 제어판 너비 관리
const controlPanelWidth = ref(300)

// 디버그 정보
const showDebugInfo = ref(false)
const canvasAreaRef = ref(null)

// 정보 텍스트
const infoText = ref({
  content: '시뮬레이션 정보를 입력하세요',
  style: {
    fontSize: 16,
    color: '#000000',
    fontWeight: 'normal'
  },
  isExpanded: false
})

// 창 크기 추적
const windowSize = ref({
  width: window.innerWidth,
  height: window.innerHeight
})

// Composables 사용
const {
  // 시뮬레이션 상태
  dispatchedProductsFromSim,
  processTimeFromSim,
  currentStepCount,
  isFirstStep,
  activeEntityStates,
  stepHistory,
  isSimulationEnded,
  isFullExecutionRunning,
  shouldStopFullExecution,
  
  // 계산된 속성
  hasStepHistory,
  canGoBack,
  
  // 메서드
  resetSimulationState,
  executeStep,
  executeBatchSteps,
  startStepBasedExecution,
  stopFullExecution,
  resetSimulation
} = useSimulation()

const {
  // 블록 상태
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
  setupInitialBlocks,
  updateBlocksForSettings,
  refreshAllAutoConnections
} = useBlocks()

const {
  // 신호 상태
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
  getAllSignalNamesFromBlocks,
  resetSignalsToInitialValues
} = useSignals()

// 시뮬레이션 로그 관리
const {
  logs: simulationLogs,
  addLogs: addSimulationLogs,
  clearLogs: clearSimulationLogs,
  exportLogs: exportSimulationLogs,
  isAutoScrollEnabled,
  toggleAutoScroll
} = useSimulationLogs()

// 초기 시나리오 설정
async function setupInitialScenario() {
  try {
    const baseConfig = await SimulationApi.loadBaseConfig()
    
    // 설정 적용
    if (baseConfig.settings) {
      currentSettings.value = { ...currentSettings.value, ...baseConfig.settings }
    }
    
    // 블록 설정 적용
    setupInitialBlocks(baseConfig, currentSettings.value)
    
    // 신호 설정 적용
    setupInitialSignals(baseConfig)
    
    // 초기 로드 후 자동 연결 새로고침 (모든 연결을 자동 생성으로 다시 생성)
    setTimeout(() => {
      refreshAllAutoConnections()
    }, 100)
  } catch (error) {
    console.error("[App] Failed to setup initial scenario:", error)
    alert(`초기 설정 로드 실패: ${error.message}`)
  }
}

// 설정 업데이트 처리
function handleUpdateSettings(newSettings) {
  currentSettings.value = { ...currentSettings.value, ...newSettings }
  
  // 블록 크기 업데이트
  updateBlocksForSettings(newSettings)
  
  // 백엔드 설정 업데이트
  updateBackendSettings(newSettings)
}

async function updateBackendSettings(settings) {
  try {
    await SimulationApi.updateSettings(settings)
  } catch (error) {
    console.error('[App] 백엔드 설정 업데이트 실패:', error)
  }
}

// 정보 텍스트 업데이트
function handleUpdateInfoText(updatedInfoText) {
  infoText.value = updatedInfoText
}

// 새 블록 추가 처리
function handleAddProcessBlock(name) {
  const newBlock = addNewBlockToCanvas(name, currentSettings.value)
  if (newBlock && canvasAreaRef.value) {
    // 캔버스 업데이트 (필요한 경우)
    canvasAreaRef.value.updateCanvas?.()
  }
}

// 시뮬레이션 실행 처리
async function handleStepSimulation() {
  // 첫 번째 스텝인 경우에만 설정 데이터 전송, 이후에는 null
  const setupData = isFirstStep.value ? getSimulationSetupData() : null
  const result = await executeStep(setupData, updateBlockWarnings, addSimulationLogs)
  
  if (!result.success) {
    alert(`시뮬레이션 실행 실패: ${result.error}`)
  } else {
    // 신호 상태 업데이트
    if (result.result) {
      updateSignalsFromSimulation(result.result)
    }
  }
}

// 블록 경고 상태 업데이트
function updateBlockWarnings(blockStates) {
  if (!blockStates) return
  
  // 각 블록의 경고 정보를 업데이트
  blocks.value.forEach(block => {
    const blockState = blockStates[block.id]
    if (blockState) {
      // 경고 정보 업데이트
      if (blockState.warnings) {
        block.warnings = blockState.warnings
      } else {
        block.warnings = []
      }
      
      // total_processed 정보 업데이트
      if (blockState.total_processed !== undefined) {
        block.totalProcessed = blockState.total_processed
      }
    }
  })
}

async function handleStepBasedRun(options) {
  // 첫 번째 스텝인 경우에만 설정 데이터 전송, 이후에는 null
  const setupData = isFirstStep.value ? getSimulationSetupData() : null
  
  await startStepBasedExecution(setupData, (result) => {
    // 신호 상태 업데이트
    updateSignalsFromSimulation(result)
  }, options, updateBlockWarnings, addSimulationLogs)
}


async function handlePreviousStep() {
  // 이전 스텝으로 되돌리기는 시뮬레이션 리셋 후 재실행으로 구현
  await resetSimulation()
  resetSignalsToInitialValues()
}

async function resetSimulationDisplay() {
  await resetSimulation()
  resetSignalsToInitialValues()
  clearSimulationLogs()
}

// 시뮬레이션 설정 데이터 생성
function getSimulationSetupData() {
  // 기존 변환 로직 유지 (간소화)
  const apiBlocks = blocks.value.map(block => ({
    id: String(block.id),
    name: block.name,
    type: "process",
    x: block.x,
    y: block.y,
    width: block.width,
    height: block.height,
    maxCapacity: block.maxCapacity || 1,
    capacity: block.maxCapacity || 1,  // ProcessBlockConfig 모델과 호환성을 위해 둘 다 전송
    script: block.script || '',  // script 필드 추가
    actions: block.actions || [],
    connectionPoints: (block.connectionPoints || []).map(cp => ({
      ...cp,
      id: String(cp.id),
      actions: (cp.actions || []).map(action => convertActionScript(action))
    }))
  }))
  
  // connections도 ID를 string으로 변환
  const apiConnections = connections.value.map(conn => ({
    ...conn,
    from_block_id: String(conn.from_block_id || conn.fromBlockId),
    to_block_id: String(conn.to_block_id || conn.toBlockId),
    from_connector_id: String(conn.from_connector_id || conn.fromConnectorId),
    to_connector_id: String(conn.to_connector_id || conn.toConnectorId)
  }))
  
  // globalSignals를 initial_signals로 변환 (백엔드 SimulationSetup 모델에 맞춤)
  const initial_signals = {}
  globalSignals.value.forEach(signal => {
    initial_signals[signal.name] = signal.value
  })
  
  // globalSignals 배열 형식도 추가 (타입 정보 포함)
  const globalSignalsArray = globalSignals.value.map(signal => ({
    name: signal.name,
    type: signal.type || (typeof signal.value === 'boolean' ? 'boolean' : 'integer'),
    value: signal.value,
    initialValue: signal.initialValue !== undefined ? signal.initialValue : signal.value
  }))
  
  return {
    blocks: apiBlocks,
    connections: apiConnections,
    initial_signals,  // backward compatibility
    globalSignals: globalSignalsArray,  // 새로운 형식 추가
    initial_entities: 1
  }
}

function convertActionScript(action) {
  if (action.type === 'conditional_branch' && action.parameters?.script) {
    return {
      ...action,
      parameters: {
        ...action.parameters,
        script: convertScriptGoToCommands(action.parameters.script)
      }
    }
  }
  return action
}

function convertScriptGoToCommands(script) {
  // 기존 변환 로직 유지 (간소화된 버전)
  const lines = script.split('\n')
  const convertedLines = lines.map(line => {
    const trimmedLine = line.trim()
    if (trimmedLine.startsWith('go to ')) {
      const target = trimmedLine.replace('go to ', '').trim()
      const [targetPath] = target.split(',')
      
      if (targetPath.includes('.')) {
        const [blockName, connectorName] = targetPath.split('.')
        const targetBlock = blocks.value.find(block => 
          block.name === blockName.trim() || block.id.toString() === blockName.trim()
        )
        
        if (targetBlock) {
          const targetConnector = targetBlock.connectionPoints?.find(cp => 
            cp.name === connectorName.trim()
          )
          
          if (targetConnector) {
            return line.replace(targetPath, `${targetBlock.id}.${targetConnector.id}`)
          }
        }
      }
    }
    return line
  })
  
  return convertedLines.join('\n')
}

// 설정 내보내기/가져오기
function handleExportConfiguration() {
  const config = {
    blocks: blocks.value,
    connections: connections.value,
    globalSignals: globalSignals.value,
    settings: currentSettings.value,
    infoText: infoText.value
  }
  
  const dataStr = JSON.stringify(config, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = 'simulation-config.json'
  link.click()
  
  URL.revokeObjectURL(url)
}

function handleImportConfiguration(config) {
  try {
    // 설정을 sessionStorage에 저장
    sessionStorage.setItem('pendingImportConfig', JSON.stringify(config));
    
    // 페이지 새로고침
    window.location.reload();
  } catch (error) {
    console.error('[App] 설정 저장 실패:', error);
    alert('설정 저장 중 오류가 발생했습니다: ' + error.message);
  }
}

// 실제 설정 적용 함수
function applyImportedConfiguration(config) {
  try {
    if (config.blocks) {
      // 블록 로드 시 script 필드가 있으면 script 타입 액션으로 변환
      blocks.value = config.blocks.map(block => {
        const processedBlock = { ...block };
        
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
              id: `script-action-${Date.now()}`,
              name: '스크립트 실행',
              type: 'script',
              parameters: {
                script: processedBlock.script
              }
            });
          }
        }
        
        // 모든 액션에 name 필드가 있는지 확인하고 없으면 추가
        if (processedBlock.actions) {
          processedBlock.actions = processedBlock.actions.map(action => {
            if (!action.name) {
              // 액션 타입에 따른 기본 이름 생성
              const defaultNames = {
                'script': '스크립트',
                'custom_sink': '배출',
                'delay': '대기',
                'signal_wait': '신호 대기',
                'signal_update': '신호 변경',
                'route_to_connector': '이동',
                'conditional_branch': '조건부 실행'
              };
              return {
                ...action,
                name: defaultNames[action.type] || action.type
              };
            }
            return action;
          });
        }
        
        return processedBlock;
      });
    }
    if (config.connections) {
      connections.value = config.connections;
    }
    if (config.globalSignals) {
      // 신호를 로드할 때 value를 initialValue로 리셋
      globalSignals.value = config.globalSignals.map(signal => ({
        ...signal,
        // type이 없으면 값에서 추론
        type: signal.type || (typeof signal.value === 'boolean' ? 'boolean' : 'integer'),
        // initialValue가 정의되어 있으면 그것을 사용, 아니면 기존 value 사용
        value: signal.initialValue !== undefined ? signal.initialValue : signal.value
      }));
    }
    if (config.settings) {
      currentSettings.value = { ...currentSettings.value, ...config.settings };
    }
    if (config.infoText) {
      infoText.value = config.infoText;
    }
    
    // 설정 적용 후 자동 연결 새로고침
    refreshAllAutoConnections();
  } catch (error) {
    console.error('[App] 설정 가져오기 실패:', error);
    alert('설정 적용 중 오류가 발생했습니다: ' + error.message);
  }
}

// 신호 편집 시 참조 업데이트
function handleEditGlobalSignalWithReferences(data) {
  handleEditGlobalSignal(data)
  if (data.originalName !== data.newName) {
    updateSignalReferences(data.originalName, data.newName, blocks.value)
  }
}

// 제어판 너비 변경 처리
function handlePanelWidthChanged(newWidth) {
  controlPanelWidth.value = newWidth
}

// 디버그 토글
function toggleDebugInfo() {
  showDebugInfo.value = !showDebugInfo.value
}

// 컴포넌트 마운트 시 초기화
onMounted(() => {
  // 대기 중인 import config가 있는지 확인
  const pendingConfig = sessionStorage.getItem('pendingImportConfig')
  if (pendingConfig) {
    try {
      const config = JSON.parse(pendingConfig)
      // sessionStorage에서 삭제
      sessionStorage.removeItem('pendingImportConfig')
      // 설정 적용
      applyImportedConfiguration(config)
    } catch (error) {
      console.error('[App] 저장된 설정 적용 실패:', error)
      // 실패 시에도 기본 시나리오 설정
      setupInitialScenario()
    }
  } else {
    // 대기 중인 설정이 없으면 기본 시나리오 설정
    setupInitialScenario()
  }
  
  // 창 크기 변경 감지
  const updateWindowSize = () => {
    windowSize.value = {
      width: window.innerWidth,
      height: window.innerHeight
    }
  }
  
  window.addEventListener('resize', updateWindowSize)
  
  // 컴포넌트 언마운트 시 정리
  const cleanup = () => {
    window.removeEventListener('resize', updateWindowSize)
  }
  
  onUnmounted(cleanup)
})

// 설정 변경 감지
watch(currentSettings, (newSettings) => {
  updateBackendSettings(newSettings)
}, { deep: true })
</script>

<style scoped>
#layout {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw; /* 전체 너비 명시 */
  background-color: #f5f5f5;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-width: 0; /* flex 축소 허용 */
  display: flex;
  flex-direction: row;
  overflow: hidden;
  background: #f5f5f5; /* 원래 배경색으로 복원 */
}

.canvas-container {
  flex: 1;
  min-width: 200px; /* 최소 너비 보장 */
  position: relative;
  background: #ffffff; /* 흰색 배경으로 설정 */
  overflow: hidden;
}

.settings-sidebar {
  width: 400px;
  background: #f8f9fa;
  border-left: 1px solid #ddd;
  transition: all 0.3s ease;
  overflow-y: auto;
  flex-shrink: 0;
  z-index: 200; /* 정보 텍스트창(z-index: 50)보다 위에 표시 */
  position: relative;
}

.debug-info {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 1000;
}

.debug-button {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  font-size: 20px;
  cursor: pointer;
  z-index: 100;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.debug-button:hover {
  background: #0056b3;
  transform: scale(1.1);
}
</style> 
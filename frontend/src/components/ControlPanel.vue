<template>
  <div class="control-panel" :style="{ width: panelWidth }">
    <button @click="togglePanel" class="toggle-button">
      {{ isMinimized ? '최대화' : '최소화' }}
    </button>
    <div v-show="!isMinimized" class="panel-content">
      <h3>제어판</h3>
      
      <!-- 실행 모드 선택 -->
      <div class="execution-mode-selector">
        <label>실행 모드:</label>
        <select v-model="selectedExecutionMode" @change="changeExecutionMode" :disabled="isRunning">
          <option value="default">기본 모드 (엔티티 이벤트)</option>
          <option value="time_step">시간 스텝 모드</option>
          <option value="high_speed">고속 진행 모드</option>
        </select>
      </div>
      
      <!-- 시간 스텝 모드 설정 -->
      <div v-if="selectedExecutionMode === 'time_step'" class="time-step-config">
        <h5>시간 스텝 설정</h5>
        <div class="config-row">
          <label>1스텝 = </label>
          <input 
            type="number" 
            v-model.number="timeStepDuration" 
            step="0.1" 
            min="0.1" 
            max="3600"
            class="time-input"
          /> 
          <span> 초</span>
          <button @click="saveTimeStepConfig" :disabled="isRunning" class="save-config-btn">설정</button>
        </div>
        <small class="help-text">스텝 실행 시 이 시간만큼 시뮬레이션이 진행됩니다</small>
      </div>
      
      <!-- 고속 진행 모드 설정 -->
      <div v-if="selectedExecutionMode === 'high_speed'" class="high-speed-config">
        <h5>고속 진행 모드 설정</h5>
        
        <div class="termination-conditions">
          <h6>종료 조건 (하나 이상 선택):</h6>
          
          <div class="condition-row">
            <label>
              <input type="checkbox" v-model="highSpeedConfig.useEntityCount" />
              목표 엔티티 처리 수:
            </label>
            <input 
              type="number" 
              v-model.number="highSpeedConfig.targetEntityCount" 
              :disabled="!highSpeedConfig.useEntityCount"
              min="1" 
              placeholder="예: 100"
              class="condition-input"
            />
            <span>개</span>
          </div>
          
          <div class="condition-row">
            <label>
              <input type="checkbox" v-model="highSpeedConfig.useSimulationTime" />
              목표 시뮬레이션 시간:
            </label>
            <input 
              type="number" 
              v-model.number="highSpeedConfig.targetSimulationTime" 
              :disabled="!highSpeedConfig.useSimulationTime"
              min="1" 
              placeholder="예: 3600"
              class="condition-input"
            />
            <span>초</span>
          </div>
          
          <div class="config-row">
            <button @click="saveHighSpeedConfig" :disabled="isRunning || !isHighSpeedConfigValid" class="save-config-btn">설정</button>
          </div>
        </div>
        
        <small class="help-text">
          고속 모드는 매우 큰 시간 스텝으로 실행하여 종료 조건에 도달할 때까지 빠르게 진행합니다.
          <br>적어도 하나의 종료 조건을 설정해야 합니다.
        </small>
      </div>
      
      <div>배출된 제품: {{ currentDispatchedProducts }} 개</div>
      <div>진행 시간: {{ currentProcessTime.toFixed(1) }} 초</div>
      <div>실행된 스텝 수: {{ currentStepCount }} 회</div>
      
      <button @click="stepExecution" :disabled="isPaused" :title="isPaused ? '브레이크포인트에서 멈춤. 계속 실행을 눌러주세요.' : ''">스텝 실행</button>
      <button @click="handleFullExecutionToggle">
        {{ isFullExecutionRunning ? '일시 정지' : '전체 실행 시작' }}
      </button>
      <button @click="previousExecution" disabled style="opacity: 0.5; cursor: not-allowed;" title="이전 단계로 되돌아가는 기능은 아직 구현되지 않았습니다.">이전 실행</button>
      <button @click="resetSimulationDisplayInternal" class="reset-button">시뮬레이션 초기화</button>

      <!-- 디버그 제어 섹션 -->
      <div class="debug-section" v-if="showDebugControls">
        <h4>디버그 제어</h4>
        <div class="debug-status">{{ debugStatus }}</div>
        
        <!-- 브레이크포인트 목록 -->
        <div class="breakpoint-list" v-if="hasBreakpoints">
          <h5>활성 브레이크포인트:</h5>
          <ul>
            <li v-for="(lines, blockId) in currentBreakpoints" :key="blockId">
              {{ getBlockName(blockId) }}: 라인 {{ lines.join(', ') }}
            </li>
          </ul>
        </div>
        
        <div class="debug-controls">
          <button @click="continueExecution" :disabled="!isPaused" class="continue-btn">
            계속 실행
          </button>
          <button @click="clearAllBreakpoints" class="clear-btn">
            모든 브레이크포인트 제거
          </button>
        </div>
      </div>

      <div>
        <h4>전체 실행 옵션</h4>
        <div class="execution-options">
          <div class="option-group">
            <label>
              <input type="radio" v-model="executionMode" value="quantity" />
              투입 수량
            </label>
            <input 
              type="number" 
              v-model.number="inputQuantity" 
              :disabled="executionMode !== 'quantity'"
              min="1" 
              placeholder="수량 입력"
              class="option-input"
            />
            <span v-if="executionMode === 'quantity'">개</span>
          </div>
          
          
          <div class="option-group">
            <label>
              <input type="radio" v-model="executionMode" value="time" />
              진행 시간
            </label>
            <input 
              type="text" 
              v-model="runTimeInput" 
              :disabled="executionMode !== 'time'"
              placeholder="예: 100s, 30m, 1h"
              class="option-input"
            />
          </div>
        </div>
      </div>

      <button @click="openSettingsPopup">설정</button>
      <button @click="triggerAddProcessBlock">공정 블록 추가</button>
      <small class="info-text">💡 블록 클릭 후 복사(Ctrl+D) 또는 삭제(Delete) 가능</small>
      <button @click="refreshAutoConnections" class="refresh-connections-btn">🔗 자동 연결 새로고침</button>
      <small class="info-text">💡 go to 액션에서 자동으로 연결선 생성</small>
      <button @click="saveConfiguration">저장</button>
      <button @click="loadConfiguration">불러오기</button>

      <!-- 전역 신호 관리 버튼 -> 패널 토글 버튼으로 역할 변경 -->
      <button @click="toggleGlobalSignalPanel">전역 신호 패널 {{props.isGlobalSignalPanelVisible ? '숨기기' : '보이기'}}</button>
    </div>

    <!-- Settings Popup -->
    <div v-if="showSettingsPopup" class="popup-overlay" @click.self="closeSettingsPopup">
      <div class="popup">
        <h4>시뮬레이션 설정</h4>
        
        <div class="settings-section">
          <h5>화면 표시 설정</h5>
          <label for="box-size">박스 크기 (px):</label>
          <input type="number" id="box-size" v-model.number="editableSettings.boxSize" min="10">
          <br>
          <label for="font-size">폰트 크기 (px):</label>
          <input type="number" id="font-size" v-model.number="editableSettings.fontSize" min="5">
        </div>
        
        <div class="settings-section">
          <h5>시뮬레이션 설정</h5>
          <label for="deadlock-timeout">데드락 감지 시간 (초):</label>
          <input type="number" id="deadlock-timeout" v-model.number="editableSettings.deadlockTimeout" min="5" max="300">
          <small class="help-text">엔티티 이동이 없을 때 데드락으로 판단할 시간 (5~300초)</small>
        </div>
        
        <br>
        <button @click="applySettings">적용</button>
        <button @click="closeSettingsPopup">닫기</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  initialSettings: {
    type: Object,
    default: () => ({ boxSize: 100, fontSize: 14, deadlockTimeout: 20 })
  },
  // globalSignals prop은 더 이상 ControlPanel에서 직접 사용하지 않음 (App.vue가 GlobalSignalPanel로 직접 전달)
  isGlobalSignalPanelVisible: { // App.vue로부터 패널 표시 여부를 받음
      type: Boolean,
      default: false
  },
  currentDispatchedProducts: { type: Number, default: 0 },
  currentProcessTime: { type: Number, default: 0 },
  currentStepCount: { // 추가된 prop
    type: Number,
    default: 0
  },
  globalSignals: { type: Array, default: () => [] },
  isSimulationEnded: { type: Boolean, default: false },
  isFullExecutionRunning: { type: Boolean, default: false },
  blocks: { type: Array, default: () => [] }
})

const emit = defineEmits([
    'update-settings', 
    'add-process-block', 
    'run-simulation', 
    'step-simulation', 
    'step-based-run',
    'stop-full-execution',
    'toggle-global-signal-panel',
    'reset-simulation-display', // App.vue로 이벤트 전달
    'export-configuration',
    'import-configuration',
    'previous-step',
    'panel-width-changed', // 패널 너비 변경 이벤트 추가
    'refresh-auto-connections',
    'clear-all-breakpoints' // 브레이크포인트 제거 이벤트 추가
])

const inputQuantity = ref(10) // 투입 수량은 로컬에서 관리
const runTimeInput = ref("100s") // 진행 시간 입력은 로컬에서 관리
const executionMode = ref("quantity") // 실행 모드 선택 (quantity 또는 time)

const isMinimized = ref(false)
const panelWidth = computed(() => (isMinimized.value ? '50px' : '300px'))

// 실행 모드 관련
const selectedExecutionMode = ref('default')
const isRunning = computed(() => props.isFullExecutionRunning)

// 시간 스텝 모드 관련
const timeStepDuration = ref(1.0)  // 기본값 1초

// 고속 진행 모드 관련
const highSpeedConfig = ref({
  useEntityCount: false,
  targetEntityCount: 100,
  useSimulationTime: false,
  targetSimulationTime: 3600,
  largeTimeStep: 9000000  // 기본 9백만초
})

// 고속 모드 설정 유효성 검사
const isHighSpeedConfigValid = computed(() => {
  return highSpeedConfig.value.useEntityCount || highSpeedConfig.value.useSimulationTime
})

// 브레이크포인트가 있는지 확인하는 computed
const hasBreakpoints = computed(() => {
  const keys = Object.keys(currentBreakpoints.value)
  return keys.length > 0
})

// 디버그 상태
const showDebugControls = ref(true) // 디버그 컨트롤 표시 여부
const isDebugging = ref(false)
const isPaused = ref(false)
const debugStatus = ref('')
const currentBreakpoints = ref({}) // blockId -> array of line numbers

const showSettingsPopup = ref(false)
// editableSettings는 팝업 내에서 임시로 수정되는 값들을 다룹니다.
const editableSettings = ref({ boxSize: 100, fontSize: 14, deadlockTimeout: 20 })

// Prop으로 받은 initialSettings를 editableSettings의 초기값으로 설정
onMounted(() => {
  editableSettings.value = { ...props.initialSettings }
})

// Props가 외부에서 변경될 때 editableSettings도 동기화
watch(() => props.initialSettings, (newSettings) => {
  editableSettings.value = { ...newSettings }
}, { deep: true })

function togglePanel() {
  isMinimized.value = !isMinimized.value
  // 패널 너비 변경 알림
  emit('panel-width-changed', isMinimized.value ? 50 : 300)
}

function stepExecution() {
  if (props.isSimulationEnded) {
    alert("시뮬레이션이 이미 종료되었습니다. 초기화 후 다시 실행해주세요.");
    alert("시뮬레이션이 종료되었습니다. 초기화 버튼을 눌러 다시 시작해주세요.");
    return;
  }
  emit('step-simulation'); 
}

function handleFullExecutionToggle() {
  if (props.isFullExecutionRunning) {
    emit('stop-full-execution');
  } else {
    
    if (executionMode.value === 'quantity') {
      if (!inputQuantity.value || inputQuantity.value <= 0) {
        alert("올바른 투입 수량을 입력해주세요 (1 이상)");
        return;
      }
      emit('step-based-run', { 
        mode: 'quantity', 
        value: inputQuantity.value 
      });
    } else if (executionMode.value === 'time') {
      if (!runTimeInput.value) {
        alert("진행 시간을 입력해주세요 (예: 100s, 30m, 1h)");
        return;
      }
      emit('step-based-run', { 
        mode: 'time', 
        value: runTimeInput.value 
      });
    }
  }
}


function resetSimulationDisplayInternal() {
  // 전체 실행이 진행 중이면 먼저 정지
  if (props.isFullExecutionRunning) {
    emit('stop-full-execution');
  }
  
  // 확인 창 표시
  if (confirm("시뮬레이션 진행 상태를 초기화하시겠습니까? (캔버스 배치는 유지됩니다)")) {
    emit('reset-simulation-display'); // App.vue로 이벤트 전달
  }
}

function previousExecution() {
  // 이전 실행 기능은 아직 구현되지 않음
  alert("이전 단계로 되돌아가는 기능은 아직 구현되지 않았습니다.");
}

// 디버그 관련 함수들
async function continueExecution() {
  try {
    const SimulationApi = (await import('../services/SimulationApi.js')).default
    const result = await SimulationApi.debugContinue()
    
    if (result && result.success) {
      isPaused.value = false
      debugStatus.value = '실행 재개됨'
      // 계속 실행 후 스텝 실행
      emit('step-simulation')
    }
  } catch (error) {
    console.error('Failed to continue execution:', error)
    alert(`디버그 계속 실행 실패: ${error.message}`)
  }
}

async function clearAllBreakpoints() {
  if (confirm('모든 브레이크포인트를 제거하시겠습니까?')) {
    emit('clear-all-breakpoints')
    currentBreakpoints.value = {}
    debugStatus.value = '모든 브레이크포인트 제거됨'
  }
}

function getBlockName(blockId) {
  // props.blocks에서 블록 이름 찾기
  if (props.blocks && Array.isArray(props.blocks)) {
    const block = props.blocks.find(b => String(b.id) === String(blockId))
    if (block) {
      return block.name
    }
  }
  return `블록 ${blockId}`
}

// 디버그 상태 업데이트 (시뮬레이션 결과에서 호출)
function updateDebugStatus(debugInfo) {
  if (debugInfo) {
    isDebugging.value = debugInfo.is_debugging
    isPaused.value = debugInfo.is_paused
    
    if (debugInfo.is_paused && debugInfo.current_break) {
      const blockName = getBlockName(debugInfo.current_break.block_id)
      debugStatus.value = `브레이크포인트: ${blockName} 라인 ${debugInfo.current_break.line}`
    } else if (debugInfo.is_debugging) {
      debugStatus.value = '디버그 모드 실행 중'
    } else {
      debugStatus.value = '디버그 모드 비활성'
    }
    
    // 브레이크포인트 목록 업데이트
    if (debugInfo.breakpoints) {
      currentBreakpoints.value = debugInfo.breakpoints
    }
  }
}

function parseTimeToSeconds(timeStr) {
  const match = timeStr.match(/^(\d+)([smh])$/);
  if (!match) return null;
  const value = parseInt(match[1]);
  const unit = match[2];
  if (unit === 's') return value;
  if (unit === 'm') return value * 60;
  if (unit === 'h') return value * 60 * 60;
  return null;
}

// 외부에서 디버그 상태 업데이트를 위해 노출
defineExpose({
  updateDebugStatus,
  updateBreakpoints
})

// 브레이크포인트 목록 업데이트
function updateBreakpoints(breakpoints) {
  currentBreakpoints.value = breakpoints
}

function openSettingsPopup() {
  // 팝업을 열 때 현재 적용된 설정값(props.initialSettings)으로 editableSettings를 다시 설정
  editableSettings.value = { ...props.initialSettings };
  showSettingsPopup.value = true
}

function closeSettingsPopup() {
  showSettingsPopup.value = false
}

function applySettings() {
  emit('update-settings', { ...editableSettings.value })
  closeSettingsPopup()
}

function triggerAddProcessBlock() {
  const processName = prompt("공정 블록 이름을 입력하세요:");
  if (processName) {
    emit('add-process-block', processName);
  }
}

function refreshAutoConnections() {
  emit('refresh-auto-connections');
}

function saveConfiguration() {
  // 전체 시뮬레이션 설정을 JSON으로 구성
  const config = {
    settings: props.initialSettings,
    blocks: [], // App.vue로부터 받아와야 함
    connections: [], // App.vue로부터 받아와야 함
    globalSignals: [], // App.vue로부터 받아와야 함
    timestamp: new Date().toISOString(),
    version: "1.0"
  };
  
  // 설정을 App.vue로부터 받아오기 위해 이벤트 발송
  emit('export-configuration', config);
}

function loadConfiguration() {
  // 파일 입력 엘리먼트 생성
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const config = JSON.parse(text);
      
      // 설정을 App.vue로 전달하여 적용
      emit('import-configuration', config);
      alert("설정을 성공적으로 불러왔습니다!");
    } catch (error) {
      console.error("설정 파일 로드 오류:", error);
      alert("설정 파일을 읽는 중 오류가 발생했습니다: " + error.message);
    }
  };
  input.click();
}

function toggleGlobalSignalPanel() {
    emit('toggle-global-signal-panel');
}

// 실행 모드 관련 함수들
import SimulationApi from '../services/SimulationApi'

async function changeExecutionMode() {
  try {
    let config = {}
    
    // 시간 스텝 모드인 경우 설정 포함
    if (selectedExecutionMode.value === 'time_step') {
      config = { step_duration: timeStepDuration.value }
    }
    // 고속 모드인 경우 기본 설정 포함
    else if (selectedExecutionMode.value === 'high_speed') {
      config = buildHighSpeedConfig()
    }
    
    await SimulationApi.setExecutionMode(selectedExecutionMode.value, config)
  } catch (error) {
    alert(error.message)
    // 실패 시 원래 모드로 복원
    selectedExecutionMode.value = 'default'
  }
}

async function saveTimeStepConfig() {
  try {
    const config = { step_duration: timeStepDuration.value }
    await SimulationApi.setExecutionMode('time_step', config)
    alert(`시간 스텝 모드가 ${timeStepDuration.value}초로 설정되었습니다.`)
  } catch (error) {
    alert(`설정 저장 실패: ${error.message}`)
  }
}

// 고속 모드 설정 빌드
function buildHighSpeedConfig() {
  const config = {
    large_time_step: highSpeedConfig.value.largeTimeStep
  }
  
  if (highSpeedConfig.value.useEntityCount) {
    config.target_entity_count = highSpeedConfig.value.targetEntityCount
  }
  
  if (highSpeedConfig.value.useSimulationTime) {
    config.target_simulation_time = highSpeedConfig.value.targetSimulationTime
  }
  
  return config
}

async function saveHighSpeedConfig() {
  try {
    if (!isHighSpeedConfigValid.value) {
      alert('적어도 하나의 종료 조건을 설정해야 합니다.')
      return
    }
    
    const config = buildHighSpeedConfig()
    await SimulationApi.setExecutionMode('high_speed', config)
    
    let message = '고속 진행 모드가 설정되었습니다.\n종료 조건: '
    const conditions = []
    
    if (config.target_entity_count) {
      conditions.push(`엔티티 ${config.target_entity_count}개 처리`)
    }
    if (config.target_simulation_time) {
      conditions.push(`시간 ${config.target_simulation_time}초 경과`)
    }
    
    message += conditions.join(' 또는 ')
    alert(message)
  } catch (error) {
    alert(`설정 저장 실패: ${error.message}`)
  }
}

// 컴포넌트 마운트 시 현재 모드 조회
onMounted(async () => {
  try {
    const { mode, config } = await SimulationApi.getExecutionMode()
    selectedExecutionMode.value = mode
    
    // 시간 스텝 모드인 경우 설정도 로드
    if (mode === 'time_step' && config && config.step_duration) {
      timeStepDuration.value = config.step_duration
    }
    // 고속 모드인 경우 설정도 로드
    else if (mode === 'high_speed' && config) {
      if (config.large_time_step) {
        highSpeedConfig.value.largeTimeStep = config.large_time_step
      }
      if (config.target_entity_count) {
        highSpeedConfig.value.useEntityCount = true
        highSpeedConfig.value.targetEntityCount = config.target_entity_count
      }
      if (config.target_simulation_time) {
        highSpeedConfig.value.useSimulationTime = true
        highSpeedConfig.value.targetSimulationTime = config.target_simulation_time
      }
    }
  } catch (error) {
    console.error('Failed to get execution mode:', error)
  }
})

</script>

<style scoped>
.control-panel {
  background-color: #f8f9fa;
  padding: 10px;
  border-right: 1px solid #dee2e6;
  overflow-y: auto;
  transition: width 0.3s ease;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-width: 50px;
  max-width: 350px;
  z-index: 100; /* 스크립트 편집창(5000)보다 낮게 설정 */
  box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}

.toggle-button {
  position: absolute;
  top: 5px;
  right: 5px;
  z-index: 10;
  padding: 3px 6px;
  font-size: 0.8em;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.toggle-button:hover {
  background-color: #0056b3;
}

.panel-content {
  margin-top: 15px;
  flex: 1;
  overflow-y: auto;
}

.panel-content div,
.panel-content h4,
.panel-content label {
  margin-bottom: 8px;
}

.panel-content button {
  display: block;
  width: calc(100% - 10px); 
  margin-bottom: 8px;
}

.panel-content input[type="number"],
.panel-content input[type="text"] {
  width: calc(100% - 20px); 
  margin-bottom: 8px;
}

.reset-button {
    background-color: #ffc107; /* 경고성 노란색 */
    color: black;
}
.reset-button:hover {
    background-color: #e0a800;
}

.refresh-connections-btn {
    background-color: #17a2b8; /* 정보성 청록색 */
    color: white;
}
.refresh-connections-btn:hover {
    background-color: #138496;
}

/* 디버그 섹션 스타일 */
.debug-section {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.debug-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #495057;
}

.debug-status {
  padding: 8px;
  background-color: #e9ecef;
  border-radius: 3px;
  margin-bottom: 10px;
  font-size: 12px;
  min-height: 20px;
  color: #495057;
}

.debug-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.debug-controls button {
  padding: 6px 12px;
  font-size: 14px;
}

.debug-controls button.active {
  background-color: #dc3545;
  color: white;
}

.debug-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.breakpoint-list {
  margin-top: 10px;
  padding: 10px;
  background-color: #fff;
  border-radius: 3px;
  border: 1px solid #dee2e6;
}

.breakpoint-list h5 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #495057;
}

.breakpoint-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.breakpoint-list li {
  padding: 4px 0;
  font-size: 12px;
  color: #6c757d;
}

.continue-btn:enabled {
  background-color: #28a745;
  color: white;
}

.continue-btn:enabled:hover {
  background-color: #218838;
}

.clear-btn {
  background-color: #dc3545;
  color: white;
}

.clear-btn:hover {
  background-color: #c82333;
}

.execution-options {
  margin: 10px 0;
}

.option-group {
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.option-group label {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 120px;
}

.option-input {
  padding: 4px;
  border: 1px solid #ddd;
  border-radius: 3px;
  width: 100px;
}

.option-input:disabled {
  background-color: #f5f5f5;
  color: #999;
}

/* 실행 모드 선택 스타일 */
.execution-mode-selector {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.execution-mode-selector label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.execution-mode-selector select {
  width: 100%;
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 3px;
  font-size: 14px;
}

.execution-mode-selector select:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

/* 시간 스텝 모드 설정 스타일 */
.time-step-config {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #28a745;
  border-radius: 4px;
  background-color: #f8fff9;
}

.time-step-config h5 {
  margin: 0 0 8px 0;
  color: #28a745;
  font-size: 14px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 5px;
}

.config-row label {
  min-width: 60px;
  margin: 0;
  font-size: 13px;
}

.time-input {
  width: 60px;
  padding: 3px 5px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 13px;
}

.save-config-btn {
  padding: 3px 8px;
  font-size: 12px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  margin: 0;
  width: auto;
  display: inline-block;
}

.save-config-btn:hover:not(:disabled) {
  background-color: #218838;
}

.save-config-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

/* 고속 진행 모드 스타일 */
.high-speed-config {
  background-color: #fff5e6;
  border: 1px solid #ffc107;
  border-radius: 5px;
  padding: 12px;
  margin-top: 10px;
}

.high-speed-config h5 {
  margin: 0 0 8px 0;
  color: #ff6600;
  font-size: 14px;
}

.high-speed-config h6 {
  margin: 8px 0 5px 0;
  color: #495057;
  font-size: 13px;
}

.termination-conditions {
  margin-top: 8px;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.condition-row label {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: auto;
  font-size: 13px;
  color: #495057;
}

.condition-input {
  width: 80px;
  padding: 3px 5px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 13px;
}

.condition-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
}

.high-speed-config .help-text {
  color: #6c757d;
  font-size: 11px;
  line-height: 1.3;
  margin-top: 8px;
}

.popup-overlay {
  /* Styles in main.css or App.vue global style */
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000; /* ControlPanel보다 높게 */
}
.popup {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  min-width: 300px; /* 최소 너비 */
}
.popup h4 {
    margin-top: 0;
}
.popup button {
  margin-right: 10px;
  display: inline-block;
  width: auto;
}

.settings-section {
  margin: 15px 0;
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.settings-section h5 {
  margin: 0 0 10px 0;
  color: #333;
  font-weight: bold;
}

.settings-section label {
  display: block;
  margin: 8px 0 4px 0;
  font-weight: normal;
}

.settings-section input {
  width: 100%;
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 3px;
  margin-bottom: 5px;
}

.help-text {
  display: block;
  font-size: 11px;
  color: #666;
  font-style: italic;
  margin-top: 2px;
}

/* .global-signal-manager, .global-signals-list 등 관련 스타일은 GlobalSignalPanel.vue로 이동 */

.control-panel button {
  margin: 5px 0;
  padding: 8px 12px;
  width: 100%;
  border: 1px solid #007bff;
  background-color: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}


.info-text {
  display: block;
  color: #6c757d;
  font-style: italic;
  margin: 3px 0;
  text-align: center;
}
</style> 
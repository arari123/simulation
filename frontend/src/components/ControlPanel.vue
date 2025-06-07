<template>
  <div class="control-panel" :style="{ width: panelWidth }">
    <button @click="togglePanel" class="toggle-button">
      {{ isMinimized ? '최대화' : '최소화' }}
    </button>
    <div v-show="!isMinimized" class="panel-content">
      <h3>제어판</h3>
      <div>배출된 제품: {{ currentDispatchedProducts }} 개</div>
      <div>진행 시간: {{ currentProcessTime.toFixed(1) }} 초</div>
      <div>실행된 스텝 수: {{ currentStepCount }} 회</div>
      
      <button @click="stepExecution">스텝 실행</button>
      <button @click="handleFullExecutionToggle">
        {{ isFullExecutionRunning ? '일시 정지' : '전체 실행 시작' }}
      </button>
      <button @click="previousExecution" title="참고: 실제 이전 단계 기능은 복잡하며 완전히 구현되지 않을 수 있습니다.">이전 실행</button>
      <button @click="resetSimulationDisplayInternal" class="reset-button">시뮬레이션 초기화</button>

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
  isFullExecutionRunning: { type: Boolean, default: false }
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
    'refresh-auto-connections'
])

const inputQuantity = ref(10) // 투입 수량은 로컬에서 관리
const runTimeInput = ref("100s") // 진행 시간 입력은 로컬에서 관리
const executionMode = ref("quantity") // 실행 모드 선택 (quantity 또는 time)

const isMinimized = ref(false)
const panelWidth = computed(() => (isMinimized.value ? '50px' : '300px'))

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
  if (confirm("시뮬레이션 진행 상태를 초기화하시겠습니까? (캔버스 배치는 유지됩니다)")) {
    emit('reset-simulation-display'); // App.vue로 이벤트 전달
  }
}

function previousExecution() {
  emit('previous-step');
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
  console.log("자동 연결 새로고침 실행");
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
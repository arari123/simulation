<template>
  <div class="settings-container">
    <!-- 헤더 섹션 -->
    <div class="settings-header">
      <div class="header-title">
        <h3>{{ title }}</h3>
        <p class="subtitle">{{ subtitle }}</p>
      </div>
      <div class="header-actions">
        <button @click="$emit('close')" class="close-btn">×</button>
      </div>
    </div>

    <!-- 추가 정보 슬롯 -->
    <slot name="extra-info"></slot>

    <!-- 기본 정보 섹션 -->
    <div class="settings-section">
      <h4>기본 정보</h4>
      <div class="form-group">
        <label :for="`${entityType}-name`">{{ entityType === 'block' ? '블록' : '커넥터' }} 이름:</label>
        <div class="name-input-group">
          <input
            :id="`${entityType}-name`"
            v-model="localName"
            type="text"
            :placeholder="`${entityType === 'block' ? '블록' : '커넥터'} 이름 입력`"
            @blur="handleNameChange"
            class="name-input"
          />
          <button 
            @click="handleNameChange" 
            class="apply-name-btn"
            :disabled="!hasNameChanged"
          >
            적용
          </button>
        </div>
        <div v-if="nameValidationError" class="error-message">
          {{ nameValidationError }}
        </div>
      </div>

      <!-- 블록 전용 설정 -->
      <div v-if="entityType === 'block'" class="form-group">
        <label for="max-capacity">최대 용량:</label>
        <input
          id="max-capacity"
          v-model.number="localMaxCapacity"
          type="number"
          min="1"
          @change="handleMaxCapacityChange"
          class="capacity-input"
        />
      </div>

      <!-- 블록 색상 설정 -->
      <div v-if="entityType === 'block'" class="form-group">
        <label>배경 색상:</label>
        <div class="color-input-group">
          <input
            type="color"
            v-model="localBackgroundColor"
            @change="handleBackgroundColorChange"
            class="color-picker"
          />
          <input
            type="text"
            v-model="localBackgroundColor"
            @change="handleBackgroundColorChange"
            placeholder="#FFFFFF"
            class="color-code-input"
          />
          <button 
            @click="resetBackgroundColor" 
            class="reset-color-btn"
            title="기본 색상으로 초기화"
          >
            ↺
          </button>
        </div>
      </div>

      <div v-if="entityType === 'block'" class="form-group">
        <label>텍스트 색상:</label>
        <div class="color-input-group">
          <input
            type="color"
            v-model="localTextColor"
            @change="handleTextColorChange"
            class="color-picker"
          />
          <input
            type="text"
            v-model="localTextColor"
            @change="handleTextColorChange"
            placeholder="#000000"
            class="color-code-input"
          />
          <button 
            @click="resetTextColor" 
            class="reset-color-btn"
            title="기본 색상으로 초기화"
          >
            ↺
          </button>
        </div>
      </div>
    </div>

    <!-- 액션 섹션 -->
    <div class="settings-section">
      <div class="section-header">
        <h4>액션 목록</h4>
        <div class="header-buttons">
          <button 
            @click="openScriptEditor" 
            @click.stop="openScriptEditor"
            @mousedown="openScriptEditor"
            class="script-editor-btn"
            style="position: relative; z-index: 100;"
          >
            📝 스크립트 편집기
          </button>
          <button @click="openActionEditor" class="add-action-btn">+ 액션 추가</button>
          <button v-if="entityType === 'block'" @click="addConnector" class="add-connector-btn">+ 연결점 추가</button>
        </div>
      </div>

      <!-- 액션 목록 표시 -->
      <div class="actions-list">        
        <div 
          v-for="(action, index) in editableActions" 
          :key="`action-${action.id || index}-${action.name || 'unnamed'}-${index}-${editableActions.length}`" 
          class="action-item"
          :class="{ active: editingActionIndex === index, error: action.type === 'script_error' }"
          :data-action-id="action.id"
          :data-action-index="index"
        >
          <div class="action-info">
            <div class="action-header">
              <span class="action-name">{{ action.name }}</span>
              <span class="action-type">{{ getActionTypeLabel(action.type) }}</span>
            </div>
            <div class="action-details">
              {{ formatActionDetails(action) }}
            </div>
          </div>
          <div class="action-controls">
            <button @click="editAction(index)" class="edit-btn">수정</button>
            <button @click="deleteAction(index)" class="delete-btn">삭제</button>
          </div>
        </div>
        
        <div v-if="editableActions.length === 0" class="no-actions">
          액션이 없습니다. + 버튼을 클릭하여 액션을 추가하세요.
        </div>
      </div>
    </div>


    <!-- 스크립트 미리보기 섹션 -->
    <div class="settings-section">
      <h4>스크립트 미리보기</h4>
      <div class="script-preview">
        <pre class="script-content">{{ generatedScript }}</pre>
      </div>
    </div>

    <!-- 스크립트 편집기 (분리된 컴포넌트) -->
    <ScriptEditor
      ref="scriptEditorRef"
      :show="showScriptEditor"
      :script-content="scriptContent"
      :action-count="editableActions.length"
      :all-signals="allSignals"
      :all-blocks="allBlocks"
      :current-block="currentBlock"
      :entity-type="entityType"
      :breakpoints="currentBreakpoints"
      @close="closeScriptEditor"
      @apply="handleScriptApply"
      @breakpointChange="handleBreakpointChange"
    />

    <!-- 액션 편집기 (모달) -->
    <div v-if="showActionEditor" class="action-editor-overlay" @click="closeActionEditor">
      <div class="action-editor" @click.stop>
        <ActionEditor
          :action="currentEditAction"
          :action-index="editingActionIndex"
          :available-actions="editableActions"
          :all-signals="allSignals"
          :all-blocks="allBlocks"
          :current-block="currentBlock"
          @save="handleActionSave"
          @cancel="closeActionEditor"
        />
      </div>
    </div>

    <!-- 푸터 액션 -->
    <div class="settings-footer">
      <div class="footer-left">
        <button 
          v-if="entityType === 'connector'" 
          @click="handleDeleteConnector" 
          class="delete-connector-btn"
        >
          🗑️ 커넥터 삭제
        </button>
        <button 
          v-if="entityType === 'block'" 
          @click="handleDeleteBlock" 
          class="delete-block-btn"
        >
          🗑️ 블록 삭제
        </button>
      </div>
      <div class="footer-right">
        <button @click="handleSave" class="save-btn">저장</button>
        <button @click="$emit('close')" class="cancel-btn">닫기</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import ActionEditor from './ActionEditor.vue'
// 스크립트 편집기 버전 선택
const USE_NEW_SCRIPT_EDITOR = true // 환경 변수나 설정으로 변경 가능

import ScriptEditorLegacy from './ScriptEditorLegacy.vue'
import ScriptEditorV2 from '../script/ScriptEditorV2.vue'

const ScriptEditor = USE_NEW_SCRIPT_EDITOR ? ScriptEditorV2 : ScriptEditorLegacy
import { convertActionToScript } from '../../utils/BlockManager.js'

// Props 정의
const props = defineProps({
  entityType: { type: String, required: true }, // 'block' 또는 'connector'
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  initialName: { type: String, required: true },
  initialActions: { type: Array, default: () => [] },
  initialMaxCapacity: { type: Number, default: 1 },
  initialConnectors: { type: Array, default: () => [] }, // 커넥터 목록
  initialBackgroundColor: { type: String, default: '#cfdff7' },
  initialTextColor: { type: String, default: '#000000' },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  currentBlock: { type: Object, default: null },
  validateName: { type: Function, required: true },
  onNameChange: { type: Function, default: null },
  onMaxCapacityChange: { type: Function, default: null },
  breakpoints: { type: Array, default: () => [] }
})

// Emits 정의
const emit = defineEmits(['close', 'save', 'nameChange', 'maxCapacityChange', 'backgroundColorChange', 'textColorChange', 'connectorAdd', 'deleteConnector', 'deleteBlock', 'breakpointChange'])

// 상태 관리
const localName = ref(props.initialName)
const localMaxCapacity = ref(props.initialMaxCapacity)
const localBackgroundColor = ref(props.initialBackgroundColor)
const localTextColor = ref(props.initialTextColor)
const editableActions = ref([])
const showActionEditor = ref(false)
const showScriptEditor = ref(false)
const scriptContent = ref('')
const editingActionIndex = ref(-1)
const currentEditAction = ref(null)
const nameValidationError = ref('')
const currentBreakpoints = ref([])
const scriptEditorRef = ref(null)

// 계산된 속성
const hasNameChanged = computed(() => {
  return localName.value !== props.initialName && localName.value.trim() !== ''
})

const generatedScript = computed(() => {
  if (editableActions.value.length === 0) {
    return '// 액션이 없습니다'
  }
  
  // script 타입 액션이 있으면 그 스크립트를 우선 반환
  const scriptAction = editableActions.value.find(action => action.type === 'script')
  if (scriptAction && scriptAction.parameters?.script) {
    return scriptAction.parameters.script
  }
  
  const context = {
    allBlocks: props.allBlocks,
    currentBlock: props.currentBlock,
    currentBlockName: props.currentBlock?.name,
    editableActions: editableActions.value
  }
  
  return editableActions.value
    .map(action => convertActionToScript(action, context))
    .join('\n')
})

// 메서드
function handleNameChange() {
  const validation = props.validateName(localName.value)
  if (!validation.valid) {
    nameValidationError.value = validation.error
    return
  }
  
  nameValidationError.value = ''
  if (props.onNameChange) {
    props.onNameChange(localName.value)
  }
  emit('nameChange', localName.value)
}

function handleMaxCapacityChange() {
  if (props.onMaxCapacityChange) {
    props.onMaxCapacityChange(localMaxCapacity.value)
  }
  emit('maxCapacityChange', localMaxCapacity.value)
}

function handleBackgroundColorChange() {
  emit('backgroundColorChange', localBackgroundColor.value)
}

function handleTextColorChange() {
  emit('textColorChange', localTextColor.value)
}

function resetBackgroundColor() {
  localBackgroundColor.value = '#cfdff7'
  handleBackgroundColorChange()
}

function resetTextColor() {
  localTextColor.value = '#000000'
  handleTextColorChange()
}

function openActionEditor() {
  currentEditAction.value = {
    id: `new-${Date.now()}`,
    name: '',
    type: 'delay',
    parameters: {}
  }
  editingActionIndex.value = -1
  showActionEditor.value = true
}

function editAction(index) {
  const action = editableActions.value[index]
  currentEditAction.value = JSON.parse(JSON.stringify(action))
  editingActionIndex.value = index
  showActionEditor.value = true
}

function deleteAction(index) {
  if (confirm('이 액션을 삭제하시겠습니까?')) {
    editableActions.value.splice(index, 1)
  }
}

function closeActionEditor() {
  showActionEditor.value = false
  editingActionIndex.value = -1
  currentEditAction.value = null
}

function handleActionSave(actionData) {
  if (editingActionIndex.value >= 0) {
    // 기존 액션 수정 - 새 배열을 생성하여 반응성 보장
    const newActions = [...editableActions.value]
    newActions[editingActionIndex.value] = actionData
    editableActions.value = newActions
  } else {
    // 새 액션 추가 - 새 배열을 생성하여 반응성 보장
    editableActions.value = [...editableActions.value, actionData]
  }
  
  // 액션 편집기 닫기 (기존 액션 수정이든 새 액션 추가든 상관없이)
  closeActionEditor()
  
  // 액션 변경 후 자동 저장
  handleSave()
}

function getActionTypeLabel(type) {
  const typeLabels = {
    'delay': '딜레이',
    'signal_wait': '신호 대기',
    'signal_update': '신호 변경',
    'signal_check': '신호 확인',
    'route_to_connector': '연결점 이동',
    'conditional_branch': '조건부 실행',
    'action_jump': '액션 점프',
    'custom_sink': '커스텀 싱크',
    'script_error': '스크립트 오류',
    'script': '스크립트'
  }
  return typeLabels[type] || type
}

function formatActionDetails(action) {
  switch (action.type) {
    case 'delay':
      return `${action.parameters?.duration || 0}초 대기`
    case 'signal_wait':
      return `${action.parameters?.signal_name} = ${action.parameters?.expected_value} 대기`
    case 'signal_update':
      return `${action.parameters?.signal_name} = ${action.parameters?.value} 설정`
    case 'route_to_connector':
      if (action.parameters?.target_block_id) {
        const targetBlock = props.allBlocks.find(b => b.id == action.parameters.target_block_id)
        const blockName = targetBlock?.name || `블록${action.parameters.target_block_id}`
        return `${blockName}으로 이동`
      }
      return '이동 액션'
    case 'conditional_branch':
      return '조건부 실행'
    case 'script_error':
      return `오류: ${action.parameters?.error || '알 수 없는 오류'}`
    case 'script':
      const scriptLines = action.parameters?.script?.split('\n') || []
      const firstLine = scriptLines[0]?.trim() || ''
      return scriptLines.length > 1 ? `${firstLine}... (${scriptLines.length}줄)` : firstLine || '빈 스크립트'
    default:
      return action.type
  }
}

function handleSave() {
  const saveData = {
    name: localName.value,
    actions: editableActions.value,
    maxCapacity: localMaxCapacity.value
  }
  
  // 블록인 경우 색상 정보도 추가
  if (props.entityType === 'block') {
    saveData.backgroundColor = localBackgroundColor.value
    saveData.textColor = localTextColor.value
  }
  
  emit('save', saveData)
}

function openScriptEditor() {
  // 강제로 상태 업데이트
  showActionEditor.value = false  // 다른 편집기 닫기
  
  // script 타입 액션이 있으면 그 스크립트와 브레이크포인트를 우선 표시
  const scriptAction = editableActions.value.find(action => action.type === 'script')
  if (scriptAction && scriptAction.parameters?.script) {
    scriptContent.value = scriptAction.parameters.script
    // 브레이크포인트 정보도 복원
    currentBreakpoints.value = scriptAction.parameters?.breakpoints || []
  } else {
    // 현재 액션들을 스크립트로 변환하여 편집기에 표시
    scriptContent.value = generatedScript.value
    currentBreakpoints.value = []
  }
  
  // DOM 업데이트 후 스크립트 편집기 열기
  nextTick(() => {
    showScriptEditor.value = true
  })
}

function closeScriptEditor() {
  showScriptEditor.value = false
  scriptContent.value = ''
}

function handleScriptApply(parsedActions, scriptText, breakpoints) {
  // 스크립트 편집기에서 가져온 스크립트 내용을 사용하여 script 타입 액션 생성
  const scriptAction = {
    id: `script-${Date.now()}`,
    name: '스크립트',
    type: 'script',
    parameters: {
      script: scriptText,
      breakpoints: breakpoints || [] // 브레이크포인트 정보 저장
    }
  }
  
  // 모든 액션을 script 타입 액션 하나로 교체
  editableActions.value = [scriptAction]
  
  // 스크립트 적용 후 자동 저장
  handleSave()
  
  closeScriptEditor()
}

// 브레이크포인트 변경 핸들러
function handleBreakpointChange(blockId, lineNumber, isOn) {
  emit('breakpointChange', blockId, lineNumber, isOn)
}

// 커넥터 관리 함수들
function addConnector() {
  const connectorName = prompt('연결점 이름을 입력하세요:', `연결점${(props.initialConnectors?.length || 0) + 1}`)
  
  if (!connectorName || !connectorName.trim()) {
    return // 취소하거나 빈 이름인 경우
  }
  
  // 중복 이름 체크
  const isDuplicate = props.initialConnectors?.some(conn => conn.name === connectorName.trim())
  if (isDuplicate) {
    alert('같은 이름의 연결점이 이미 있습니다.')
    return
  }
  
  const newConnector = {
    id: `connector-${Date.now()}`,
    name: connectorName.trim(),
    x: 50, // 기본 위치
    y: 50
  }
  
  emit('connectorAdd', newConnector)
}

function handleDeleteConnector() {
  const confirmMessage = `"${localName.value}" 커넥터를 정말 삭제하시겠습니까?\n\n삭제하면 다음 항목들이 함께 제거됩니다:\n- 이 커넥터의 모든 액션\n- 이 커넥터와 연결된 모든 연결선\n\n이 작업은 되돌릴 수 없습니다.`
  
  if (confirm(confirmMessage)) {
    emit('deleteConnector')
  }
}

function handleDeleteBlock() {
  const confirmMessage = `"${localName.value}" 블록을 정말 삭제하시겠습니까?\n\n삭제하면 다음 항목들이 함께 제거됩니다:\n- 이 블록의 모든 액션과 커넥터\n- 이 블록과 연결된 모든 연결선\n- 다른 블록에서 이 블록을 참조하는 스크립트에 오류가 발생할 수 있습니다\n\n이 작업은 되돌릴 수 없습니다.`
  
  if (confirm(confirmMessage)) {
    emit('deleteBlock')
  }
}


// 초기화
onMounted(() => {
  editableActions.value = JSON.parse(JSON.stringify(props.initialActions || []))
})

// Props 변경 감지
watch(() => props.initialActions, (newActions) => {
  editableActions.value = JSON.parse(JSON.stringify(newActions || []))
}, { deep: true })

watch(() => props.initialName, (newName) => {
  localName.value = newName
})

watch(() => props.initialMaxCapacity, (newCapacity) => {
  localMaxCapacity.value = newCapacity
})

// 브레이크포인트 prop 변경 감지
watch(() => props.breakpoints, (newBreakpoints) => {
  currentBreakpoints.value = [...newBreakpoints]
  
  // 브레이크포인트가 모두 제거된 경우 스크립트 편집기에서도 강제로 클리어
  if ((!newBreakpoints || newBreakpoints.length === 0) && scriptEditorRef.value && showScriptEditor.value) {
    nextTick(() => {
      scriptEditorRef.value.forceClearBreakpoints?.()
    })
  }
}, { deep: true, immediate: true })
</script>

<style scoped>
.settings-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.header-title h3 {
  margin: 0;
  color: #343a40;
}

.subtitle {
  margin: 4px 0 0 0;
  color: #6c757d;
  font-size: 14px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #dc3545;
}

.settings-section {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
}

.settings-section h4 {
  margin: 0 0 15px 0;
  color: #495057;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #495057;
  font-weight: 500;
}

.name-input-group {
  display: flex;
  gap: 10px;
}

.name-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
}

.apply-name-btn {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.apply-name-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.capacity-input {
  width: 100px;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
}

.error-message {
  color: #dc3545;
  font-size: 12px;
  margin-top: 5px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.script-editor-btn {
  padding: 6px 12px;
  background: #6f42c1;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.script-editor-btn:hover {
  background: #5a2d91;
}

.add-action-btn {
  padding: 6px 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.add-action-btn:hover {
  background: #218838;
}

.actions-list {
  max-height: 300px;
  overflow-y: auto;
}

.action-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  margin-bottom: 8px;
  background: #f8f9fa;
}

.action-item.active {
  border-color: #007bff;
  background: #e3f2fd;
}

.action-item.error {
  border-color: #dc3545;
  background: #fff5f5;
}

.action-item.error .action-name {
  color: #dc3545;
}

.action-item.error .action-type {
  background: #dc3545;
  color: white;
}

.action-info {
  flex: 1;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.action-name {
  font-weight: 500;
  color: #343a40;
}

.action-type {
  background: #e9ecef;
  color: #495057;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.action-details {
  color: #6c757d;
  font-size: 12px;
}

.action-controls {
  display: flex;
  gap: 8px;
}

.edit-btn, .delete-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.edit-btn {
  background: #ffc107;
  color: #212529;
}

.delete-btn {
  background: #dc3545;
  color: white;
}

.no-actions {
  text-align: center;
  color: #6c757d;
  padding: 40px 20px;
  font-style: italic;
}

/* 연결점 추가 버튼 스타일 */
.add-connector-btn {
  background: #17a2b8;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.2s;
}

.add-connector-btn:hover {
  background: #138496;
}

.script-preview {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 16px;
  max-height: 200px;
  overflow-y: auto;
}

.script-content {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #495057;
  white-space: pre-wrap;
}

.action-editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.action-editor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.settings-footer {
  padding: 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.footer-left {
  display: flex;
  gap: 10px;
}

.footer-right {
  display: flex;
  gap: 10px;
}

.save-btn {
  padding: 8px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.cancel-btn {
  padding: 8px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.delete-connector-btn, .delete-block-btn {
  padding: 8px 16px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.delete-connector-btn:hover, .delete-block-btn:hover {
  background: #c82333;
}

/* 색상 설정 스타일 */
.color-input-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-picker {
  width: 50px;
  height: 35px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px;
}

.color-code-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
}

.reset-color-btn {
  padding: 6px 12px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.2s;
}

.reset-color-btn:hover {
  background: #5a6268;
}
</style> 
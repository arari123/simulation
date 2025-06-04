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
      :show="showScriptEditor"
      :script-content="scriptContent"
      :action-count="editableActions.length"
      :all-signals="allSignals"
      :all-blocks="allBlocks"
      :current-block="currentBlock"
      :entity-type="entityType"
      @close="closeScriptEditor"
      @apply="handleScriptApply"
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
      <button @click="handleSave" class="save-btn">저장</button>
      <button @click="$emit('close')" class="cancel-btn">닫기</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import ActionEditor from './ActionEditor.vue'
import ScriptEditor from './ScriptEditor.vue'
import { convertActionToScript } from '../../utils/BlockManager.js'

// Props 정의
const props = defineProps({
  entityType: { type: String, required: true }, // 'block' 또는 'connector'
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  initialName: { type: String, required: true },
  initialActions: { type: Array, default: () => [] },
  initialMaxCapacity: { type: Number, default: 1 },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  currentBlock: { type: Object, default: null },
  validateName: { type: Function, required: true },
  onNameChange: { type: Function, default: null },
  onMaxCapacityChange: { type: Function, default: null }
})

// Emits 정의
const emit = defineEmits(['close', 'save', 'nameChange', 'maxCapacityChange'])

// 상태 관리
const localName = ref(props.initialName)
const localMaxCapacity = ref(props.initialMaxCapacity)
const editableActions = ref([])
const showActionEditor = ref(false)
const showScriptEditor = ref(false)
const scriptContent = ref('')
const editingActionIndex = ref(-1)
const currentEditAction = ref(null)
const nameValidationError = ref('')

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
  emit('save', {
    name: localName.value,
    actions: editableActions.value,
    maxCapacity: localMaxCapacity.value
  })
}

function openScriptEditor() {
  // 강제로 상태 업데이트
  showActionEditor.value = false  // 다른 편집기 닫기
  
  // script 타입 액션이 있으면 그 스크립트를 우선 표시
  const scriptAction = editableActions.value.find(action => action.type === 'script')
  if (scriptAction && scriptAction.parameters?.script) {
    scriptContent.value = scriptAction.parameters.script
  } else {
    // 현재 액션들을 스크립트로 변환하여 편집기에 표시
    scriptContent.value = generatedScript.value
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

function handleScriptApply(parsedActions, scriptText) {
  // 스크립트 편집기에서 가져온 스크립트 내용을 사용하여 script 타입 액션 생성
  const scriptAction = {
    id: `script-${Date.now()}`,
    name: '스크립트',
    type: 'script',
    parameters: {
      script: scriptText
    }
  }
  
  // 모든 액션을 script 타입 액션 하나로 교체
  editableActions.value = [scriptAction]
  
  // 스크립트 적용 후 자동 저장
  handleSave()
  
  closeScriptEditor()
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
  justify-content: flex-end;
  gap: 10px;
  margin-top: auto;
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
</style> 
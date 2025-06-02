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
          <button @click="openScriptEditor" class="script-editor-btn">📝 스크립트 편집기</button>
          <button @click="openActionEditor" class="add-action-btn">+ 액션 추가</button>
        </div>
      </div>

      <!-- 액션 목록 표시 -->
      <ActionList 
        :actions="editableActions"
        :editing-action-index="editingActionIndex"
        @edit-action="editAction"
        @delete-action="deleteAction"
      />
    </div>

    <!-- 스크립트 미리보기 섹션 -->
    <ScriptPreview :script="generatedScript" />

    <!-- 스크립트 편집기 (모달) -->
    <ScriptEditor
      v-if="showScriptEditor"
      :script-content="scriptContent"
      :real-time-errors="realTimeErrors"
      :line-count="lineCount"
      @close="closeScriptEditor"
      @apply="applyScript"
      @script-input="onScriptInput"
      @composition-start="onCompositionStart"
      @composition-end="onCompositionEnd"
      @sync-scroll="syncScroll"
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
import { ref, computed, watch, onMounted } from 'vue'
import ActionEditor from './ActionEditor.vue'
import ActionList from '../validation/ActionList.vue'
import ScriptPreview from '../script/ScriptPreview.vue'
import ScriptEditor from '../script/ScriptEditor.vue'
import { convertActionToScript } from '../../utils/BlockManager.js'
import { validateScript, parseScriptToActions } from '../script/ScriptValidator.js'

// Props 정의
const props = defineProps({
  entityType: { type: String, required: true },
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
const realTimeErrors = ref([])
const isComposing = ref(false)

// 계산된 속성
const hasNameChanged = computed(() => {
  return localName.value !== props.initialName && localName.value.trim() !== ''
})

const lineCount = computed(() => {
  return Math.max(12, scriptContent.value.split('\n').length)
})

const generatedScript = computed(() => {
  if (editableActions.value.length === 0) {
    return '// 액션이 없습니다'
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
    editableActions.value[editingActionIndex.value] = actionData
  } else {
    editableActions.value.push(actionData)
  }
  
  closeActionEditor()
  handleSave()
}

function handleSave() {
  emit('save', {
    name: localName.value,
    actions: editableActions.value,
    maxCapacity: localMaxCapacity.value
  })
}

function openScriptEditor() {
  scriptContent.value = generatedScript.value
  showScriptEditor.value = true
}

function closeScriptEditor() {
  showScriptEditor.value = false
  scriptContent.value = ''
}

function applyScript() {
  try {
    // 스크립트 유효성 검사
    const validationResult = validateScript(scriptContent.value, props)
    if (!validationResult.valid) {
      alert('스크립트 오류:\n' + validationResult.errors.join('\n'))
      return
    }
    
    // 스크립트를 파싱하여 액션으로 변환
    const parsedActions = parseScriptToActions(scriptContent.value, props)
    editableActions.value = parsedActions
    
    handleSave()
    closeScriptEditor()
  } catch (error) {
    alert('스크립트 파싱 오류: ' + error.message)
  }
}

function onScriptInput() {
  if (isComposing.value) return
  
  // 실시간 문법 검사
  const validation = validateScript(scriptContent.value, props)
  realTimeErrors.value = validation.errors.map(error => {
    const lineMatch = error.match(/라인 (\d+):/)
    const line = lineMatch ? parseInt(lineMatch[1]) : 1
    return {
      line: line,
      message: error.replace(/라인 \d+: /, '')
    }
  })
}

function onCompositionStart() {
  isComposing.value = true
}

function onCompositionEnd() {
  isComposing.value = false
  onScriptInput()
}

function syncScroll() {
  // 스크롤 동기화 로직은 ScriptEditor 컴포넌트에서 처리
}

// 초기화
onMounted(() => {
  editableActions.value = JSON.parse(JSON.stringify(props.initialActions))
})

// Props 변경 감지
watch(() => props.initialActions, (newActions) => {
  editableActions.value = JSON.parse(JSON.stringify(newActions))
}, { deep: true })

watch(() => props.initialName, (newName) => {
  localName.value = newName
})

watch(() => props.initialMaxCapacity, (newCapacity) => {
  localMaxCapacity.value = newCapacity
})

watch(scriptContent, () => {
  onScriptInput()
}, { immediate: true })
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
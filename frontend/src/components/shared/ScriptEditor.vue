<template>
  <div v-if="show" class="script-editor-overlay" @click="closeEditor">
    <div class="script-editor" @click.stop>
      <div class="script-editor-header">
        <h3>📝 스크립트 편집기</h3>
        <!-- 디버깅 정보 -->
        <div style="font-size: 12px; color: #666;">
          상태: {{ show ? '열림' : '닫힘' }} | 액션 개수: {{ actionCount }}
        </div>
        <button @click="closeEditor" class="close-btn">×</button>
      </div>
      
      <div class="script-editor-content">
        <div class="script-editor-controls">
          <button @click="showHelp = true" class="help-btn">❓ 사용법</button>
        </div>
        
        <div class="script-input-section">
          <label for="script-input">스크립트:</label>
          <div class="script-editor-wrapper">
            <div class="line-numbers" ref="lineNumbers">
              <div v-for="n in lineCount" :key="n" class="line-number">{{ n }}</div>
            </div>
            <div class="script-input-container">
              <textarea
                id="script-input"
                ref="scriptTextarea"
                v-model="localScriptContent"
                rows="12"
                placeholder="스크립트를 입력하세요..."
                class="script-textarea"
                @scroll="syncScroll"
                @input="onScriptInput"
                @compositionstart="onCompositionStart"
                @compositionend="onCompositionEnd"
              ></textarea>
              <div class="syntax-errors" ref="syntaxErrors">
                <div 
                  v-for="error in realTimeErrors" 
                  :key="error.line"
                  class="error-line"
                  :style="{ top: `${(error.line - 1) * 1.5}em` }"
                >
                  <div class="error-underline" :title="error.message"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="script-editor-actions">
          <button @click="applyScript" class="apply-btn">적용</button>
          <button @click="closeEditor" class="cancel-btn">취소</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 스크립트 사용법 팝업 -->
  <ScriptHelp v-if="showHelp" @close="showHelp = false" />
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import ScriptHelp from './ScriptHelp.vue'
import { validateScript, parseScriptToActions } from '../../utils/ScriptUtils.js'

// Props 정의
const props = defineProps({
  show: { type: Boolean, default: false },
  scriptContent: { type: String, default: '' },
  actionCount: { type: Number, default: 0 },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  currentBlock: { type: Object, default: null },
  entityType: { type: String, required: true }
})

// Emits 정의
const emit = defineEmits(['close', 'apply'])

// 상태 관리
const localScriptContent = ref('')
const showHelp = ref(false)
const realTimeErrors = ref([])
const lineNumbers = ref(null)
const scriptTextarea = ref(null)
const isComposing = ref(false)

// 계산된 속성
const lineCount = computed(() => {
  return Math.max(12, localScriptContent.value.split('\n').length)
})

// 메서드
function closeEditor() {
  emit('close')
}

function applyScript() {
  try {
    console.log('[ScriptEditor] applyScript 호출됨', {
      scriptContent: localScriptContent.value
    })
    
    // 스크립트 유효성 검사
    const validationResult = validateScript(
      localScriptContent.value,
      props.allSignals,
      props.allBlocks,
      props.currentBlock,
      props.entityType
    )
    
    if (!validationResult.valid) {
      alert('스크립트 오류:\n' + validationResult.errors.join('\n'))
      return
    }
    
    // 스크립트를 파싱하여 액션으로 변환
    const parsedActions = parseScriptToActions(
      localScriptContent.value,
      props.allBlocks,
      props.currentBlock,
      props.entityType
    )
    
    console.log('[ScriptEditor] 파싱된 액션들:', parsedActions)
    
    emit('apply', parsedActions)
  } catch (error) {
    console.error('[ScriptEditor] 스크립트 파싱 오류:', error)
    alert('스크립트 파싱 오류: ' + error.message)
  }
}

function syncScroll() {
  if (lineNumbers.value && scriptTextarea.value) {
    lineNumbers.value.scrollTop = scriptTextarea.value.scrollTop
  }
}

function onScriptInput() {
  // 한글 입력 중일 때는 실시간 검증을 건너뛰기
  if (isComposing.value) {
    return
  }
  
  // 실시간 문법 검사
  const validation = validateScript(
    localScriptContent.value,
    props.allSignals,
    props.allBlocks,
    props.currentBlock,
    props.entityType
  )
  
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
  // 한글 입력이 끝났을 때 실시간 검증 실행
  onScriptInput()
}

// Props 변경 감지
watch(() => props.scriptContent, (newContent) => {
  localScriptContent.value = newContent
}, { immediate: true })

watch(() => props.show, (newShow) => {
  if (newShow) {
    nextTick(() => {
      onScriptInput()
    })
  }
})
</script>

<style scoped>
.script-editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.script-editor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.script-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
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

.script-editor-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.script-editor-controls {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px;
}

.script-editor-controls button {
  padding: 8px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.script-editor-controls .help-btn {
  background: #6f42c1;
}

.script-input-section {
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
}

.script-input-section label {
  display: block;
  margin-bottom: 5px;
  color: #495057;
  font-weight: 500;
}

.script-editor-wrapper {
  position: relative;
  display: flex;
  border: 1px solid #ced4da;
  border-radius: 4px;
  overflow: hidden;
}

.line-numbers {
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
  padding: 8px 12px 8px 8px;
  color: #6c757d;
  font-size: 14px;
  font-family: 'Courier New', monospace;
  text-align: right;
  min-width: 50px;
  user-select: none;
  overflow: hidden;
}

.line-number {
  height: 1.5em;
  line-height: 1.5em;
}

.script-input-container {
  position: relative;
  flex: 1;
}

.script-textarea {
  width: 100%;
  padding: 8px;
  border: none;
  font-size: 14px;
  font-family: 'Courier New', monospace;
  line-height: 1.5em;
  resize: none;
  outline: none;
  background: transparent;
  color: #495057;
  caret-color: #007bff;
  cursor: text;
  z-index: 1;
  position: relative;
}

.syntax-errors {
  position: absolute;
  left: 8px;
  top: 8px;
  right: 8px;
  bottom: 8px;
  pointer-events: none;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5em;
}

.error-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1.5em;
  pointer-events: none;
}

.error-underline {
  position: absolute;
  bottom: 2px;
  left: 0;
  right: 0;
  height: 2px;
  background: red;
  border-radius: 1px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.script-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px;
}

.script-editor-actions button {
  padding: 8px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.script-editor-actions .apply-btn {
  background: #28a745;
}

.script-editor-actions .cancel-btn {
  background: #6c757d;
}
</style> 
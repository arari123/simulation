<template>
  <div>
    <div 
      class="info-text-panel" 
      :class="{ expanded: isExpanded }"
      :style="panelStyle"
    >
      <div class="text-content" @click="toggleExpand">
        <div v-if="!isExpanded" class="minimized-text">
          <span v-html="getFirstLineHtml()"></span>
        </div>
        <div 
          v-else 
          class="expanded-text"
          contenteditable="false"
          ref="textContentRef"
          v-html="formattedContent"
        >
        </div>
      </div>
      <button class="edit-button" @click.stop="openEditDialog" title="텍스트 편집">
        ✏️
      </button>
    </div>
    
    <!-- 편집 다이얼로그 - info-text-panel 밖에 위치 -->
    <teleport to="body">
      <div v-if="showEditDialog" class="edit-dialog-overlay" @click="closeEditDialog">
      <div class="edit-dialog" @click.stop>
        <h3>정보 텍스트 편집</h3>
        
        <div class="form-group">
          <label>텍스트 내용</label>
          <div class="editor-toolbar">
            <button 
              class="toolbar-btn"
              :class="{ active: selectedStyle.bold }"
              @click="toggleBold"
              title="굵게"
            >
              <strong>B</strong>
            </button>
            <div class="toolbar-separator"></div>
            <input 
              type="color" 
              v-model="selectedStyle.color"
              @change="applyColor"
              title="글자 색상"
              class="color-picker"
            >
            <div class="toolbar-separator"></div>
            <select 
              v-model="selectedStyle.fontSize"
              @change="applyFontSize"
              class="font-size-select"
            >
              <option v-for="size in fontSizes" :key="size" :value="size">
                {{ size }}px
              </option>
            </select>
          </div>
          <div 
            ref="editorRef"
            class="rich-text-editor"
            contenteditable="true"
            @compositionstart="isComposing = true"
            @compositionend="handleCompositionEnd"
            @input="handleInput"
            @mouseup="updateSelection"
            @keyup="updateSelection"
          ></div>
        </div>
        
        <div class="dialog-actions">
          <button class="save-btn" @click="saveChanges">저장</button>
          <button class="cancel-btn" @click="closeEditDialog">취소</button>
        </div>
      </div>
    </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  infoText: {
    type: Object,
    required: true
  },
  controlPanelWidth: {
    type: Number,
    default: 300
  },
  showBlockSettings: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:infoText'])

// 상태
const isExpanded = ref(false)
const showEditDialog = ref(false)
const localContent = ref('')
const formattedContent = ref('')
const textContentRef = ref(null)
const editorRef = ref(null)
const isComposing = ref(false)
const selectedStyle = ref({
  bold: false,
  color: '#000000',
  fontSize: 16
})

// 폰트 크기 옵션
const fontSizes = [12, 14, 16, 18, 20, 22, 24]

// 계산된 속성
const panelStyle = computed(() => {
  const baseLeft = props.controlPanelWidth + 22 // 20px 추가 여백으로 증가
  return {
    left: `${baseLeft}px`,
    width: `calc(100% - ${baseLeft}px)`
  }
})

// 첫 줄 HTML 추출
function getFirstLineHtml() {
  if (!formattedContent.value) return '정보 텍스트를 입력하세요'
  
  // 임시 div에서 첫 줄 추출
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = formattedContent.value
  const text = tempDiv.textContent || tempDiv.innerText
  const firstLine = text.split('\n')[0]
  
  // 첫 줄의 HTML 반환
  if (firstLine.length > 50) {
    return firstLine.substring(0, 50) + '...'
  }
  return firstLine
}

// 메서드
function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function openEditDialog() {
  localContent.value = formattedContent.value || '<p>시뮬레이션 정보를 입력하세요...</p>'
  showEditDialog.value = true
  
  // 에디터 내용 설정 및 포커스
  nextTick(() => {
    if (editorRef.value) {
      editorRef.value.innerHTML = localContent.value
      editorRef.value.focus()
    }
  })
}

function closeEditDialog() {
  showEditDialog.value = false
}

function handleInput(event) {
  // 한글 입력 중일 때는 처리하지 않음
  if (isComposing.value) return
  
  localContent.value = event.target.innerHTML
}

function handleCompositionEnd(event) {
  isComposing.value = false
  // 한글 입력이 완료되면 내용 업데이트
  localContent.value = event.target.innerHTML
}

function updateSelection() {
  const selection = window.getSelection()
  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0)
    const container = range.commonAncestorContainer
    const element = container.nodeType === 3 ? container.parentElement : container
    
    // 현재 선택 영역의 스타일 확인
    selectedStyle.value.bold = document.queryCommandState('bold')
    
    // 색상 확인
    const color = window.getComputedStyle(element).color
    selectedStyle.value.color = rgbToHex(color)
    
    // 폰트 크기 확인
    const fontSize = window.getComputedStyle(element).fontSize
    selectedStyle.value.fontSize = parseInt(fontSize)
  }
}

function toggleBold() {
  document.execCommand('bold', false, null)
  selectedStyle.value.bold = !selectedStyle.value.bold
}

function applyColor() {
  document.execCommand('foreColor', false, selectedStyle.value.color)
}

function applyFontSize() {
  const selection = window.getSelection()
  if (selection.rangeCount > 0 && !selection.isCollapsed) {
    // 선택한 텍스트가 있을 때만 처리
    const fontSize = selectedStyle.value.fontSize
    
    // 폰트 크기에 따라 적절한 font 태그 사이즈 매핑
    let fontSizeValue = 3 // 기본값
    if (fontSize <= 12) fontSizeValue = 1
    else if (fontSize <= 14) fontSizeValue = 2
    else if (fontSize <= 16) fontSizeValue = 3
    else if (fontSize <= 18) fontSizeValue = 4
    else if (fontSize <= 20) fontSizeValue = 5
    else if (fontSize <= 22) fontSizeValue = 6
    else fontSizeValue = 7
    
    // execCommand 사용
    document.execCommand('fontSize', false, fontSizeValue)
    
    // 생성된 font 태그를 span으로 변환하고 정확한 크기 적용
    const fontElements = editorRef.value.getElementsByTagName('font')
    for (let i = fontElements.length - 1; i >= 0; i--) {
      const font = fontElements[i]
      if (font.size == fontSizeValue) {
        const span = document.createElement('span')
        span.style.fontSize = `${fontSize}px`
        span.innerHTML = font.innerHTML
        font.parentNode.replaceChild(span, font)
      }
    }
  }
}

function rgbToHex(rgb) {
  if (rgb.startsWith('#')) return rgb
  
  const values = rgb.match(/\d+/g)
  if (!values || values.length < 3) return '#000000'
  
  const r = parseInt(values[0]).toString(16).padStart(2, '0')
  const g = parseInt(values[1]).toString(16).padStart(2, '0')
  const b = parseInt(values[2]).toString(16).padStart(2, '0')
  
  return `#${r}${g}${b}`
}

function saveChanges() {
  formattedContent.value = localContent.value
  emit('update:infoText', {
    content: localContent.value,
    isExpanded: isExpanded.value
  })
  closeEditDialog()
}

// 초기화
watch(() => props.infoText, (newVal) => {
  if (newVal && newVal.content) {
    formattedContent.value = newVal.content
  }
}, { immediate: true })

// ESC 키로 다이얼로그 닫기
watch(showEditDialog, (newVal) => {
  if (newVal) {
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        closeEditDialog()
      }
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }
})
</script>

<style scoped>
.info-text-panel {
  position: fixed;
  top: 0;
  background: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid #ddd;
  transition: all 0.3s ease;
  z-index: 100;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.info-text-panel.expanded {
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  z-index: 100; /* 확장 시에도 동일한 z-index 유지 */
}

.text-content {
  flex: 1;
  cursor: pointer;
  user-select: none;
}

.minimized-text {
  padding: 8px 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.minimized-text :deep(*) {
  display: inline;
}

.expanded-text {
  padding: 16px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.edit-button {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
}

.edit-button:hover {
  background: #f0f0f0;
  border-color: #999;
}

/* 편집 다이얼로그 */
.edit-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center; /* 중앙 정렬로 복원 */
  justify-content: center;
  z-index: 2000; /* info-text-panel보다 높은 z-index */
  padding: 0;
  overflow-y: auto;
}

.edit-dialog {
  background: white;
  border-radius: 8px;
  padding: 24px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh; /* 화면 높이의 80% */
  margin: 20px; /* 전체 여백 */
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  position: relative;
}

.edit-dialog h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #555;
}

/* 에디터 툴바 */
.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
}

.toolbar-btn {
  padding: 4px 8px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 3px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.toolbar-btn:hover {
  background: #e0e0e0;
}

.toolbar-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.toolbar-separator {
  width: 1px;
  height: 20px;
  background: #ccc;
}

.color-picker {
  width: 32px;
  height: 28px;
  padding: 2px;
  border: 1px solid #ddd;
  border-radius: 3px;
  cursor: pointer;
}

.font-size-select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 3px;
  background: white;
  cursor: pointer;
}

/* 리치 텍스트 에디터 */
.rich-text-editor {
  min-height: 200px;
  max-height: 400px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 0 0 4px 4px;
  background: white;
  overflow-y: auto;
  font-size: 16px;
  line-height: 1.5;
}

.rich-text-editor:focus {
  outline: none;
  border-color: #4CAF50;
}

.rich-text-editor :deep(p) {
  margin: 0 0 10px 0;
}

.rich-text-editor :deep(p:last-child) {
  margin-bottom: 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.dialog-actions button {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.save-btn {
  background: #4CAF50;
  color: white;
}

.save-btn:hover {
  background: #45a049;
}

.cancel-btn {
  background: #f0f0f0;
  color: #333;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

/* 스크롤바 스타일링 */
.expanded-text::-webkit-scrollbar,
.rich-text-editor::-webkit-scrollbar {
  width: 6px;
}

.expanded-text::-webkit-scrollbar-track,
.rich-text-editor::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.expanded-text::-webkit-scrollbar-thumb,
.rich-text-editor::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
}

.expanded-text::-webkit-scrollbar-thumb:hover,
.rich-text-editor::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.5);
}
</style>
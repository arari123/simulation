<template>
  <div v-if="show" class="script-editor-overlay" @click="closeEditor">
    <div class="script-editor" @click.stop>
      <div class="script-editor-header">
        <h3>📝 스크립트 편집기 V2</h3>
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
          <div class="codemirror-wrapper" ref="editorWrapper"></div>
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
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { EditorView, keymap, lineNumbers, drawSelection } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { defaultKeymap, historyKeymap, indentWithTab, history, undo, redo } from '@codemirror/commands'
// import { javascript } from '@codemirror/lang-javascript' // 임시로 주석 처리
import { createHighlightPlugin, highlightTheme } from './SimpleHighlighter.js'
import { createSimpleLinter } from './ScriptLinter.js'
import { lintGutter } from '@codemirror/lint'
import { createBreakpointExtension, getBreakpoints, clearAllBreakpoints as clearAllBreakpointsInEditor, initializeBreakpoints } from './BreakpointExtension.js'
import ScriptHelp from '../shared/ScriptHelp.vue'
import { validateScript, parseScriptToActions } from '../../utils/ScriptUtils.js'

// Props 정의 (기존과 동일)
const props = defineProps({
  show: { type: Boolean, default: false },
  scriptContent: { type: String, default: '' },
  actionCount: { type: Number, default: 0 },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  currentBlock: { type: Object, default: null },
  entityType: { type: String, required: true },
  breakpoints: { type: Array, default: () => [] } // 브레이크포인트 배열
})

// Emits 정의 (기존과 동일)
const emit = defineEmits(['close', 'apply', 'breakpointChange'])

// 상태 관리
const editorWrapper = ref(null)
const showHelp = ref(false)
const editorView = ref(null)

// 메서드
function closeEditor() {
  emit('close')
}

function applyScript() {
  try {
    const scriptContent = editorView.value ? editorView.value.state.doc.toString() : ''
    
    
    // 스크립트 유효성 검사
    const validationResult = validateScript(
      scriptContent,
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
      scriptContent,
      props.allBlocks,
      props.currentBlock,
      props.entityType
    )
    
    // 브레이크포인트 정보 가져오기
    const breakpoints = editorView.value ? getBreakpoints(editorView.value) : []
    
    // 파싱된 액션과 함께 스크립트 내용, 브레이크포인트도 전달
    emit('apply', parsedActions, scriptContent, breakpoints)
  } catch (error) {
    alert('스크립트 파싱 오류: ' + error.message)
  }
}

// 브레이크포인트 변경 핸들러
function handleBreakpointChange(lineNumber, isOn) {
  
  if (!props.currentBlock?.id) {
    console.error('No block ID available for breakpoint!')
    return
  }
  
  emit('breakpointChange', props.currentBlock.id, lineNumber, isOn)
}

function createEditor() {
  if (!editorWrapper.value) return

  // 신호명과 블록명 목록 추출
  const signalNames = props.allSignals || []
  const blockNames = (props.allBlocks || []).map(block => block.name).filter(name => name)
  

  // 기본 확장 기능들을 수동으로 구성 (history + 하이라이팅 + linting + 브레이크포인트 포함)
  const basicExtensions = [
    lineNumbers(),
    history(), // 히스토리 기능 추가
    createHighlightPlugin(signalNames, blockNames), // 구문 하이라이팅 추가
    lintGutter(), // 오류 표시 거터 추가
    createSimpleLinter(props.allSignals, props.allBlocks, props.currentBlock, props.entityType), // 실시간 검증 추가
    createBreakpointExtension(handleBreakpointChange), // 브레이크포인트 기능 추가
    // ifBlockHighlighter, // if 블록 하이라이팅 추가 - 임시 비활성화
    // indentGuides, // 들여쓰기 가이드 추가 - 임시 비활성화
    keymap.of([
      ...defaultKeymap,
      ...historyKeymap, // 히스토리 키맵 추가 (Ctrl+Z, Ctrl+Y)
      indentWithTab,
      // 명시적인 키바인딩 추가
      { key: "Ctrl-z", run: undo },
      { key: "Ctrl-y", run: redo },
      { key: "Ctrl-Shift-z", run: redo }
    ])
  ]

  // CodeMirror 편집기 생성
  const startState = EditorState.create({
    doc: props.scriptContent,
    extensions: [
      ...basicExtensions,
      highlightTheme, // 하이라이팅 테마 추가 (if 블록 스타일 포함)
      // javascript(), // 임시로 JavaScript 언어 모드 사용 - 주석 처리
      EditorView.theme({
        // Lint 관련 스타일
        '.cm-diagnostic': {
          padding: '3px 6px',
          borderRadius: '3px',
          border: '1px solid'
        },
        '.cm-diagnostic-error': {
          borderColor: '#d73a49',
          backgroundColor: 'rgba(215, 58, 73, 0.1)'
        },
        // 들여쓰기 가이드라인
        '.cm-indent-guide': {
          borderLeft: '1px solid #e0e0e0',
          marginLeft: '0.5ch',
          position: 'relative'
        },
        // if 블록 하이라이팅
        '.cm-line-if-block': {
          backgroundColor: 'rgba(0, 123, 255, 0.05)',
          borderLeft: '3px solid #007bff',
          paddingLeft: '5px'
        },
        // 중첩된 if 블록
        '.cm-line-if-block-nested': {
          backgroundColor: 'rgba(0, 123, 255, 0.1)',
          borderLeft: '3px solid #0056b3'
        },
        '.cm-diagnostic-warning': {
          borderColor: '#e36209',
          backgroundColor: 'rgba(227, 98, 9, 0.1)'
        },
        '.cm-diagnostic-info': {
          borderColor: '#0366d6',
          backgroundColor: 'rgba(3, 102, 214, 0.1)'
        },
        '.cm-lintRange-error': {
          borderBottom: '2px solid #d73a49',
          paddingBottom: '1px'
        },
        '.cm-lintRange-warning': {
          borderBottom: '2px solid #e36209',
          paddingBottom: '1px'
        },
        '.cm-lintRange-info': {
          borderBottom: '2px solid #0366d6',
          paddingBottom: '1px'
        }
      }, {
        // 기존 테마와 병합
      }),
      EditorView.theme({
        '&': {
          fontSize: '14px',
          fontFamily: '"Courier New", monospace',
          height: '300px' // 고정 높이 설정
        },
        '.cm-content': {
          padding: '12px',
          minHeight: '300px'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-editor': {
          border: '1px solid #ced4da',
          borderRadius: '4px',
          height: '300px' // 편집기 자체 높이 고정
        },
        '.cm-scroller': {
          lineHeight: '1.5',
          overflow: 'auto', // 내부 스크롤 활성화
          maxHeight: '300px' // 최대 높이 제한
        },
        '.cm-line': {
          padding: '0'
        }
      }),
      EditorView.lineWrapping,
      // 탭 크기 설정
      EditorState.tabSize.of(4),
      // 들여쓰기 설정
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          // 내용 변경 시 실시간 검증
        }
      })
    ]
  })

  editorView.value = new EditorView({
    state: startState,
    parent: editorWrapper.value
  })
  
  // 기존 브레이크포인트 복원
  if (props.breakpoints && props.breakpoints.length > 0) {
    nextTick(() => {
      initializeBreakpoints(editorView.value, props.breakpoints)
    })
  }
}

function destroyEditor() {
  if (editorView.value) {
    editorView.value.destroy()
    editorView.value = null
  }
}

function updateEditorContent() {
  if (editorView.value && props.scriptContent !== editorView.value.state.doc.toString()) {
    editorView.value.dispatch({
      changes: {
        from: 0,
        to: editorView.value.state.doc.length,
        insert: props.scriptContent
      }
    })
  }
}

// 라이프사이클
onMounted(() => {
  if (props.show) {
    nextTick(() => {
      createEditor()
    })
  }
})

onUnmounted(() => {
  destroyEditor()
})

// Props 변경 감지
watch(() => props.show, (newShow) => {
  if (newShow) {
    nextTick(() => {
      createEditor()
    })
  } else {
    destroyEditor()
  }
})

watch(() => props.scriptContent, () => {
  updateEditorContent()
})

// 브레이크포인트를 강제로 클리어하는 메서드
function forceClearBreakpoints() {
  if (editorView.value) {
    clearAllBreakpointsInEditor(editorView.value)
  }
}

// 브레이크포인트 변경 감지
watch(() => props.breakpoints, (newBreakpoints, oldBreakpoints) => {
  if (editorView.value) {
    // 기존 브레이크포인트를 모두 제거하고 새로 설정
    clearAllBreakpointsInEditor(editorView.value)
    if (newBreakpoints && newBreakpoints.length > 0) {
      initializeBreakpoints(editorView.value, newBreakpoints)
    }
  }
}, { deep: true, immediate: true })

// 메서드를 외부에서 호출할 수 있도록 노출
defineExpose({
  forceClearBreakpoints
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
  z-index: 5000; /* 제어판(1000)보다 확실히 위에 표시 */
}

.script-editor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  width: 90%;
  max-width: 800px;
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

.codemirror-wrapper {
  min-height: 300px;
  border-radius: 4px;
  overflow: hidden;
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

/* CodeMirror 스타일 오버라이드 */
:deep(.cm-editor) {
  border: 1px solid #ced4da !important;
}

:deep(.cm-content) {
  padding: 12px !important;
  min-height: 300px !important;
}

:deep(.cm-focused) {
  outline: none !important;
}
</style>
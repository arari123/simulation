<template>
  <div class="log-panel" :class="{ minimized: isMinimized }">
    <!-- 헤더 -->
    <div class="log-header" @click="toggleMinimize">
      <span class="title">📋 시뮬레이션 로그</span>
      <div class="controls">
        <span class="log-count">{{ filteredLogs.length }}개</span>
        <button @click.stop="clearLogs" title="로그 지우기" class="control-btn">
          🗑️
        </button>
        <button @click.stop="showExportMenu = !showExportMenu" title="로그 내보내기" class="control-btn">
          💾
        </button>
        <button @click.stop="toggleMinimize" title="최소화/최대화" class="control-btn">
          {{ isMinimized ? '▲' : '▼' }}
        </button>
      </div>
      
      <!-- 내보내기 메뉴 -->
      <div v-if="showExportMenu" class="export-menu" @click.stop>
        <button @click="exportLogs('txt')">TXT로 내보내기</button>
        <button @click="exportLogs('csv')">CSV로 내보내기</button>
        <button @click="exportLogs('json')">JSON으로 내보내기</button>
      </div>
    </div>
    
    <!-- 로그 필터 -->
    <div v-if="!isMinimized" class="log-filters">
      <input 
        v-model="filterText" 
        placeholder="로그 검색..."
        class="filter-input"
        @input="handleFilterChange"
      >
      <select v-model="filterBlock" class="filter-select" @change="handleFilterChange">
        <option value="">모든 블록</option>
        <option v-for="block in uniqueBlocks" :key="block" :value="block">
          {{ block }}
        </option>
      </select>
      <button 
        @click="toggleAutoScroll" 
        class="auto-scroll-btn"
        :class="{ active: isAutoScrollEnabled }"
        title="자동 스크롤"
      >
        ⬇️
      </button>
    </div>
    
    <!-- 로그 내용 -->
    <div v-if="!isMinimized" class="log-content" ref="logContentRef">
      <div 
        v-for="(log, index) in filteredLogs" 
        :key="`${log.time}-${log.block}-${index}`"
        class="log-entry"
        :class="getLogClass(log)"
      >
        <span class="log-time">[{{ formatTime(log.time) }}s]</span>
        <span class="log-block">[{{ log.block }}]</span>
        <span class="log-message" v-html="highlightText(log.message)"></span>
      </div>
      <div v-if="filteredLogs.length === 0" class="no-logs">
        {{ logs.length === 0 ? '로그가 없습니다' : '필터와 일치하는 로그가 없습니다' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  isAutoScrollEnabled: {
    type: Boolean,
    default: true
  },
  controlPanelWidth: {
    type: Number,
    default: 300
  }
})

const emit = defineEmits(['clear-logs', 'export-logs', 'toggle-auto-scroll'])

// 상태
const isMinimized = ref(true) // 초기값을 true로 변경하여 최소화 상태로 시작
const filterText = ref('')
const filterBlock = ref('')
const showExportMenu = ref(false)
const logContentRef = ref(null)

// 필터링된 로그
const filteredLogs = computed(() => {
  let filtered = props.logs
  
  // 블록 필터
  if (filterBlock.value) {
    filtered = filtered.filter(log => log.block === filterBlock.value)
  }
  
  // 텍스트 필터
  if (filterText.value) {
    const searchText = filterText.value.toLowerCase()
    filtered = filtered.filter(log => 
      log.message.toLowerCase().includes(searchText) ||
      log.block.toLowerCase().includes(searchText)
    )
  }
  
  return filtered
})

// 고유 블록 목록
const uniqueBlocks = computed(() => {
  const blocks = new Set()
  props.logs.forEach(log => blocks.add(log.block))
  return Array.from(blocks).sort()
})

// 메서드
function toggleMinimize() {
  isMinimized.value = !isMinimized.value
}

function clearLogs() {
  if (confirm('모든 로그를 삭제하시겠습니까?')) {
    emit('clear-logs')
  }
}

function exportLogs(format) {
  emit('export-logs', format)
  showExportMenu.value = false
}

function toggleAutoScroll() {
  emit('toggle-auto-scroll')
}

function formatTime(time) {
  return time.toFixed(1)
}

function getLogClass(log) {
  const message = log.message.toLowerCase()
  if (message.includes('error') || message.includes('오류')) {
    return 'log-error'
  }
  if (message.includes('warning') || message.includes('경고')) {
    return 'log-warning'
  }
  return 'log-normal'
}

function highlightText(text) {
  if (!filterText.value) return text
  
  const regex = new RegExp(`(${filterText.value})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

function handleFilterChange() {
  // 필터 변경 시 스크롤 위치 유지
  if (logContentRef.value) {
    const scrollPosition = logContentRef.value.scrollTop
    nextTick(() => {
      if (logContentRef.value) {
        logContentRef.value.scrollTop = scrollPosition
      }
    })
  }
}

// 자동 스크롤
function scrollToBottom() {
  if (logContentRef.value && props.isAutoScrollEnabled && !isMinimized.value) {
    nextTick(() => {
      if (logContentRef.value) {
        logContentRef.value.scrollTop = logContentRef.value.scrollHeight
      }
    })
  }
}

// 로그 추가 시 자동 스크롤
watch(() => props.logs.length, () => {
  scrollToBottom()
})

// 외부 클릭 시 내보내기 메뉴 닫기
function handleClickOutside(event) {
  if (showExportMenu.value && !event.target.closest('.export-menu')) {
    showExportMenu.value = false
  }
}

// 마운트/언마운트 시 이벤트 처리
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.log-panel {
  position: fixed;
  bottom: 0;
  left: v-bind((controlPanelWidth + 21) + 'px');
  width: 800px;
  max-width: calc(70vw - v-bind((controlPanelWidth + 20) + 'px'));
  background: white;
  border: 1px solid #ddd;
  border-radius: 0 8px 0 0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
  z-index: 100;
  transition: all 0.3s ease;
}

.log-panel.minimized {
  height: 40px;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  cursor: pointer;
  user-select: none;
  position: relative;
}

.log-header:hover {
  background: #e8e8e8;
}

.title {
  font-weight: 500;
  color: #333;
}

.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-count {
  font-size: 12px;
  color: #666;
  padding: 2px 8px;
  background: white;
  border-radius: 12px;
  border: 1px solid #ddd;
}

.control-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.control-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

.export-menu {
  position: absolute;
  top: 100%;
  left: 60px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  overflow: hidden;
}

.export-menu button {
  display: block;
  width: 100%;
  padding: 8px 16px;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.export-menu button:hover {
  background: #f0f0f0;
}

.log-filters {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #eee;
}

.filter-input {
  flex: 1;
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.filter-input:focus {
  outline: none;
  border-color: #4CAF50;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #4CAF50;
}

.auto-scroll-btn {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.auto-scroll-btn.active {
  background: #4CAF50;
  border-color: #4CAF50;
}

.log-content {
  height: 300px;
  overflow-y: auto;
  padding: 8px 0;
}

.log-entry {
  padding: 4px 16px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.log-entry:hover {
  background: #f8f8f8;
}

.log-time {
  color: #666;
  margin-right: 8px;
}

.log-block {
  color: #2196F3;
  font-weight: 500;
  margin-right: 8px;
}

.log-message {
  color: #333;
}

.log-message :deep(mark) {
  background: #ffeb3b;
  padding: 0 2px;
  border-radius: 2px;
}

.log-entry.log-error {
  background: #ffebee;
}

.log-entry.log-error .log-message {
  color: #c62828;
}

.log-entry.log-warning {
  background: #fff8e1;
}

.log-entry.log-warning .log-message {
  color: #f57c00;
}

.no-logs {
  padding: 40px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

/* 스크롤바 스타일링 */
.log-content::-webkit-scrollbar {
  width: 8px;
}

.log-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.log-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 반응형 */
@media (max-width: 768px) {
  .log-panel {
    width: 100%;
    max-width: none;
    border-radius: 0;
  }
}
</style>
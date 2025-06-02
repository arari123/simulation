<template>
  <div class="script-preview-section">
    <div class="section-header">
      <h4>생성된 스크립트 미리보기</h4>
      <button @click="toggleExpanded" class="toggle-btn">
        {{ isExpanded ? '접기' : '펼치기' }}
      </button>
    </div>
    
    <div class="script-container" :class="{ expanded: isExpanded }">
      <pre class="script-content"><code>{{ script }}</code></pre>
    </div>
    
    <div class="script-info">
      <span class="line-count">{{ lineCount }}줄</span>
      <span class="char-count">{{ charCount }}자</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Props
const props = defineProps({
  script: { type: String, default: '' }
})

// 상태
const isExpanded = ref(false)

// 계산된 속성
const lineCount = computed(() => {
  return props.script.split('\n').length
})

const charCount = computed(() => {
  return props.script.length
})

// 메서드
function toggleExpanded() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.script-preview-section {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  background: #f8f9fa;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h4 {
  margin: 0;
  color: #495057;
  font-size: 14px;
}

.toggle-btn {
  padding: 4px 8px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.toggle-btn:hover {
  background: #5a6268;
}

.script-container {
  background: white;
  border: 1px solid #ced4da;
  border-radius: 4px;
  overflow: hidden;
  max-height: 120px;
  transition: max-height 0.3s ease;
}

.script-container.expanded {
  max-height: 400px;
}

.script-content {
  padding: 12px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #495057;
  overflow: auto;
  white-space: pre;
  background: transparent;
}

.script-info {
  display: flex;
  gap: 15px;
  margin-top: 8px;
  font-size: 11px;
  color: #6c757d;
}

.line-count, .char-count {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 2px;
}
</style> 
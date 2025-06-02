<template>
  <div class="action-list">
    <div v-if="actions.length === 0" class="empty-state">
      <p>액션이 없습니다. 액션을 추가하거나 스크립트 편집기를 사용해보세요.</p>
    </div>
    
    <div v-else class="action-items">
      <div
        v-for="(action, index) in actions"
        :key="action.id || index"
        class="action-item"
        :class="{ 
          editing: editingActionIndex === index,
          error: action.type === 'script_error'
        }"
      >
        <div class="action-content">
          <div class="action-header">
            <span class="action-type">{{ getActionTypeLabel(action.type) }}</span>
            <span class="action-name">{{ action.name || '이름 없음' }}</span>
          </div>
          
          <div class="action-details" v-if="action.parameters">
            <ActionParameters :action="action" />
          </div>
          
          <div v-if="action.type === 'script_error'" class="error-details">
            <p class="error-message">{{ action.parameters?.error }}</p>
            <p class="error-line">라인 {{ action.parameters?.lineNumber }}</p>
          </div>
        </div>
        
        <div class="action-buttons">
          <button 
            @click="$emit('edit-action', index)"
            class="edit-btn"
            :disabled="action.type === 'script_error'"
          >
            수정
          </button>
          <button 
            @click="$emit('delete-action', index)"
            class="delete-btn"
          >
            삭제
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ActionParameters from './ActionParameters.vue'

// Props
const props = defineProps({
  actions: { type: Array, default: () => [] },
  editingActionIndex: { type: Number, default: -1 }
})

// Emits
const emit = defineEmits(['edit-action', 'delete-action'])

// 액션 타입 라벨 매핑
function getActionTypeLabel(type) {
  const labels = {
    'delay': '지연',
    'signal_update': '신호 설정',
    'signal_wait': '신호 대기',
    'route_to_connector': '이동',
    'conditional_branch': '조건부 실행',
    'action_jump': '점프',
    'script_error': '오류'
  }
  return labels[type] || type
}
</script>

<style scoped>
.action-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e9ecef;
  border-radius: 4px;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #6c757d;
  background: #f8f9fa;
}

.action-items {
  display: flex;
  flex-direction: column;
}

.action-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e9ecef;
  background: white;
  transition: background-color 0.2s;
}

.action-item:hover {
  background: #f8f9fa;
}

.action-item.editing {
  background: #e3f2fd;
  border-color: #2196f3;
}

.action-item.error {
  background: #ffeaa7;
  border-color: #fdcb6e;
}

.action-item:last-child {
  border-bottom: none;
}

.action-content {
  flex: 1;
  min-width: 0;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.action-type {
  background: #007bff;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
}

.action-item.error .action-type {
  background: #dc3545;
}

.action-name {
  font-weight: 500;
  color: #343a40;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-details {
  font-size: 12px;
  color: #6c757d;
  margin-top: 4px;
}

.error-details {
  margin-top: 8px;
}

.error-message {
  color: #dc3545;
  font-size: 12px;
  margin: 0 0 4px 0;
  font-weight: 500;
}

.error-line {
  color: #6c757d;
  font-size: 11px;
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: 6px;
  margin-left: 12px;
}

.edit-btn, .delete-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.edit-btn {
  background: #007bff;
  color: white;
}

.edit-btn:hover:not(:disabled) {
  background: #0056b3;
}

.edit-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.delete-btn {
  background: #dc3545;
  color: white;
}

.delete-btn:hover {
  background: #c82333;
}
</style> 
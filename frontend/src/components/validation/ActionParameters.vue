<template>
  <div class="action-parameters">
    <!-- 지연 액션 파라미터 -->
    <template v-if="action.type === 'delay'">
      <span class="param-label">지연시간:</span>
      <span class="param-value">{{ action.parameters?.duration }}초</span>
    </template>

    <!-- 신호 업데이트 액션 파라미터 -->
    <template v-else-if="action.type === 'signal_update'">
      <span class="param-label">신호:</span>
      <span class="param-value">{{ action.parameters?.signal_name }}</span>
      <span class="param-separator">→</span>
      <span class="param-value" :class="{ 'value-true': action.parameters?.value, 'value-false': !action.parameters?.value }">
        {{ action.parameters?.value ? 'true' : 'false' }}
      </span>
    </template>

    <!-- 신호 대기 액션 파라미터 -->
    <template v-else-if="action.type === 'signal_wait'">
      <span class="param-label">대기 신호:</span>
      <span class="param-value">{{ action.parameters?.signal_name }}</span>
      <span class="param-separator">=</span>
      <span class="param-value" :class="{ 'value-true': action.parameters?.expected_value, 'value-false': !action.parameters?.expected_value }">
        {{ action.parameters?.expected_value ? 'true' : 'false' }}
      </span>
    </template>

    <!-- 이동 액션 파라미터 -->
    <template v-else-if="action.type === 'route_to_connector'">
      <span class="param-label">목적지:</span>
      <span class="param-value">
        {{ getDestinationText() }}
      </span>
      <template v-if="action.parameters?.delay && action.parameters.delay !== '0'">
        <span class="param-separator">|</span>
        <span class="param-label">지연:</span>
        <span class="param-value">{{ action.parameters.delay }}초</span>
      </template>
    </template>

    <!-- 조건부 실행 액션 파라미터 -->
    <template v-else-if="action.type === 'conditional_branch'">
      <span class="param-label">스크립트:</span>
      <span class="param-value script-preview">{{ getScriptPreview() }}</span>
    </template>

    <!-- 점프 액션 파라미터 -->
    <template v-else-if="action.type === 'action_jump'">
      <span class="param-label">점프 대상:</span>
      <span class="param-value">{{ action.parameters?.target }}</span>
    </template>

    <!-- 기타 액션 파라미터 -->
    <template v-else>
      <span class="param-label">파라미터:</span>
      <span class="param-value">{{ formatParameters() }}</span>
    </template>
  </div>
</template>

<script setup>
// Props
const props = defineProps({
  action: { type: Object, required: true }
})

// 목적지 텍스트 생성
function getDestinationText() {
  const params = props.action.parameters
  if (!params) return '알 수 없음'
  
  if (params.target_block_name && params.target_connector_name) {
    if (params.target_block_name === 'self') {
      return `self.${params.target_connector_name}`
    } else {
      return `${params.target_block_name}.${params.target_connector_name}`
    }
  }
  
  if (params.target_block_id && params.target_connector_id) {
    return `블록 ${params.target_block_id}.커넥터 ${params.target_connector_id}`
  }
  
  return '알 수 없음'
}

// 스크립트 미리보기 생성
function getScriptPreview() {
  const script = props.action.parameters?.script || ''
  if (script.length <= 50) {
    return script
  }
  return script.substring(0, 47) + '...'
}

// 기타 파라미터 포맷팅
function formatParameters() {
  const params = props.action.parameters
  if (!params) return '없음'
  
  const entries = Object.entries(params)
  if (entries.length === 0) return '없음'
  
  return entries
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ')
}
</script>

<style scoped>
.action-parameters {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.param-label {
  color: #6c757d;
  font-size: 11px;
  font-weight: 500;
}

.param-value {
  color: #343a40;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  background: #f8f9fa;
  padding: 1px 4px;
  border-radius: 2px;
}

.param-separator {
  color: #6c757d;
  font-size: 11px;
  font-weight: bold;
}

.value-true {
  background: #d4edda;
  color: #155724;
}

.value-false {
  background: #f8d7da;
  color: #721c24;
}

.script-preview {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-style: italic;
}
</style> 
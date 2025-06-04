<template>
  <SettingsBase
    entity-type="connector"
    :title="`커넥터 설정 - ${connectorInfo.blockName}.${connectorInfo.connectorName}`"
    subtitle="커넥터의 액션을 관리합니다"
    :initial-name="connectorInfo.connectorName"
    :initial-actions="connectorInfo.actions || []"
    :all-signals="allSignals"
    :all-blocks="allBlocks"
    :current-block="currentBlock"
    :validate-name="validateConnectorName"
    @close="$emit('close-popup')"
    @save="handleSave"
    @name-change="handleNameChange"
    @delete-connector="handleDeleteConnector"
  >
    <template #extra-info>
      <div class="connector-move-info">
        <div class="info-icon">💡</div>
        <div class="info-text">
          커넥터가 선택된 상태에서 드래그하여 위치를 이동할 수 있습니다.
          <br />
          <span class="highlight">파란색 점선 원</span>이 표시되면 드래그가 가능합니다.
        </div>
      </div>
    </template>
  </SettingsBase>
</template>

<script setup>
import { computed } from 'vue'
import SettingsBase from './shared/SettingsBase.vue'
import { validateConnectorName as validateConnectorNameUtil } from '../utils/BlockManager.js'

// Props 정의
const props = defineProps({
  connectorInfo: { type: Object, required: true },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  isSidebar: { type: Boolean, default: false }
})

// Emits 정의
const emit = defineEmits([
  'close-popup',
  'save-connector-settings',
  'change-connector-name',
  'delete-connector'
])

// 현재 블록 찾기
const currentBlock = computed(() => {
  return props.allBlocks.find(block => block.id == props.connectorInfo.blockId)
})

// 유효성 검사 함수
const validateConnectorName = (name) => {
  const block = currentBlock.value
  if (!block) return { valid: false, error: '블록을 찾을 수 없습니다.' }
  
  return validateConnectorNameUtil(
    name, 
    block.connectionPoints || [], 
    props.connectorInfo.connectorId
  )
}

// 이벤트 핸들러
function handleSave(data) {
  emit('save-connector-settings', 
    props.connectorInfo.blockId, 
    props.connectorInfo.connectorId, 
    data.actions, 
    data.name
  )
}

function handleNameChange(newName) {
  emit('change-connector-name', 
    props.connectorInfo.blockId, 
    props.connectorInfo.connectorId, 
    newName
  )
}

function handleDeleteConnector() {
  emit('delete-connector', 
    props.connectorInfo.blockId, 
    props.connectorInfo.connectorId
  )
}
</script>

<style scoped>
.connector-move-info {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background-color: #E3F2FD;
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid #90CAF9;
}

.info-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.info-text {
  font-size: 13px;
  color: #1565C0;
  line-height: 1.6;
}

.highlight {
  font-weight: bold;
  color: #0D47A1;
}
</style> 
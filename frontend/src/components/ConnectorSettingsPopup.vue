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
  />
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
  'change-connector-name'
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
</script> 
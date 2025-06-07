<template>
  <SettingsBase
    entity-type="block"
    :title="`블록 설정 - ${blockData.name}`"
    subtitle="블록의 기본 정보와 액션을 관리합니다"
    :initial-name="blockData.name"
    :initial-actions="blockData.actions || []"
    :initial-max-capacity="blockData.maxCapacity || 1"
    :initial-connectors="blockData.connectionPoints || []"
    :initial-background-color="blockData.backgroundColor || '#cfdff7'"
    :initial-text-color="blockData.textColor || '#000000'"
    :all-signals="allSignals"
    :all-blocks="allBlocks"
    :current-block="blockData"
    :validate-name="validateBlockName"
    :breakpoints="blockBreakpoints"
    @close="$emit('close-popup')"
    @save="handleSave"
    @name-change="handleNameChange"
    @max-capacity-change="handleMaxCapacityChange"
    @background-color-change="handleBackgroundColorChange"
    @text-color-change="handleTextColorChange"
    @connector-add="handleConnectorAdd"
    @delete-block="$emit('delete-block', blockData.id)"
    @breakpoint-change="handleBreakpointChange"
  />
</template>

<script setup>
import { computed } from 'vue'
import SettingsBase from './shared/SettingsBase.vue'
import { validateBlockName as validateBlockNameUtil } from '../utils/BlockManager.js'

// Props 정의
const props = defineProps({
  blockData: { type: Object, required: true },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  isSidebar: { type: Boolean, default: false },
  blockBreakpoints: { type: Array, default: () => [] }
})

// Emits 정의
const emit = defineEmits([
  'close-popup',
  'save-block-settings',
  'copy-block',
  'delete-block',
  'add-connector',
  'change-block-name',
  'breakpoint-change'
])

// 유효성 검사 함수
const validateBlockName = (name) => {
  return validateBlockNameUtil(name, props.allBlocks, props.blockData.id)
}

// 이벤트 핸들러
function handleSave(data) {
  emit('save-block-settings', props.blockData.id, data.actions, data.maxCapacity, data.name, data.backgroundColor, data.textColor)
}

function handleNameChange(newName) {
  emit('change-block-name', props.blockData.id, props.blockData.name, newName)
}

function handleMaxCapacityChange(newCapacity) {
  emit('save-block-settings', props.blockData.id, props.blockData.actions || [], newCapacity, props.blockData.name)
}

// 색상 관련 이벤트 핸들러
function handleBackgroundColorChange(newColor) {
  emit('save-block-settings', props.blockData.id, props.blockData.actions || [], props.blockData.maxCapacity, props.blockData.name, newColor, props.blockData.textColor)
}

function handleTextColorChange(newColor) {
  emit('save-block-settings', props.blockData.id, props.blockData.actions || [], props.blockData.maxCapacity, props.blockData.name, props.blockData.backgroundColor, newColor)
}

// 커넥터 관련 이벤트 핸들러
function handleConnectorAdd(newConnector) {
  emit('add-connector', props.blockData.id, newConnector)
}

// 브레이크포인트 변경 핸들러
function handleBreakpointChange(blockId, lineNumber, isOn) {
  emit('breakpoint-change', blockId, lineNumber, isOn)
}
</script>
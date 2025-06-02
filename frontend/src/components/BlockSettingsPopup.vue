<template>
  <SettingsBase
    entity-type="block"
    :title="`블록 설정 - ${blockData.name}`"
    subtitle="블록의 기본 정보와 액션을 관리합니다"
    :initial-name="blockData.name"
    :initial-actions="blockData.actions || []"
    :initial-max-capacity="blockData.maxCapacity || 1"
    :all-signals="allSignals"
    :all-blocks="allBlocks"
    :current-block="blockData"
    :validate-name="validateBlockName"
    @close="$emit('close-popup')"
    @save="handleSave"
    @name-change="handleNameChange"
    @max-capacity-change="handleMaxCapacityChange"
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
  isSidebar: { type: Boolean, default: false }
})

// Emits 정의
const emit = defineEmits([
  'close-popup',
  'save-block-settings',
  'copy-block',
  'delete-block',
  'add-connector',
  'change-block-name'
])

// 유효성 검사 함수
const validateBlockName = (name) => {
  return validateBlockNameUtil(name, props.allBlocks, props.blockData.id)
}

// 이벤트 핸들러
function handleSave(data) {
  emit('save-block-settings', props.blockData.id, data.actions, data.maxCapacity, data.name)
}

function handleNameChange(newName) {
  emit('change-block-name', props.blockData.id, props.blockData.name, newName)
}

function handleMaxCapacityChange(newCapacity) {
  emit('save-block-settings', props.blockData.id, props.blockData.actions || [], newCapacity, props.blockData.name)
}
</script>
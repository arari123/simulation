<template>
  <div class="action-editor">
    <h3>{{ actionIndex >= 0 ? '액션 수정' : '새 액션 추가' }}</h3>
    
    <div class="form-group">
      <label for="action-name">액션 이름:</label>
      <input
        id="action-name"
        v-model="localAction.name"
        type="text"
        placeholder="액션 이름을 입력하세요"
        class="form-input"
      />
    </div>

    <div class="form-group">
      <label for="action-type">액션 타입:</label>
      <select id="action-type" v-model="localAction.type" class="form-select" @change="handleTypeChange">
        <option value="delay">딜레이</option>
        <option value="signal_wait">신호 대기</option>
        <option value="signal_update">신호 변경</option>
        <option value="signal_check">신호 확인</option>
        <option value="route_to_connector">연결점 이동</option>
        <option value="block_entry">블록으로 이동</option>
        <option value="conditional_branch">조건부 실행</option>
        <option value="action_jump">액션 점프</option>
        <option value="custom_sink">커스텀 싱크</option>
        <option value="script">스크립트</option>
      </select>
    </div>

    <!-- 타입별 파라미터 입력 -->
    <div class="parameters-section">
      <h4>파라미터</h4>
      
      <!-- 딜레이 -->
      <div v-if="localAction.type === 'delay'" class="form-group">
        <label for="delay-duration">지연 시간 (초):</label>
        <input
          id="delay-duration"
          v-model="localAction.parameters.duration"
          type="text"
          placeholder="예: 5 또는 1-10"
          class="form-input"
          @change="updateActionName"
        />
        <div class="help-text">숫자 또는 "최소-최대" 형태로 랜덤 딜레이 설정 (예: 1-10)</div>
      </div>

      <!-- 신호 대기 -->
      <div v-else-if="localAction.type === 'signal_wait'" class="form-group">
        <label for="wait-signal">신호 이름:</label>
        <select 
          id="wait-signal" 
          v-model="localAction.parameters.signal_name" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option value="">신호를 선택하세요</option>
          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
        </select>
        <label for="wait-value">대기할 값:</label>
        <select 
          id="wait-value" 
          v-model="localAction.parameters.expected_value" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option :value="true">true</option>
          <option :value="false">false</option>
        </select>
      </div>

      <!-- 신호 변경 -->
      <div v-else-if="localAction.type === 'signal_update'" class="form-group">
        <label for="update-signal">신호 이름:</label>
        <select 
          id="update-signal" 
          v-model="localAction.parameters.signal_name" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option value="">신호를 선택하세요</option>
          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
        </select>
        <label for="update-value">설정할 값:</label>
        <select 
          id="update-value" 
          v-model="localAction.parameters.value" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option :value="true">true</option>
          <option :value="false">false</option>
        </select>
      </div>

      <!-- 신호 확인 -->
      <div v-else-if="localAction.type === 'signal_check'" class="form-group">
        <label for="check-signal">신호 이름:</label>
        <select 
          id="check-signal" 
          v-model="localAction.parameters.signal_name" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option value="">신호를 선택하세요</option>
          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
        </select>
        <label for="check-value">확인할 값:</label>
        <select 
          id="check-value" 
          v-model="localAction.parameters.expected_value" 
          class="form-select" 
          @change="updateActionName" 
          @input="updateActionName"
        >
          <option :value="true">true</option>
          <option :value="false">false</option>
        </select>
      </div>

      <!-- 연결점 이동 -->
      <div v-else-if="localAction.type === 'route_to_connector'" class="form-group">
        <label for="route-type">이동 타입:</label>
        <select id="route-type" v-model="routeType" class="form-select" @change="handleRouteTypeChange">
          <option value="self">현재 블록 내 연결점</option>
          <option value="other">다른 블록의 연결점</option>
        </select>

        <div v-if="routeType === 'self'">
          <label for="self-connector">연결점:</label>
          <select id="self-connector" v-model="localAction.parameters.connector_id" class="form-select" @change="updateActionName">
            <option value="self">블록 액션으로 이동</option>
            <option v-for="cp in currentBlockConnectors" :key="cp.id" :value="cp.id">
              {{ cp.name || cp.id }}
            </option>
          </select>
        </div>

        <div v-else>
          <label for="target-block">대상 블록:</label>
          <select id="target-block" v-model="localAction.parameters.target_block_id" class="form-select" @change="updateTargetConnectors">
            <option value="">블록을 선택하세요</option>
            <option v-for="block in allBlocks" :key="block.id" :value="block.id">
              {{ block.name }}
            </option>
          </select>

          <label for="target-connector">대상 연결점:</label>
          <select id="target-connector" v-model="localAction.parameters.target_connector_id" class="form-select" @change="updateActionName">
            <option value="">연결점을 선택하세요</option>
            <option v-for="cp in targetBlockConnectors" :key="cp.id" :value="cp.id">
              {{ cp.name || cp.id }}
            </option>
          </select>
        </div>

        <label for="route-delay">이동 딜레이 (초):</label>
        <input
          id="route-delay"
          v-model="localAction.parameters.delay"
          type="text"
          placeholder="예: 3 또는 1-5"
          class="form-input"
          @change="updateActionName"
        />
        <div class="help-text">숫자 또는 "최소-최대" 형태로 랜덤 딜레이 설정</div>
      </div>

      <!-- 블록으로 이동 -->
      <div v-else-if="localAction.type === 'block_entry'" class="form-group">
        <label for="entry-delay">진입 딜레이 (초):</label>
        <input
          id="entry-delay"
          v-model="localAction.parameters.delay"
          type="text"
          placeholder="예: 1 또는 1-3"
          class="form-input"
          @change="updateActionName"
        />
        <div class="help-text">같은 블록으로 진입하기 전 딜레이</div>
        
        <label for="target-block-name">대상 블록명:</label>
        <input
          id="target-block-name"
          v-model="localAction.parameters.target_block_name"
          type="text"
          placeholder="예: 공정1"
          class="form-input"
          @change="updateActionName"
        />
        <div class="help-text">이동할 블록 이름 (보통 현재 블록명과 동일)</div>
      </div>

      <!-- 조건부 실행 -->
      <div v-else-if="localAction.type === 'conditional_branch'" class="form-group">
        <label for="condition-script">조건부 실행 스크립트:</label>
        <textarea
          id="condition-script"
          v-model="localAction.parameters.script"
          rows="8"
          placeholder="조건부 실행 스크립트를 입력하세요..."
          class="form-textarea"
          @keydown="onKeyDown"
        ></textarea>
        <div class="help-text">
          예시:<br>
          if 신호명 = true<br>
          &nbsp;&nbsp;&nbsp;&nbsp;delay 5<br>
          &nbsp;&nbsp;&nbsp;&nbsp;go to 블록이름.커넥터이름
        </div>
      </div>

      <!-- 액션 점프 -->
      <div v-else-if="localAction.type === 'action_jump'" class="form-group">
        <label for="jump-target">점프할 액션:</label>
        <select id="jump-target" v-model="localAction.parameters.target_action_name" class="form-select" @change="updateActionName">
          <option value="">액션을 선택하세요</option>
          <option v-for="action in availableActions" :key="action.id" :value="action.name">
            {{ action.name }}
          </option>
        </select>
      </div>

      <!-- 커스텀 싱크 (파라미터 없음) -->
      <div v-else-if="localAction.type === 'custom_sink'" class="info-text">
        이 액션은 추가 파라미터가 필요하지 않습니다.
      </div>

      <!-- 스크립트 -->
      <div v-else-if="localAction.type === 'script'" class="form-group">
        <label for="script-content">스크립트:</label>
        <textarea
          id="script-content"
          v-model="localAction.parameters.script"
          rows="10"
          placeholder="스크립트를 입력하세요..."
          class="form-textarea"
          @keydown="onKeyDown"
        ></textarea>
        <div class="help-text">
          사용 가능한 명령어:<br>
          - delay 5 (5초 대기)<br>
          - 신호명 = true/false (신호 설정)<br>
          - wait 신호명 = true/false (신호 대기)<br>
          - if 신호명 = true/false (조건부 실행, 다음 줄 들여쓰기)<br>
          - go to 블록명.커넥터명 (이동)<br>
          - jump to 1 (1번 줄로 점프)
        </div>
      </div>
    </div>

    <div class="editor-footer">
      <button @click="handleSave" class="save-btn" :disabled="!isValid">저장</button>
      <button @click="$emit('cancel')" class="cancel-btn">취소</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

// Props
const props = defineProps({
  action: { type: Object, required: true },
  actionIndex: { type: Number, default: -1 },
  availableActions: { type: Array, default: () => [] },
  allSignals: { type: Array, default: () => [] },
  allBlocks: { type: Array, default: () => [] },
  currentBlock: { type: Object, default: null }
})

// Emits
const emit = defineEmits(['save', 'cancel'])

// 상태
const localAction = ref({})
const routeType = ref('self')
const targetBlockConnectors = ref([])
const isInitialLoad = ref(true) // 초기 로딩 감지용
const userModifiedName = ref(false) // 사용자가 직접 이름을 수정했는지 추적

// 계산된 속성
const currentBlockConnectors = computed(() => {
  return props.currentBlock?.connectionPoints || []
})

const isValid = computed(() => {
  if (!localAction.value.name?.trim()) return false
  
  // 타입별 유효성 검사
  switch (localAction.value.type) {
    case 'delay':
      return localAction.value.parameters?.duration != null
    case 'signal_wait':
    case 'signal_update':
    case 'signal_check':
      return localAction.value.parameters?.signal_name && 
             localAction.value.parameters?.expected_value !== undefined ||
             localAction.value.parameters?.value !== undefined
    case 'route_to_connector':
      if (routeType.value === 'self') {
        return localAction.value.parameters?.connector_id
      } else {
        return localAction.value.parameters?.target_block_id && 
               localAction.value.parameters?.target_connector_id
      }
    case 'conditional_branch':
      return localAction.value.parameters?.script?.trim()
    case 'action_jump':
      return localAction.value.parameters?.target_action_name
    case 'custom_sink':
      return true
    case 'script':
      return localAction.value.parameters?.script?.trim()
    default:
      return false
  }
})

// 메서드
function handleTypeChange() {
  // 타입 변경 시 파라미터 초기화
  localAction.value.parameters = {}
  
  // 타입별 기본값 설정
  switch (localAction.value.type) {
    case 'delay':
      localAction.value.parameters = { duration: '5' }
      break
    case 'signal_wait':
    case 'signal_update':
    case 'signal_check':
      localAction.value.parameters = { signal_name: '', expected_value: true, value: true }
      break
    case 'route_to_connector':
      localAction.value.parameters = { connector_id: 'self', delay: '0' }
      routeType.value = 'self'
      break
    case 'block_entry':
      localAction.value.parameters = { delay: '1', target_block_name: '' }
      break
    case 'conditional_branch':
      localAction.value.parameters = { script: '' }
      break
    case 'action_jump':
      localAction.value.parameters = { target_action_name: '' }
      break
    case 'custom_sink':
      localAction.value.parameters = {}
      break
    case 'script':
      localAction.value.parameters = { script: '' }
      break
  }
}

function handleRouteTypeChange() {
  if (routeType.value === 'self') {
    localAction.value.parameters = {
      connector_id: 'self',
      delay: localAction.value.parameters?.delay || '0'
    }
  } else {
    localAction.value.parameters = {
      target_block_id: '',
      target_connector_id: '',
      delay: localAction.value.parameters?.delay || '0'
    }
  }
  // 라우트 타입 변경 시 액션 이름 업데이트
  updateActionName()
}

function updateTargetConnectors() {
  const targetBlockId = localAction.value.parameters.target_block_id
  const targetBlock = props.allBlocks.find(b => b.id == targetBlockId)
  targetBlockConnectors.value = targetBlock?.connectionPoints || []
  localAction.value.parameters.target_connector_id = ''
  // 대상 블록 변경 시 액션 이름 업데이트
  updateActionName()
}

function handleSave() {
  if (!isValid.value) {
    console.log('[ActionEditor] 유효하지 않은 액션으로 저장 취소', localAction.value)
    return
  }
  
  console.log('[ActionEditor] 액션 저장 시작', {
    localAction: localAction.value,
    actionIndex: props.actionIndex,
    isValid: isValid.value
  })
  
  // ID가 없으면 생성
  if (!localAction.value.id) {
    localAction.value.id = `action-${Date.now()}`
  }
  
  // route_to_connector 액션의 경우 블록명과 커넥터명 추가
  if (localAction.value.type === 'route_to_connector') {
    if (routeType.value === 'self') {
      // 현재 블록 내 커넥터로 이동
      const connector = currentBlockConnectors.value.find(cp => cp.id === localAction.value.parameters.connector_id)
      localAction.value.parameters.target_block_name = 'self'
      localAction.value.parameters.target_connector_name = connector?.name || 'self'
    } else {
      // 다른 블록으로 이동
      const targetBlock = props.allBlocks.find(b => b.id == localAction.value.parameters.target_block_id)
      const targetConnector = targetBlock?.connectionPoints?.find(cp => cp.id === localAction.value.parameters.target_connector_id)
      
      localAction.value.parameters.target_block_name = targetBlock?.name || `블록${localAction.value.parameters.target_block_id}`
      localAction.value.parameters.target_connector_name = targetConnector?.name || 'self'
    }
  }
  
  const finalAction = JSON.parse(JSON.stringify(localAction.value))
  console.log('[ActionEditor] 최종 액션 emit 전송', finalAction)
  emit('save', finalAction)
}

function onKeyDown(event) {
  // Tab 키 처리 - 들여쓰기
  if (event.key === 'Tab') {
    event.preventDefault()
    
    const textarea = event.target
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = textarea.value
    
    if (event.shiftKey) {
      // Shift+Tab: 내어쓰기
      const lineStart = text.lastIndexOf('\n', start - 1) + 1
      const lineEnd = text.indexOf('\n', end)
      const selectedLines = text.substring(lineStart, lineEnd === -1 ? text.length : lineEnd)
      
      // 각 줄의 시작에서 탭 제거
      const unindentedLines = selectedLines.split('\n').map(line => {
        if (line.startsWith('\t')) {
          return line.substring(1)
        } else if (line.startsWith('    ')) { // 4칸 공백
          return line.substring(4)
        }
        return line
      }).join('\n')
      
      const before = text.substring(0, lineStart)
      const after = text.substring(lineEnd === -1 ? text.length : lineEnd)
      
      localAction.value.parameters.script = before + unindentedLines + after
      
      // 커서 위치 조정
      nextTick(() => {
        const removedChars = selectedLines.length - unindentedLines.length
        textarea.selectionStart = Math.max(lineStart, start - Math.min(removedChars, start - lineStart))
        textarea.selectionEnd = Math.max(lineStart, end - removedChars)
      })
    } else {
      // Tab: 들여쓰기
      if (start === end) {
        // 단일 커서: 탭 문자 삽입
        const before = text.substring(0, start)
        const after = text.substring(end)
        
        localAction.value.parameters.script = before + '\t' + after
        
        // 커서 위치 조정
        nextTick(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 1
        })
      } else {
        // 선택된 텍스트: 각 줄의 시작에 탭 추가
        const lineStart = text.lastIndexOf('\n', start - 1) + 1
        const lineEnd = text.indexOf('\n', end)
        const selectedLines = text.substring(lineStart, lineEnd === -1 ? text.length : lineEnd)
        
        // 각 줄의 시작에 탭 추가
        const indentedLines = selectedLines.split('\n').map(line => '\t' + line).join('\n')
        
        const before = text.substring(0, lineStart)
        const after = text.substring(lineEnd === -1 ? text.length : lineEnd)
        
        localAction.value.parameters.script = before + indentedLines + after
        
        // 커서 위치 조정
        nextTick(() => {
          const addedChars = indentedLines.length - selectedLines.length
          textarea.selectionStart = start + (start > lineStart ? 1 : 0)
          textarea.selectionEnd = end + addedChars
        })
      }
    }
  }
  
  // Enter 키 처리 - 자동 들여쓰기
  else if (event.key === 'Enter') {
    event.preventDefault()
    
    const textarea = event.target
    const start = textarea.selectionStart
    const text = textarea.value
    
    // 현재 줄의 들여쓰기 레벨 확인
    const lineStart = text.lastIndexOf('\n', start - 1) + 1
    const currentLine = text.substring(lineStart, start)
    const indent = currentLine.match(/^(\t*)/)[1] // 시작 부분의 탭들
    
    // 새 줄 + 동일한 들여쓰기 적용
    const before = text.substring(0, start)
    const after = text.substring(start)
    
    localAction.value.parameters.script = before + '\n' + indent + after
    
    // 커서 위치 조정
    nextTick(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 1 + indent.length
    })
  }
}

// 초기화
onMounted(() => {
  localAction.value = JSON.parse(JSON.stringify(props.action))
  
  // 기존 액션인지 새 액션인지 확인
  const isExistingAction = props.actionIndex >= 0 && props.action.name
  
  if (isExistingAction) {
    // 기존 액션의 경우 사용자가 이미 이름을 설정했을 수 있음
    userModifiedName.value = !isAutoGeneratedName(props.action.name)
  } else {
    // 새 액션의 경우 자동 이름 생성 허용
    userModifiedName.value = false
  }
  
  // 기존 액션의 라우팅 타입 감지
  if (localAction.value.type === 'route_to_connector') {
    if (localAction.value.parameters?.target_block_id) {
      routeType.value = 'other'
      updateTargetConnectors()
    } else {
      routeType.value = 'self'
    }
  }
  
  // 파라미터가 없으면 기본값 설정
  if (!localAction.value.parameters) {
    handleTypeChange()
  }
  
  // 초기 액션 이름 업데이트 (새 액션이거나 자동 생성 이름인 경우만)
  if (!isExistingAction || isAutoGeneratedName(localAction.value.name)) {
    updateActionName()
  }
  
  // 초기 로딩 완료
  isInitialLoad.value = false
})

// Props 변경 감지
watch(() => props.action, (newAction) => {
  localAction.value = JSON.parse(JSON.stringify(newAction))
}, { deep: true })

// 사용자가 직접 이름을 수정했는지 감지
watch(() => localAction.value.name, (newName, oldName) => {
  if (!isInitialLoad.value && newName !== oldName) {
    // 자동 생성된 이름이 아니고, 초기 로딩이 아닌 경우에만 사용자 수정으로 간주
    if (!isAutoGeneratedName(newName)) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[ActionEditor] 사용자가 직접 이름 수정:', oldName, '->', newName)
      }
      userModifiedName.value = true
    } else if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 자동 생성된 이름으로 변경:', oldName, '->', newName)
      // 자동 생성된 이름으로 변경되는 경우는 사용자 수정이 아님
    }
  }
}, { flush: 'post' }) // DOM 업데이트 후에 실행

// 파라미터 변경 시 사용자 수정 플래그 리셋 (신호 변경 등을 허용하기 위해)
watch(() => localAction.value.parameters, () => {
  if (!isInitialLoad.value) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 파라미터 변경됨, 사용자 수정 플래그 리셋')
    }
    userModifiedName.value = false
  }
  updateActionName()
}, { deep: true, flush: 'post' })

watch(() => localAction.value.type, () => {
  if (!isInitialLoad.value) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 타입 변경됨, 사용자 수정 플래그 리셋')
    }
    userModifiedName.value = false
  }
  updateActionName()
})

// 신호 관련 파라미터 개별 감지
watch(() => localAction.value.parameters?.signal_name, () => {
  updateActionName()
})

watch(() => localAction.value.parameters?.expected_value, () => {
  updateActionName()
})

watch(() => localAction.value.parameters?.value, () => {
  updateActionName()
})

// 라우팅 관련 파라미터 개별 감지
watch(() => localAction.value.parameters?.target_block_id, () => {
  updateActionName()
})

watch(() => localAction.value.parameters?.target_connector_id, () => {
  updateActionName()
})

watch(() => localAction.value.parameters?.connector_id, () => {
  updateActionName()
})

watch(() => routeType.value, () => {
  updateActionName()
})

async function updateActionName() {
  if (process.env.NODE_ENV === 'development') {
    console.log('[ActionEditor] updateActionName 호출됨', {
      type: localAction.value.type,
      parameters: localAction.value.parameters,
      currentName: localAction.value.name,
      userModifiedName: userModifiedName.value,
      isInitialLoad: isInitialLoad.value
    })
  }
  
  if (!localAction.value.type || !localAction.value.parameters) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 타입이나 파라미터가 없어서 종료')
    }
    return
  }
  
  // 강제로 이름 업데이트를 허용하도록 조건 완화
  if (!isInitialLoad.value && userModifiedName.value) {
    // 현재 이름이 자동 생성된 패턴과 맞지 않으면 사용자가 직접 수정한 것으로 간주
    if (!isAutoGeneratedName(localAction.value.name)) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[ActionEditor] 사용자 수정 이름이므로 업데이트 건너뛰기:', localAction.value.name)
      }
      return
    } else {
      // 자동 생성된 패턴이면 업데이트 허용하고 플래그 리셋
      if (process.env.NODE_ENV === 'development') {
        console.log('[ActionEditor] 자동 생성 패턴이므로 업데이트 허용')
      }
      userModifiedName.value = false
    }
  }
  
  const oldName = localAction.value.name
  let newName = ''
  
  switch (localAction.value.type) {
    case 'delay':
      const duration = localAction.value.parameters.duration || '5'
      newName = `딜레이 ${duration}초`
      break
    case 'signal_wait':
      const waitSignal = localAction.value.parameters.signal_name || '신호명'
      const waitValue = localAction.value.parameters.expected_value === true ? 'true' : 'false'
      newName = `${waitSignal} = ${waitValue} 대기`
      break
    case 'signal_update':
      const updateSignal = localAction.value.parameters.signal_name || '신호명'
      const updateValue = localAction.value.parameters.value === true ? 'true' : 'false'
      newName = `${updateSignal} = ${updateValue} 설정`
      break
    case 'signal_check':
      const checkSignal = localAction.value.parameters.signal_name || '신호명'
      const checkValue = localAction.value.parameters.expected_value === true ? 'true' : 'false'
      newName = `${checkSignal} = ${checkValue} 확인`
      break
    case 'route_to_connector':
      if (routeType.value === 'self') {
        const connector = currentBlockConnectors.value.find(cp => cp.id === localAction.value.parameters.connector_id)
        const connectorName = connector?.name || 'self'
        newName = `self.${connectorName}로 이동`
      } else {
        const targetBlock = props.allBlocks.find(b => b.id == localAction.value.parameters.target_block_id)
        const targetConnector = targetBlockConnectors.value.find(cp => cp.id === localAction.value.parameters.target_connector_id)
        const blockName = targetBlock?.name || '블록명'
        const connectorName = targetConnector?.name || '커넥터명'
        newName = `${blockName}.${connectorName}로 이동`
      }
      break
    case 'block_entry':
      const blockName = localAction.value.parameters.target_block_name || '블록명'
      newName = `${blockName} 블록으로 이동`
      break
    case 'conditional_branch':
      newName = '조건부 실행'
      break
    case 'action_jump':
      const targetAction = localAction.value.parameters.target_action_name || '액션명'
      newName = `${targetAction}로 점프`
      break
    case 'custom_sink':
      newName = '제품 배출 처리'
      break
    case 'script':
      newName = '스크립트 실행'
      break
  }
  
  if (newName && newName !== oldName) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 이름 업데이트:', oldName, '->', newName)
    }
    
    // nextTick을 사용하여 DOM 업데이트 후 이름 변경
    await nextTick()
    localAction.value.name = newName
    
    // 강제로 반응성 트리거
    await nextTick()
  } else if (process.env.NODE_ENV === 'development') {
    console.log('[ActionEditor] 이름 변경 없음:', newName)
  }
  
  // 초기 로딩 완료 표시
  if (isInitialLoad.value) {
    isInitialLoad.value = false
    if (process.env.NODE_ENV === 'development') {
      console.log('[ActionEditor] 초기 로딩 완료')
    }
  }
}

function isAutoGeneratedName(name) {
  // 자동 생성된 이름인지 확인하는 패턴들
  const autoPatterns = [
    /^딜레이 .+초$/,
    /^.+ = (true|false) 대기$/,
    /^.+ = (true|false) 설정$/,
    /^.+ = (true|false) 확인$/,
    /^.+로 이동$/,
    /^조건부 실행$/,
    /^.+로 점프$/,
    /^제품 배출 처리$/,
    /^신호명 = /,    // 기본값들도 포함
    /^블록명\./,
    /^액션명으로/
  ]
  
  return autoPatterns.some(pattern => pattern.test(name))
}
</script>

<style scoped>
.action-editor {
  max-width: 500px;
  margin: 0 auto;
}

.action-editor h3 {
  margin: 0 0 20px 0;
  color: #343a40;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #495057;
  font-weight: 500;
  font-size: 14px;
}

.form-input, .form-select, .form-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
  margin-bottom: 10px;
  box-sizing: border-box; /* padding과 border를 포함한 전체 크기 계산 */
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  border-color: #007bff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.form-textarea {
  resize: vertical;
  font-family: 'Courier New', monospace;
  min-height: 120px; /* 최소 높이 설정 */
  line-height: 1.4;
  tab-size: 4; /* 탭 크기 설정 */
  -moz-tab-size: 4;
  white-space: pre-wrap; /* 공백과 탭 보존, 줄바꿈 허용 */
}

.parameters-section {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
}

.parameters-section h4 {
  margin: 0 0 15px 0;
  color: #495057;
  font-size: 16px;
}

.help-text {
  font-size: 12px;
  color: #6c757d;
  margin-top: -5px;
  margin-bottom: 10px;
  line-height: 1.4;
  font-style: italic;
}

.info-text {
  color: #6c757d;
  font-style: italic;
  text-align: center;
  padding: 20px;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.save-btn {
  padding: 8px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.save-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.cancel-btn {
  padding: 8px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style> 
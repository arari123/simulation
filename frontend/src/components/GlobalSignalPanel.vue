<template>
  <div class="global-signal-panel" v-if="isVisible">
    <div class="panel-header">
      <h4>전역 신호 관리</h4>
      <button @click="closePanel" class="close-btn" title="닫기">✖</button>
    </div>
    <div class="panel-content">
      <div class="signal-filter">
        <label for="gsp-signal-filter">신호 검색:</label>
        <input type="text" id="gsp-signal-filter" v-model="filterText" placeholder="이름으로 검색...">
      </div>

      <div class="global-signals-table-container">
        <table class="global-signals-table">
          <thead>
            <tr>
              <th>신호 이름</th>
              <th>현재 값</th>
              <th>동작</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filteredSignals.length === 0">
              <td colspan="3" class="no-signals-message">
                {{ signals.length === 0 ? '생성된 전역 신호가 없습니다.' : '검색 결과가 없습니다.' }}
              </td>
            </tr>
            <tr v-for="signal in filteredSignals" :key="signal.name">
              <td>{{ signal.name }}</td>
              <td>
                <span :class="['signal-value', signal.value ? 'is-true' : 'is-false', 'current-value']">
                  {{ signal.value ? 'TRUE' : 'FALSE' }}
                </span>
                <small class="value-indicator">(실시간)</small>
              </td>
              <td>
                <button @click="editSignal(signal)" class="action-btn edit-btn" title="수정">✏️</button>
                <button @click="toggleSignalValue(signal.name)" class="action-btn toggle-btn" title="값 변경">⇆</button>
                <button @click="removeSignal(signal.name)" class="action-btn delete-btn" title="삭제">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="add-global-signal">
        <h5>새 전역 신호 추가</h5>
        <label for="gsp-newSignalName">신호 이름:</label>
        <input type="text" id="gsp-newSignalName" v-model="newSignal.name" @keyup.enter="addSignal">
        <label for="gsp-newSignalValue">초기 값:</label>
        <select id="gsp-newSignalValue" v-model="newSignal.value">
          <option :value="true">True</option>
          <option :value="false">False</option>
        </select>
        <button @click="addSignal" :disabled="!newSignal.name.trim()">신호 추가</button>
        <small v-if="signalError" class="error-message">{{ signalError }}</small>
      </div>
    </div>

    <!-- 신호 수정 팝업 -->
    <div v-if="showEditPopup" class="edit-popup-overlay" @click.self="closeEditPopup">
      <div class="edit-popup">
        <div class="edit-popup-header">
          <h5>전역 신호 수정</h5>
          <button @click="closeEditPopup" class="close-btn">✖</button>
        </div>
        <div class="edit-popup-content">
          <label for="edit-signal-name">신호 이름:</label>
          <input type="text" id="edit-signal-name" v-model="editingSignal.name">
          
          <label for="edit-signal-value">초기 값:</label>
          <select id="edit-signal-value" v-model="editingSignal.value">
            <option :value="true">True</option>
            <option :value="false">False</option>
          </select>
          
          <div class="edit-popup-actions">
            <button @click="confirmEditSignal" :disabled="!editingSignal.name.trim()">확인</button>
            <button @click="closeEditPopup">취소</button>
          </div>
          
          <small v-if="editError" class="error-message">{{ editError }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  signals: {
    type: Array,
    default: () => []
  },
  isVisible: {
    type: Boolean,
    default: true // 기본적으로 보이도록 설정, App.vue에서 제어
  }
});

const emit = defineEmits(['close-panel', 'add-signal', 'remove-signal', 'update-signal-value', 'edit-signal']);

const newSignal = ref({ name: '', value: true });
const signalError = ref('');
const filterText = ref('');

// 수정 관련 변수들
const showEditPopup = ref(false);
const editingSignal = ref({ name: '', value: true, originalName: '' });
const editError = ref('');

const filteredSignals = computed(() => {
  if (!filterText.value.trim()) {
    return props.signals;
  }
  const lowerFilter = filterText.value.toLowerCase();
  return props.signals.filter(signal => {
    const signalNameLower = signal.name.toLowerCase();
    return signalNameLower.includes(lowerFilter);
  });
});

function closePanel() {
  emit('close-panel');
}

function addSignal() {
  if (!newSignal.value.name.trim()) {
    signalError.value = "신호 이름을 입력해주세요.";
    return;
  }
  if (props.signals.some(s => s.name === newSignal.value.name.trim())) {
    signalError.value = "이미 사용중인 신호 이름입니다.";
    return;
  }
  emit('add-signal', { ...newSignal.value });
  newSignal.value = { name: '', value: true }; // 폼 초기화
  signalError.value = '';
  filterText.value = ''; // 추가 후 필터 초기화
}

function removeSignal(signalName) {
  if (confirm(`전역 신호 '${signalName}'을(를) 삭제하시겠습니까? 이 신호를 사용하는 모든 액션에 영향을 줄 수 있습니다.`)) {
    emit('remove-signal', signalName);
  }
}

function toggleSignalValue(signalName) {
    const signal = props.signals.find(s => s.name === signalName);
    if (signal) {
        emit('update-signal-value', { name: signalName, value: !signal.value });
    }
}

function editSignal(signal) {
  editingSignal.value = {
    name: signal.name,
    value: signal.value,
    originalName: signal.name
  };
  showEditPopup.value = true;
  editError.value = '';
}

function closeEditPopup() {
  showEditPopup.value = false;
  editingSignal.value = { name: '', value: true, originalName: '' };
  editError.value = '';
}

function confirmEditSignal() {
  if (!editingSignal.value.name.trim()) {
    editError.value = "신호 이름을 입력해주세요.";
    return;
  }
  
  // 이름이 변경되었고, 새 이름이 이미 존재하는지 확인
  if (editingSignal.value.name !== editingSignal.value.originalName) {
    if (props.signals.some(s => s.name === editingSignal.value.name.trim())) {
      editError.value = "이미 사용중인 신호 이름입니다.";
      return;
    }
  }
  
  emit('edit-signal', {
    originalName: editingSignal.value.originalName,
    newName: editingSignal.value.name.trim(),
    newValue: editingSignal.value.value
  });
  
  closeEditPopup();
}
</script>

<style scoped>
.global-signal-panel {
  position: fixed;
  top: 60px; /* App 헤더 등이 있다면 조절 */
  right: 10px;
  width: 450px; /* 기존 400px에서 450px로 너비 증가 */
  max-height: calc(100vh - 80px); /* 위아래 여백 고려 */
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 5px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  z-index: 1000; /* 다른 요소들 위에 오도록 */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid #dee2e6;
  background-color: #e9ecef;
}

.panel-header h4 {
  margin: 0;
  font-size: 1.1em;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.2em;
  cursor: pointer;
  padding: 5px;
}

.panel-content {
  padding: 15px;
  overflow-y: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.signal-filter {
  margin-bottom: 15px;
}
.signal-filter label {
  margin-right: 5px;
  font-weight: 500;
}
.signal-filter input[type="text"] {
  padding: 6px 8px;
  border: 1px solid #ccc;
  border-radius: 3px;
  width: calc(100% - 80px); /* 레이블 고려 */
}

.global-signals-table-container {
  flex-grow: 1; /* 테이블 영역이 남은 공간 차지 */
  overflow-y: auto; /* 내용 많을 시 스크롤 */
  margin-bottom: 20px;
  border: 1px solid #dee2e6;
  border-radius: 3px;
}

.global-signals-table {
  width: 100%;
  border-collapse: collapse;
}

.global-signals-table th,
.global-signals-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  font-size: 0.9em;
}

.global-signals-table th {
  background-color: #f2f2f2;
  font-weight: 600;
  position: sticky;
  top: 0; /* 스크롤 시 헤더 고정 */
}

.global-signals-table td.no-signals-message {
    text-align: center;
    color: #777;
    padding: 20px;
}

.signal-value {
  padding: 4px 8px;
  border-radius: 3px;
  font-weight: bold;
  font-size: 0.9em;
}

.signal-value.current-value {
  border: 2px solid #007bff;
  box-shadow: 0 0 5px rgba(0, 123, 255, 0.3);
}

.signal-value.is-true {
  background-color: #d4edda;
  color: #155724;
  border-color: #c3e6cb;
}

.signal-value.is-false {
  background-color: #f8d7da;
  color: #721c24;
  border-color: #f5c6cb;
}

.value-indicator {
  display: block;
  color: #6c757d;
  font-style: italic;
  margin-top: 2px;
}

.action-btn {
  background: none;
  border: 1px solid #ccc;
  border-radius: 3px;
  padding: 4px 8px;
  margin: 0 2px;
  cursor: pointer;
  font-size: 0.9em;
}

.edit-btn {
  color: #007bff;
  border-color: #007bff;
}

.edit-btn:hover {
  background-color: #007bff;
  color: white;
}

.toggle-btn {
  color: #28a745;
  border-color: #28a745;
}

.toggle-btn:hover {
  background-color: #28a745;
  color: white;
}

.delete-btn {
  color: #dc3545;
  border-color: #dc3545;
}

.delete-btn:hover {
  background-color: #dc3545;
  color: white;
}

.add-global-signal {
  margin-top: auto; /* 하단에 위치 */
  padding-top: 15px;
  border-top: 1px solid #dee2e6;
}

.add-global-signal h5 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1em;
  color: #333;
}

.add-global-signal label {
  display: block;
  margin-top: 10px;
  margin-bottom: 3px;
  font-weight: 500;
}

.add-global-signal input[type="text"],
.add-global-signal select {
  width: calc(100% - 12px); /* padding 고려 */
  padding: 6px;
  margin-bottom: 10px;
  border: 1px solid #ccc;
  border-radius: 3px;
  font-size: 0.95em;
}

.add-global-signal button {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background-color: #0d6efd;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  margin-top: 5px;
}
.add-global-signal button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.add-global-signal button:hover:not(:disabled) {
  background-color: #0b5ed7;
}

.error-message {
  color: red;
  font-size: 0.85em;
  display: block;
  margin-top: 5px;
}

/* 수정 팝업 스타일 */
.edit-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.edit-popup {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  width: 400px;
  max-width: 90vw;
}

.edit-popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #dee2e6;
  background-color: #f8f9fa;
  border-radius: 8px 8px 0 0;
}

.edit-popup-header h5 {
  margin: 0;
  font-size: 1.1em;
}

.edit-popup-content {
  padding: 20px;
}

.edit-popup-content label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.edit-popup-content input,
.edit-popup-content select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 15px;
  box-sizing: border-box;
}

.edit-popup-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.edit-popup-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}

.edit-popup-actions button:first-child {
  background-color: #007bff;
  color: white;
}

.edit-popup-actions button:first-child:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.edit-popup-actions button:last-child {
  background-color: #6c757d;
  color: white;
}

.edit-popup-actions button:hover:not(:disabled) {
  opacity: 0.9;
}
</style> 
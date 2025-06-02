<template>
  <!-- 사이드바 모드 -->
  <div v-if="isSidebar" class="sidebar-container">
    <div class="sidebar-header">
      <h3 v-if="connectorInfo">{{ connectorInfo.blockName }}.{{ connectorInfo.connectorName }} - 커넥터 설정</h3>
      <h3 v-else>커넥터 설정</h3>
      <button @click="closePopup" class="close-btn">✕</button>
    </div>
    
    <div class="sidebar-content">
      <div v-if="connectorInfo">
        <!-- 커넥터 이름 편집 -->
        <div class="connector-name-setting">
          <label for="connector-name">커넥터 이름:</label>
          <input type="text" id="connector-name" v-model="editableConnectorName" placeholder="커넥터 이름을 입력하세요" />
        </div>
        
        <!-- 행동 관리 버튼들 -->
        <div class="add-action-section">
          <div class="section-header">
            <button v-if="!addingNewAction" @click="startAddingNewAction('')" class="add-action-btn">+ 행동 추가</button>
            <button @click="openScriptEditor" class="script-editor-btn-small">📝 스크립트 편집기</button>
          </div>
          <div v-if="addingNewAction" class="new-action-form">
            <label for="cp-action-name">행동 이름:</label>
            <input type="text" id="cp-action-name" v-model="newAction.name">
            
            <label for="cp-action-type">행동 타입:</label>
            <select id="cp-action-type" v-model="newAction.type" @change="onNewActionTypeChange">
              <option value="delay">딜레이 (Delay)</option>
              <option value="signal_update">신호 변경 (Signal Update)</option>
              <option value="signal_check">신호 체크 (Signal Check)</option>
              <option value="signal_wait">신호 대기 (Signal Wait)</option>
              <option value="action_jump">행동 이동 (Action Jump)</option>
              <option value="route_to_connector">다음 공정 진행 (Route to Connector)</option>
              <option value="conditional_branch">조건부 실행 (Conditional Branch)</option>
            </select>

            <!-- Delay -->
            <div v-if="newAction.type === 'delay'" class="action-options">
              <label for="cp-delay-duration">지연 시간(초):</label>
              <input type="number" id="cp-delay-duration" v-model.number="newAction.parameters.duration" min="0">
            </div>
            
            <!-- Signal Update -->
            <div v-if="newAction.type === 'signal_update'" class="action-options">
              <label for="cp-signal-update-name">변경할 신호 이름:</label>
              <select id="cp-signal-update-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-update-value">변경할 신호 값:</label>
              <select id="cp-signal-update-value" v-model="newAction.parameters.value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Signal Check -->
            <div v-if="newAction.type === 'signal_check'" class="action-options">
              <label for="cp-signal-check-name">체크할 신호 이름:</label>
              <select id="cp-signal-check-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-check-value">기대 값:</label>
              <select id="cp-signal-check-value" v-model="newAction.parameters.expected_value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Signal Wait -->
            <div v-if="newAction.type === 'signal_wait'" class="action-options">
              <label for="cp-signal-wait-name">대기할 신호 이름:</label>
              <select id="cp-signal-wait-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-wait-value">기대 값:</label>
              <select id="cp-signal-wait-value" v-model="newAction.parameters.expected_value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Action Jump -->
            <div v-if="newAction.type === 'action_jump'" class="action-options">
              <label for="cp-action-jump-target">이동할 행동 이름 (현재 커넥터 내):</label>
              <select id="cp-action-jump-target" v-model="newAction.parameters.target_action_name">
                 <option v-for="act in editableActions.filter(a => a.id !== newAction.id || editingActionIndex === null)" :key="act.id || act.name" :value="act.name">{{act.name}}</option>
              </select>
            </div>

            <!-- Route to Connector -->
            <div v-if="newAction.type === 'route_to_connector'" class="action-options">
              <label for="cp-route-block">대상 블록:</label>
              <select id="cp-route-block" v-model="selectedTargetBlockId" @change="onTargetBlockChange">
                <option :value="null">블록 선택...</option>
                <option :value="connectorInfo.blockId">{{ connectorInfo.blockName }} (현재 블록)</option> 
                <option v-for="block in connectorInfo.availableBlocks.filter(b => b.id !== connectorInfo.blockId)" :key="block.id" :value="block.id">
                    {{ block.name }} (ID: {{ block.id }})
                </option>
              </select>
              <div v-if="selectedTargetBlockId && targetBlockConnectors.length > 0">
                <label for="cp-route-connector">대상 커넥터:</label>
                <select id="cp-route-connector" v-model="newAction.parameters.target_connector_id">
                    <option v-if="parseInt(selectedTargetBlockId) === connectorInfo.blockId" value="self">
                        블록 액션 실행 (self)
                    </option>
                    <option v-for="cp in targetBlockConnectors" :key="cp.id" :value="cp.id">
                        {{ cp.name || cp.id }} ({{ getConnectionPointPosition(cp, getBlockById(selectedTargetBlockId)) }})
                    </option>
                </select>
              </div>
              <small v-else-if="selectedTargetBlockId && targetBlockConnectors.length === 0">선택한 블록에 사용 가능한 커넥터가 없습니다.</small>
              
              <label for="cp-route-delay">공정 이동 딜레이(초):</label>
              <input type="number" id="cp-route-delay" v-model.number="newAction.parameters.delay" min="0">
            </div>

            <!-- Conditional Branch -->
            <div v-if="newAction.type === 'conditional_branch'" class="action-options">
              <div class="conditional-gui-editor">
                <h5>🔀 조건부 실행 편집기</h5>
                
                <!-- 조건 목록 -->
                <div class="conditions-list">
                  <div v-for="(condition, condIndex) in conditionalConditions" :key="condIndex" class="condition-block">
                    <div class="condition-header">
                      <h6>조건 {{ condIndex + 1 }}</h6>
                      <button @click="removeCondition(condIndex)" class="remove-condition-btn" :disabled="conditionalConditions.length <= 1">🗑️</button>
                    </div>
                    
                    <!-- IF 조건 설정 -->
                    <div class="condition-if">
                      <label>IF 조건:</label>
                      <div class="if-condition-row">
                        <select v-model="condition.signal" @change="updateConditionalScript">
                          <option value="">신호 선택...</option>
                          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                        </select>
                        <span>=</span>
                        <select v-model="condition.value" @change="updateConditionalScript">
                          <option :value="true">true</option>
                          <option :value="false">false</option>
                        </select>
                      </div>
                    </div>
                    
                    <!-- THEN 행동들 -->
                    <div class="condition-actions">
                      <label>THEN 실행할 행동들:</label>
                      <div class="action-list">
                        <div v-for="(action, actionIndex) in condition.actions" :key="actionIndex" class="sub-action">
                          <select v-model="action.type" @change="updateSubActionParams(condIndex, actionIndex)">
                            <option value="signal_update">신호 변경</option>
                            <option value="delay">딜레이</option>
                            <option value="route_to_connector">커넥터로 이동</option>
                          </select>
                          
                          <!-- 신호 변경 -->
                          <template v-if="action.type === 'signal_update'">
                            <select v-model="action.signal" @change="updateConditionalScript">
                              <option value="">신호 선택...</option>
                              <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                            </select>
                            <span>=</span>
                            <select v-model="action.value" @change="updateConditionalScript">
                              <option :value="true">true</option>
                              <option :value="false">false</option>
                            </select>
                          </template>
                          
                          <!-- 딜레이 -->
                          <template v-if="action.type === 'delay'">
                            <input type="number" v-model.number="action.duration" @input="updateConditionalScript" min="0" placeholder="초">
                            <span>초</span>
                          </template>
                          
                          <!-- 커넥터로 이동 -->
                          <template v-if="action.type === 'route_to_connector'">
                            <select v-model="action.targetBlock" @change="updateSubActionConnectors(condIndex, actionIndex)">
                              <option value="">블록 선택...</option>
                              <option v-for="block in allBlocks" :key="block.id" :value="block.name">{{ block.name }}</option>
                            </select>
                            <span>.</span>
                            <select v-model="action.targetConnector" @change="updateConditionalScript">
                              <option value="">커넥터 선택...</option>
                              <option v-for="cp in getConnectorsForBlock(action.targetBlock)" :key="cp.id" :value="cp.name || cp.id">{{ cp.name || cp.id }}</option>
                            </select>
                          </template>
                          
                          <button @click="removeSubAction(condIndex, actionIndex)" class="remove-sub-action-btn">🗑️</button>
                        </div>
                        <button @click="addSubAction(condIndex)" class="add-sub-action-btn">+ 행동 추가</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="conditional-controls">
                  <button @click="addCondition" class="add-condition-btn">+ 조건 추가</button>
                  <button type="button" @click="openScriptEditor" class="open-script-editor-btn">📝 스크립트로 편집</button>
                </div>
              </div>
            </div>

            <button @click="confirmAddAction" :disabled="isSignalNameDuplicate && newAction.type === 'signal_create'">확인</button>
            <button @click="cancelAddingNewAction">취소</button>
          </div>
        </div>
        
        <h4>행동 목록</h4>
        <div class="actions-list-container">
          <div v-if="!editableActions || editableActions.length === 0" class="no-actions">
            정의된 행동이 없습니다. "행동 추가" 버튼을 눌러 새 행동을 만드세요.
          </div>
          <ul v-else class="actions-list">
            <li v-for="(action, index) in editableActions" :key="action.id || index" class="action-item">
              <div class="action-header">
                <div class="action-info">
                  <span class="action-icon">{{ getActionTypeIcon(action.type) }}</span>
                  <div class="action-details">
                    <div class="action-name">{{ action.name }}</div>
                    <div class="action-type-badge" :class="getActionTypeClass(action.type)">
                      {{ getActionTypeDisplayName(action.type) }}
                    </div>
                  </div>
                </div>
                <div>
                  <button @click="editAction(index)" class="action-btn edit-btn" title="수정">✏️</button>
                  <button @click="moveAction(index, -1)" :disabled="index === 0" class="action-btn move-btn move-up-btn" title="위로">⬆️</button>
                  <button @click="moveAction(index, 1)" :disabled="index === editableActions.length - 1" class="action-btn move-btn move-down-btn" title="아래로">⬇️</button>
                  <button @click="deleteAction(index)" class="action-btn delete-btn" title="삭제">🗑️</button>
                </div>
              </div>
              <div class="action-parameters">
                <div v-if="Object.keys(action.parameters || {}).length > 0" class="parameter-list">
                  <!-- 조건부 실행인 경우 특별한 미리보기 -->
                  <div v-if="action.type === 'conditional_branch'" class="conditional-preview">
                    <div v-for="(line, lineIndex) in (action.parameters.script || '').split('\n').slice(0, 5)" :key="lineIndex" class="conditional-line">
                      <span v-if="line.trim().startsWith('if ')" class="script-if">{{ line.trim() }}</span>
                      <span v-else-if="line.startsWith('\t')" class="script-sub-action">
                        <span class="indent-marker">┗━</span> {{ line.trim() }}
                      </span>
                      <span v-else-if="line.trim()">{{ line.trim() }}</span>
                    </div>
                    <div v-if="(action.parameters.script || '').split('\n').length > 5" style="color: #6c757d; font-style: italic;">
                      ... ({{ (action.parameters.script || '').split('\n').length - 5 }}개 줄 더)
                    </div>
                  </div>
                  <!-- 일반 파라미터 -->
                  <div v-for="(value, key) in action.parameters" :key="key" v-show="!(action.type === 'conditional_branch' && key === 'script')" class="parameter-item">
                    <span class="parameter-key">{{ key }}:</span>
                    <span class="parameter-value">{{ formatParameterValue(key, value) }}</span>
                  </div>
                </div>
                <div v-else class="no-parameters">파라미터 없음</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <div v-else>
        <p>선택된 커넥터가 없습니다.</p>
      </div>
    </div>
    
    <div class="sidebar-actions">
      <button @click="closePopup">닫기</button>
    </div>
  </div>
  
  <!-- 팝업 모드 (기존 코드) -->
  <div v-else class="popup-overlay" @click.self="closePopup">
    <div class="popup connector-settings-popup">
      <h3 v-if="connectorInfo">
        {{ connectorInfo.blockName }} - 커넥터 [{{ currentConnectorName }}] 설정
      </h3>
      <h3 v-else>커넥터 설정</h3>
      
      <div v-if="connectorInfo && editableActions !== null">
        <div class="connector-name-edit">
          <label for="connector-name-input">커넥터 이름:</label>
          <input type="text" id="connector-name-input" v-model="currentConnectorName" @blur="onConnectorNameBlur">
        </div>

        <h4>행동 목록</h4>
        <div v-if="!editableActions || editableActions.length === 0" class="no-actions">
          정의된 행동이 없습니다. "행동 추가" 버튼을 눌러 새 행동을 만드세요.
        </div>
        <ul v-else class="actions-list">
          <li v-for="(action, index) in editableActions" :key="action.id || index" class="action-item">
            <div class="action-header">
              <div class="action-info">
                <span class="action-icon">{{ getActionTypeIcon(action.type) }}</span>
                <div class="action-details">
                  <div class="action-name">{{ action.name }}</div>
                  <div class="action-type-badge" :class="getActionTypeClass(action.type)">
                    {{ getActionTypeDisplayName(action.type) }}
                  </div>
                </div>
              </div>
              <div>
                <button @click="editAction(index)" class="action-btn edit-btn" title="수정">✏️</button>
                <button @click="moveAction(index, -1)" :disabled="index === 0" class="action-btn move-btn move-up-btn" title="위로">⬆️</button>
                <button @click="moveAction(index, 1)" :disabled="index === editableActions.length - 1" class="action-btn move-btn move-down-btn" title="아래로">⬇️</button>
                <button @click="deleteAction(index)" class="action-btn delete-btn" title="삭제">🗑️</button>
              </div>
            </div>
            <div class="action-parameters">
              <div v-if="Object.keys(action.parameters || {}).length > 0" class="parameter-list">
                <!-- 조건부 실행인 경우 특별한 미리보기 -->
                <div v-if="action.type === 'conditional_branch'" class="conditional-preview">
                  <div v-for="(line, lineIndex) in (action.parameters.script || '').split('\n').slice(0, 5)" :key="lineIndex" class="conditional-line">
                    <span v-if="line.trim().startsWith('if ')" class="script-if">{{ line.trim() }}</span>
                    <span v-else-if="line.startsWith('\t')" class="script-sub-action">
                      <span class="indent-marker">┗━</span> {{ line.trim() }}
                    </span>
                    <span v-else-if="line.trim()">{{ line.trim() }}</span>
                  </div>
                  <div v-if="(action.parameters.script || '').split('\n').length > 5" style="color: #6c757d; font-style: italic;">
                    ... ({{ (action.parameters.script || '').split('\n').length - 5 }}개 줄 더)
                  </div>
                </div>
                <!-- 일반 파라미터 -->
                <div v-for="(value, key) in action.parameters" :key="key" v-show="!(action.type === 'conditional_branch' && key === 'script')" class="parameter-item">
                  <span class="parameter-key">{{ key }}:</span>
                  <span class="parameter-value">{{ formatParameterValue(key, value) }}</span>
                </div>
              </div>
              <div v-else class="no-parameters">파라미터 없음</div>
            </div>
          </li>
        </ul>

        <div class="add-action-section">
          <div class="section-header">
            <button @click="openScriptEditor" class="script-editor-btn-small">📝 스크립트 편집기</button>
          </div>
          <div v-if="!addingNewAction">
            <button @click="startAddingNewAction('')">+ 행동 추가</button>
          </div>
          <div v-if="addingNewAction" class="new-action-form">
            <label for="cp-action-name">행동 이름:</label>
            <input type="text" id="cp-action-name" v-model="newAction.name">
            
            <label for="cp-action-type">행동 타입:</label>
            <select id="cp-action-type" v-model="newAction.type" @change="onNewActionTypeChange">
              <option value="delay">딜레이 (Delay)</option>
              <option value="signal_update">신호 변경 (Signal Update)</option>
              <option value="signal_check">신호 체크 (Signal Check)</option>
              <option value="signal_wait">신호 대기 (Signal Wait)</option>
              <option value="action_jump">행동 이동 (Action Jump)</option>
              <option value="route_to_connector">다음 공정 진행 (Route to Connector)</option>
              <option value="conditional_branch">조건부 실행 (Conditional Branch)</option>
            </select>

            <!-- Delay -->
            <div v-if="newAction.type === 'delay'" class="action-options">
              <label for="cp-delay-duration">지연 시간(초):</label>
              <input type="number" id="cp-delay-duration" v-model.number="newAction.parameters.duration" min="0">
            </div>
            
            <!-- Signal Update -->
            <div v-if="newAction.type === 'signal_update'" class="action-options">
              <label for="cp-signal-update-name">변경할 신호 이름:</label>
              <select id="cp-signal-update-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-update-value">변경할 신호 값:</label>
              <select id="cp-signal-update-value" v-model="newAction.parameters.value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Signal Check -->
            <div v-if="newAction.type === 'signal_check'" class="action-options">
              <label for="cp-signal-check-name">체크할 신호 이름:</label>
              <select id="cp-signal-check-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-check-value">기대 값:</label>
              <select id="cp-signal-check-value" v-model="newAction.parameters.expected_value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Signal Wait -->
            <div v-if="newAction.type === 'signal_wait'" class="action-options">
              <label for="cp-signal-wait-name">대기할 신호 이름:</label>
              <select id="cp-signal-wait-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>신호 선택...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-wait-value">기대 값:</label>
              <select id="cp-signal-wait-value" v-model="newAction.parameters.expected_value">
                <option :value="true">참 (True)</option>
                <option :value="false">거짓 (False)</option>
              </select>
            </div>

            <!-- Action Jump -->
            <div v-if="newAction.type === 'action_jump'" class="action-options">
              <label for="cp-action-jump-target">이동할 행동 이름 (현재 커넥터 내):</label>
              <select id="cp-action-jump-target" v-model="newAction.parameters.target_action_name">
                 <option v-for="act in editableActions.filter(a => a.id !== newAction.id || editingActionIndex === null)" :key="act.id || act.name" :value="act.name">{{act.name}}</option>
              </select>
            </div>

            <!-- Route to Connector -->
            <div v-if="newAction.type === 'route_to_connector'" class="action-options">
              <label for="cp-route-block">대상 블록:</label>
              <select id="cp-route-block" v-model="selectedTargetBlockId" @change="onTargetBlockChange">
                <option :value="null">블록 선택...</option>
                <option :value="connectorInfo.blockId">{{ connectorInfo.blockName }} (현재 블록)</option> 
                <option v-for="block in connectorInfo.availableBlocks.filter(b => b.id !== connectorInfo.blockId)" :key="block.id" :value="block.id">
                    {{ block.name }} (ID: {{ block.id }})
                </option>
              </select>
              <div v-if="selectedTargetBlockId && targetBlockConnectors.length > 0">
                <label for="cp-route-connector">대상 커넥터:</label>
                <select id="cp-route-connector" v-model="newAction.parameters.target_connector_id">
                    <option v-if="parseInt(selectedTargetBlockId) === connectorInfo.blockId" value="self">
                        블록 액션 실행 (self)
                    </option>
                    <option v-for="cp in targetBlockConnectors" :key="cp.id" :value="cp.id">
                        {{ cp.name || cp.id }} ({{ getConnectionPointPosition(cp, getBlockById(selectedTargetBlockId)) }})
                    </option>
                </select>
              </div>
              <small v-else-if="selectedTargetBlockId && targetBlockConnectors.length === 0">선택한 블록에 사용 가능한 커넥터가 없습니다.</small>
              
              <label for="cp-route-delay">공정 이동 딜레이(초):</label>
              <input type="number" id="cp-route-delay" v-model.number="newAction.parameters.delay" min="0">
            </div>

            <!-- Conditional Branch -->
            <div v-if="newAction.type === 'conditional_branch'" class="action-options">
              <div class="conditional-gui-editor">
                <h5>🔀 조건부 실행 편집기</h5>
                
                <!-- 조건 목록 -->
                <div class="conditions-list">
                  <div v-for="(condition, condIndex) in conditionalConditions" :key="condIndex" class="condition-block">
                    <div class="condition-header">
                      <h6>조건 {{ condIndex + 1 }}</h6>
                      <button @click="removeCondition(condIndex)" class="remove-condition-btn" :disabled="conditionalConditions.length <= 1">🗑️</button>
                    </div>
                    
                    <!-- IF 조건 설정 -->
                    <div class="condition-if">
                      <label>IF 조건:</label>
                      <div class="if-condition-row">
                        <select v-model="condition.signal" @change="updateConditionalScript">
                          <option value="">신호 선택...</option>
                          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                        </select>
                        <span>=</span>
                        <select v-model="condition.value" @change="updateConditionalScript">
                          <option :value="true">true</option>
                          <option :value="false">false</option>
                        </select>
                      </div>
                    </div>
                    
                    <!-- THEN 행동들 -->
                    <div class="condition-actions">
                      <label>THEN 실행할 행동들:</label>
                      <div class="action-list">
                        <div v-for="(action, actionIndex) in condition.actions" :key="actionIndex" class="sub-action">
                          <select v-model="action.type" @change="updateSubActionParams(condIndex, actionIndex)">
                            <option value="signal_update">신호 변경</option>
                            <option value="delay">딜레이</option>
                            <option value="route_to_connector">커넥터로 이동</option>
                          </select>
                          
                          <!-- 신호 변경 -->
                          <template v-if="action.type === 'signal_update'">
                            <select v-model="action.signal" @change="updateConditionalScript">
                              <option value="">신호 선택...</option>
                              <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                            </select>
                            <span>=</span>
                            <select v-model="action.value" @change="updateConditionalScript">
                              <option :value="true">true</option>
                              <option :value="false">false</option>
                            </select>
                          </template>
                          
                          <!-- 딜레이 -->
                          <template v-if="action.type === 'delay'">
                            <input type="number" v-model.number="action.duration" @input="updateConditionalScript" min="0" placeholder="초">
                            <span>초</span>
                          </template>
                          
                          <!-- 커넥터로 이동 -->
                          <template v-if="action.type === 'route_to_connector'">
                            <select v-model="action.targetBlock" @change="updateSubActionConnectors(condIndex, actionIndex)">
                              <option value="">블록 선택...</option>
                              <option v-for="block in allBlocks" :key="block.id" :value="block.name">{{ block.name }}</option>
                            </select>
                            <span>.</span>
                            <select v-model="action.targetConnector" @change="updateConditionalScript">
                              <option value="">커넥터 선택...</option>
                              <option v-for="cp in getConnectorsForBlock(action.targetBlock)" :key="cp.id" :value="cp.name || cp.id">{{ cp.name || cp.id }}</option>
                            </select>
                          </template>
                          
                          <button @click="removeSubAction(condIndex, actionIndex)" class="remove-sub-action-btn">🗑️</button>
                        </div>
                        <button @click="addSubAction(condIndex)" class="add-sub-action-btn">+ 행동 추가</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="conditional-controls">
                  <button @click="addCondition" class="add-condition-btn">+ 조건 추가</button>
                  <button type="button" @click="openScriptEditor" class="open-script-editor-btn">📝 스크립트로 편집</button>
                </div>
              </div>
            </div>

            <button @click="confirmAddAction" :disabled="isSignalNameDuplicate && newAction.type === 'signal_create'">확인</button>
            <button @click="cancelAddingNewAction">취소</button>
          </div>
        </div>

      </div>
      <div v-else>
        <p>선택된 커넥터 정보가 없습니다.</p>
      </div>

      <div class="popup-actions">
        <button @click="closePopup">닫기</button>
      </div>
    </div>
  </div>

  <!-- 스크립트 편집기 팝업 - 완전히 독립된 최상위 레벨 -->
  <div v-if="showScriptEditor" class="script-editor-overlay" @click.self="closeScriptEditor">
    <div class="script-editor-popup">
      <div class="script-editor-header">
        <h3>📝 커넥터 스크립트 편집기</h3>
        <button @click="closeScriptEditor" class="close-btn">✕</button>
      </div>
      
      <div class="script-editor-content">
        <div class="script-help">
          <h5>📋 문법 가이드:</h5>
          <div class="script-examples">
            <span class="script-command">delay</span> <span class="script-value">5</span> - 5초 딜레이<br>
            <span class="script-command">if</span> <span class="script-variable">공정1 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span> - 신호 값 체크<br>
            <span class="script-command">wait</span> <span class="script-variable">공정2 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span> - 신호가 값이 될 때까지 대기<br>
            <span class="script-variable">공정1 load enable</span> <span class="script-operator">=</span> <span class="script-value">false</span> - 신호 값 변경<br>
            <span class="script-command">go to</span> <span class="script-value">self.unload</span> - 현재 블록의 커넥터로 이동<br>
            <span class="script-command">go to</span> <span class="script-variable">배출</span>.<span class="script-value">load</span> - 다른 블록의 커넥터로 이동<br>
            <span class="script-command">jump to</span> <span class="script-value">2</span> - 2번째 행동으로 이동<br>
            <br><strong>🔀 조건부 실행:</strong><br>
            <span class="script-command">if</span> <span class="script-variable">공정1 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span><br>
            &nbsp;&nbsp;&nbsp;&nbsp;<span class="script-variable">공정1 load enable</span> <span class="script-operator">=</span> <span class="script-value">false</span><br>
            &nbsp;&nbsp;&nbsp;&nbsp;<span class="script-command">go to</span> <span class="script-variable">공정1</span>.<span class="script-value">LOAD</span><br>
            <span class="script-comment">// 이것은 주석입니다</span> - 주석 처리
          </div>
          
          <!-- 사용 가능한 신호 목록 -->
          <div class="available-items">
            <h6>🔗 사용 가능한 신호:</h6>
            <div class="item-list">
              <span v-for="signal in allSignals" :key="signal" class="item-tag signal-tag">{{ signal }}</span>
              <span v-if="allSignals.length === 0" class="no-items">정의된 신호가 없습니다</span>
            </div>
          </div>
          
          <!-- 사용 가능한 블록 목록 -->
          <div class="available-items">
            <h6>📦 사용 가능한 블록:</h6>
            <div class="item-list">
              <div v-for="block in allBlocks" :key="block.id" class="block-info">
                <span class="item-tag block-tag">{{ block.name }}</span>
                <span class="connector-list">
                  커넥터: 
                  <span v-for="cp in block.connectionPoints" :key="cp.id" class="item-tag connector-tag">{{ cp.name || cp.id }}</span>
                  <span v-if="!block.connectionPoints || block.connectionPoints.length === 0">없음</span>
                </span>
              </div>
              <span v-if="allBlocks.length === 0" class="no-items">정의된 블록이 없습니다</span>
            </div>
          </div>
        </div>
        
        <div class="script-input-section">
          <label for="script-editor-input-connector">스크립트 입력:</label>
          <div class="script-editor-container">
            <div class="line-numbers" ref="lineNumbers">
              <div v-for="lineNum in scriptLineCount" :key="lineNum" class="line-number">
                {{ lineNum }}
              </div>
            </div>
            <textarea 
              id="script-editor-input-connector" 
              v-model="scriptInput" 
              placeholder="// 스크립트를 입력하세요"
              rows="25"
              class="script-editor-textarea"
              @scroll="syncLineNumbersScroll"
              @input="updateLineNumbers"
              @keydown="handleScriptKeydown"
              ref="scriptTextarea"
            ></textarea>
          </div>
          
          <!-- 실시간 유효성 검사 결과 표시 -->
          <div v-if="scriptValidationWarnings.length > 0" class="script-warnings">
            <h6>⚠️ 검사 결과:</h6>
            <div v-for="warning in scriptValidationWarnings" :key="warning" class="warning-item">
              {{ warning }}
            </div>
          </div>
        </div>
      </div>
      
      <div class="script-editor-actions">
        <button @click="parseAndAddScript" :disabled="!scriptInput.trim() || scriptValidationWarnings.length > 0" class="apply-script-btn">스크립트 적용</button>
        <button @click="closeScriptEditor">취소</button>
      </div>
      
      <div v-if="scriptParseError" class="script-error">
        ❌ {{ scriptParseError }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';

const props = defineProps({
  connectorInfo: {
    type: Object,
    default: null
  },
  allSignals: {
    type: Array,
    default: () => []
  },
  allBlocks: {
    type: Array,
    default: () => []
  },
  isSidebar: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close-popup', 'save-connector-settings']);

const editableActions = ref([]);
const addingNewAction = ref(false);
const newActionTemplate = () => ({
  id: `cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
  name: '새 커넥터 행동',
  type: 'delay', 
  parameters: {}
});
const newAction = ref(newActionTemplate());
const editingActionIndex = ref(null); 

const selectedTargetBlockId = ref(null); // "다음 공정 진행" 시 대상 블록 ID
const isSignalNameDuplicate = ref(false);
const currentConnectorName = ref(''); // 커넥터 이름 편집용
const editableConnectorName = ref(''); // 편집 가능한 커넥터 이름

// 스크립트 편집기 관련 변수들 추가
const showScriptEditor = ref(false);
const scriptInput = ref('');
const scriptParseError = ref(null);
const scriptValidationWarnings = ref([]);
const scriptLineCount = ref(1);
const lineNumbers = ref(null);
const scriptTextarea = ref(null);

// 조건부 실행 GUI 편집기를 위한 변수들
const conditionalConditions = ref([]);

// 무한 루프 방지를 위한 플래그
let isInitializingConnector = false;

watch(() => props.connectorInfo, (newInfo) => {
  isInitializingConnector = true; // 초기화 시작
  
  if (newInfo) {
    editableActions.value = JSON.parse(JSON.stringify(newInfo.actions || []));
    currentConnectorName.value = newInfo.connectorName || newInfo.connectorId; // 초기 이름 설정
    editableConnectorName.value = newInfo.connectorName || newInfo.connectorId; // 편집 가능한 이름 설정
  } else {
    editableActions.value = [];
    currentConnectorName.value = '';
    editableConnectorName.value = '';
  }
  addingNewAction.value = false;
  editingActionIndex.value = null;
  selectedTargetBlockId.value = null;
  
  // 다음 틱에서 초기화 완료
  setTimeout(() => {
    isInitializingConnector = false;
  }, 0);
}, { immediate: true, deep: true });

const actionTypeDisplayNames = {
  delay: '딜레이',
  signal_update: '신호 변경',
  signal_check: '신호 체크',
  signal_wait: '신호 대기',
  action_jump: '행동 이동',
  route_to_connector: '다음 공정 진행',
  conditional_branch: '조건부 실행'
};

function getActionTypeDisplayName(type) {
  return actionTypeDisplayNames[type] || type;
}

function getActionTypeIcon(type) {
  const icons = {
    delay: '⏱️',
    signal_update: '🔄',
    signal_check: '🔍',
    signal_wait: '⏳',
    action_jump: '↪️',
    route_to_connector: '🔗',
    conditional_branch: '🔀'
  };
  return icons[type] || '❓';
}

function getActionTypeClass(type) {
  const classes = {
    delay: 'badge-delay',
    signal_update: 'badge-signal-update',
    signal_check: 'badge-signal-check',
    signal_wait: 'badge-signal-wait',
    action_jump: 'badge-action-jump',
    route_to_connector: 'badge-route',
    conditional_branch: 'badge-conditional'
  };
  return classes[type] || 'badge-default';
}

function formatParameterValue(key, value) {
  if (key === 'target_block_id') {
    const targetBlock = props.allBlocks.find(b => b.id == value);
    return targetBlock ? targetBlock.name : `블록${value}`;
  }
  if (key === 'target_connector_id') {
    if (value === 'self') return '블록 액션';
    // 커넥터 이름 찾기 로직은 복잡하므로 일단 ID 그대로 표시
    return value;
  }
  if (key === 'signal_name') {
    return value;
  }
  if (key === 'expected_value' || key === 'value') {
    return value ? '참(true)' : '거짓(false)';
  }
  if (key === 'duration' || key === 'delay') {
    return `${value}초`;
  }
  if (key === 'script') {
    // 스크립트는 첫 번째 줄만 미리보기로 표시
    const firstLine = value.split('\n')[0];
    return firstLine.length > 30 ? firstLine.substring(0, 30) + '...' : firstLine;
  }
  return value;
}

function formatParameters(params) {
    if (!params || Object.keys(params).length === 0) return '없음';
    let parts = [];
    if (params.target_block_id && params.target_connector_id) {
        const targetBlock = props.allBlocks.find(b => b.id === parseInt(params.target_block_id));
        let targetText = `대상: ${targetBlock ? targetBlock.name : '알 수 없는 블록'}`;
        if (parseInt(params.target_block_id) === props.connectorInfo?.blockId) {
             targetText += ` (자신) -> 블록 행동`;
        } else {
            targetText += `.${params.target_connector_id}`;
        }
       
        if (params.delay !== undefined) {
            targetText += `, 딜레이: ${params.delay}s`;
        }
        parts.push(targetText);
        Object.entries(params).forEach(([key, value]) => {
            if (key !== 'target_block_id' && key !== 'target_connector_id' && key !== 'delay') {
                parts.push(`${key}: ${value}`);
            }
        });
    } else {
        Object.entries(params).forEach(([key, value]) => {
          parts.push(`${key}: ${value}`);
        });
    }
    return parts.join(', ');
}

function startAddingNewAction(type = 'delay') {
  newAction.value = newActionTemplate();
  newAction.value.type = type;
  editingActionIndex.value = null;
  addingNewAction.value = true;
  selectedTargetBlockId.value = null; // 대상 블록 선택 초기화
  onNewActionTypeChange(); 
}

function cancelAddingNewAction() {
  addingNewAction.value = false;
  editingActionIndex.value = null;
  isSignalNameDuplicate.value = false;
}

function onNewActionTypeChange() {
    const type = newAction.value.type;
    const oldParams = JSON.parse(JSON.stringify(newAction.value.parameters));
    newAction.value.parameters = {}; 
    
    if (type === 'delay') newAction.value.parameters.duration = oldParams.duration || 1;
    if (type === 'signal_update') {
        newAction.value.parameters.signal_name = oldParams.signal_name || (props.allSignals.length > 0 ? props.allSignals[0] : '');
        newAction.value.parameters.value = oldParams.hasOwnProperty('value') ? oldParams.value : true;
    }
    if (type === 'signal_check') {
        newAction.value.parameters.signal_name = oldParams.signal_name || (props.allSignals.length > 0 ? props.allSignals[0] : '');
        newAction.value.parameters.expected_value = oldParams.hasOwnProperty('expected_value') ? oldParams.expected_value : true;
    }
    if (type === 'signal_wait') {
        newAction.value.parameters.signal_name = oldParams.signal_name || (props.allSignals.length > 0 ? props.allSignals[0] : '');
        newAction.value.parameters.expected_value = oldParams.hasOwnProperty('expected_value') ? oldParams.expected_value : true;
    }
    if (type === 'action_jump' && editableActions.value.length > 0) {
        const validActions = editableActions.value.filter(a => editingActionIndex.value === null || a.id !== editableActions.value[editingActionIndex.value].id);
        newAction.value.parameters.target_action_name = oldParams.target_action_name || (validActions.length > 0 ? validActions[0].name : null);
    }
    if (type === 'route_to_connector') {
        selectedTargetBlockId.value = oldParams.target_block_id || null;
        newAction.value.parameters.target_block_id = oldParams.target_block_id || null;
        newAction.value.parameters.target_connector_id = oldParams.target_connector_id || null;
        newAction.value.parameters.delay = oldParams.delay || 0;

        if (selectedTargetBlockId.value) {
            if (parseInt(selectedTargetBlockId.value) === props.connectorInfo.blockId) {
                 const selfBlock = props.allBlocks.find(b => b.id === parseInt(selectedTargetBlockId.value));
                 if (selfBlock && selfBlock.connectionPoints && selfBlock.connectionPoints.length > 0) {
                     if (!newAction.value.parameters.target_connector_id || 
                         !selfBlock.connectionPoints.find(cp => cp.id === newAction.value.parameters.target_connector_id)) {
                     }
                 }
            } else if (targetBlockConnectors.value.length > 0) {
                 if (!targetBlockConnectors.value.find(cp => cp.id === newAction.value.parameters.target_connector_id)) {
                    newAction.value.parameters.target_connector_id = targetBlockConnectors.value[0].id;
                 }
            }
        }
    }
    if (type === 'conditional_branch') {
        // GUI 편집기 초기화
        if (oldParams.script) {
            parseScriptToGUI(oldParams.script);
        } else {
            initializeConditionalGUI();
        }
        updateConditionalScript();
    }
}

function validateSignalName() {
    if (newAction.value.type === 'signal_create' && newAction.value.parameters.signal_name) {
        const currentSignalName = (editingActionIndex.value !== null && 
                                   props.connectorInfo.actions[editingActionIndex.value].type === 'signal_create' && 
                                   props.connectorInfo.actions[editingActionIndex.value].parameters.signal_name === newAction.value.parameters.signal_name)
                               ? newAction.value.parameters.signal_name
                               : null;

        if (newAction.value.parameters.signal_name === currentSignalName) {
            isSignalNameDuplicate.value = false;
        } else {
            isSignalNameDuplicate.value = props.allSignals.includes(newAction.value.parameters.signal_name);
        }
    } else {
        isSignalNameDuplicate.value = false;
    }
}

// 자동 저장 함수
let autoSaveTimeout = null;

function autoSave() {
  if (props.connectorInfo) {
    emit('save-connector-settings', 
      props.connectorInfo.blockId, 
      props.connectorInfo.connectorId, 
      JSON.parse(JSON.stringify(editableActions.value)),
      currentConnectorName.value.trim()
    );
  }
}

function debouncedAutoSave() {
  clearTimeout(autoSaveTimeout);
  autoSaveTimeout = setTimeout(() => {
    autoSave();
  }, 1000); // 1초 디바운스
}

function confirmAddAction() {
  if (!newAction.value.name.trim()) {
    alert('행동 이름을 입력해주세요.');
    return;
  }
  if (newAction.value.type === 'signal_create' && isSignalNameDuplicate.value) {
    alert('이미 사용 중인 신호 이름입니다. 다른 이름을 사용해주세요.');
    return;
  }
  if (newAction.value.type === 'signal_update' && !newAction.value.parameters.signal_name) {
    alert('변경할 신호를 선택해주세요.');
    return;
  }
  if (newAction.value.type === 'route_to_connector') {
      if (!selectedTargetBlockId.value || !newAction.value.parameters.target_connector_id) {
          alert('다음 공정 진행을 위해서는 대상 블록과 커넥터를 모두 선택해야 합니다.');
          return;
      }
      newAction.value.parameters.target_block_id = selectedTargetBlockId.value;
  }

  const actionToAdd = JSON.parse(JSON.stringify(newAction.value));
  if (editingActionIndex.value !== null) {
    editableActions.value.splice(editingActionIndex.value, 1, actionToAdd);
  } else {
    editableActions.value.push(actionToAdd);
  }
  
  // 디바운스된 자동 저장
  debouncedAutoSave();
  
  cancelAddingNewAction();
}

function editAction(index) {
    const actionToEdit = JSON.parse(JSON.stringify(editableActions.value[index]));
    newAction.value = actionToEdit;
    editingActionIndex.value = index;
    addingNewAction.value = true;

    if (actionToEdit.type === 'route_to_connector') {
        selectedTargetBlockId.value = actionToEdit.parameters.target_block_id || null;
    } else {
        selectedTargetBlockId.value = null;
    }
    onNewActionTypeChange();
    if (actionToEdit.type === 'signal_create') {
        validateSignalName();
    }
}

function deleteAction(index) {
  if (confirm(`'${editableActions.value[index].name}' 행동을 삭제하시겠습니까?`)) {
    editableActions.value.splice(index, 1);
    // 디바운스된 자동 저장
    debouncedAutoSave();
  }
}

function moveAction(index, direction) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= editableActions.value.length) return;
  const item = editableActions.value.splice(index, 1)[0];
  editableActions.value.splice(newIndex, 0, item);
  // 디바운스된 자동 저장
  debouncedAutoSave();
}

const targetBlockConnectors = computed(() => {
  if (!selectedTargetBlockId.value || !props.allBlocks) return [];
  const targetBlock = props.allBlocks.find(b => b.id === parseInt(selectedTargetBlockId.value));
  return targetBlock ? (targetBlock.connectionPoints || []) : [];
});

function onTargetBlockChange() {
    newAction.value.parameters.target_block_id = selectedTargetBlockId.value;
    if (targetBlockConnectors.value.length > 0) {
        newAction.value.parameters.target_connector_id = targetBlockConnectors.value[0].id; // 첫 번째 커넥터로 기본 설정
    } else {
        newAction.value.parameters.target_connector_id = null;
    }
}
function getBlockById(blockId) {
    return props.allBlocks.find(b => b.id === blockId);
}

function getConnectionPointPosition(cp, block) {
    if (!cp || !block) return '';
    if (cp.x > block.width * 0.75 ) return `오른쪽 (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.x < block.width * 0.25 ) return `왼쪽 (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.y > block.height * 0.75 ) return `아래쪽 (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.y < block.height * 0.25 ) return `위쪽 (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    return `(${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
}

function closePopup() {
  emit('close-popup');
}

function onConnectorNameBlur() {
  // 필요시 이름 유효성 검사 등 추가 가능
  if (!currentConnectorName.value.trim()) {
    // alert("커넥터 이름은 비워둘 수 없습니다.");
    // currentConnectorName.value = props.connectorInfo?.connectorId || 'default'; // 기본값으로 복원
  }
}

function saveAndClose() {
  if (props.connectorInfo) {
    emit('save-connector-settings', 
      props.connectorInfo.blockId, 
      props.connectorInfo.connectorId, 
      JSON.parse(JSON.stringify(editableActions.value)),
      currentConnectorName.value.trim() // 커넥터 이름도 함께 전달
    );
  }
  closePopup();
}

function openScriptEditor() {
  console.log("[ConnectorSettingsPopup] openScriptEditor 호출됨");
  console.log("[ConnectorSettingsPopup] 현재 showScriptEditor.value:", showScriptEditor.value);
  showScriptEditor.value = true;
  console.log("[ConnectorSettingsPopup] showScriptEditor.value 설정 후:", showScriptEditor.value);
  // 스크립트 편집기 열면 자동으로 현재 설정 불러오기
  loadCurrentActionsAsScript();
}

function closeScriptEditor() {
  showScriptEditor.value = false;
}

function loadCurrentActionsAsScript() {
  try {
    const scriptLines = [];
    
    if (editableActions.value && editableActions.value.length > 0) {
      editableActions.value.forEach((action, index) => {
        const scriptLine = convertActionToScript(action, index + 1);
        if (scriptLine) {
          scriptLines.push(scriptLine);
        }
      });
    } else {
      // 행동이 없을 때는 빈 스크립트로 설정
      scriptLines.push('// 설정된 행동이 없습니다');
    }
    
    scriptInput.value = scriptLines.join('\n');
    console.log("커넥터 현재 설정이 스크립트로 변환되었습니다.");
    
  } catch (error) {
    console.error("커넥터 설정을 스크립트로 변환하는 중 오류:", error);
    scriptParseError.value = `변환 오류: ${error.message}`;
  }
}

function convertActionToScript(action, lineNumber) {
  if (!action || !action.type) {
    return `// 행동 ${lineNumber}: 타입이 정의되지 않음`;
  }
  
  try {
    switch (action.type) {
      case 'delay':
        const duration = action.parameters?.duration || 3;
        return `delay ${duration}`;
        
      case 'signal_check':
        const checkSignal = action.parameters?.signal_name || '신호명';
        const expectedValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `if ${checkSignal} = ${expectedValue}`;
        
      case 'signal_wait':
        const waitSignal = action.parameters?.signal_name || '신호명';
        const waitValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `wait ${waitSignal} = ${waitValue}`;
        
      case 'signal_update':
        const updateSignal = action.parameters?.signal_name || '신호명';
        const newValue = action.parameters?.value === true ? 'true' : 'false';
        return `${updateSignal} = ${newValue}`;
        
      case 'route_to_connector':
        if (action.parameters?.target_block_id && action.parameters?.target_connector_id) {
          // 다른 블록으로 이동
          const targetBlockId = action.parameters.target_block_id;
          const targetConnectorId = action.parameters.target_connector_id;
          const delay = action.parameters?.delay || 0;
          
          // 블록 ID로 블록 이름 찾기
          const targetBlock = props.allBlocks.find(b => b.id == targetBlockId);
          const blockName = targetBlock ? targetBlock.name : `블록${targetBlockId}`;
          
          // 'self' 특별 처리 - 현재 블록의 커넥터로 이동
          if (targetConnectorId === 'self') {
            return delay > 0 ? `go to self.${blockName},${delay}` : `go to self.${blockName}`;
          } else {
            // 커넥터 ID로 커넥터 이름 찾기
            const targetConnector = targetBlock?.connectionPoints?.find(cp => cp.id === targetConnectorId);
            const connectorName = targetConnector?.name || targetConnectorId;
            
            return delay > 0 ? `go to ${blockName}.${connectorName},${delay}` : `go to ${blockName}.${connectorName}`;
          }
        } else if (action.parameters?.connector_id) {
          // 현재 블록 내 커넥터로 이동
          const connectorId = action.parameters.connector_id;
          const connector = props.connectorInfo?.connectionPoints?.find(cp => cp.id === connectorId);
          const connectorName = connector?.name || connectorId;
          const delay = action.parameters?.delay || 0;
          return delay > 0 ? `go to self.${connectorName},${delay}` : `go to self.${connectorName}`;
        } else {
          return `// go to 대상이 명확하지 않음`;
        }
        
      case 'action_jump':
        const targetActionName = action.parameters?.target_action_name;
        if (targetActionName) {
          // 타겟 액션의 인덱스 찾기
          const targetIndex = editableActions.value.findIndex(a => a.name === targetActionName);
          if (targetIndex !== -1) {
            return `jump to ${targetIndex + 1}`;
          } else {
            return `// jump to ${targetActionName} (대상을 찾을 수 없음)`;
          }
        } else {
          return `// jump to 대상이 정의되지 않음`;
        }
        
      case 'conditional_branch':
        const script = action.parameters?.script || '';
        if (script.trim()) {
          // 조건부 실행 스크립트를 탭이 포함된 형태로 반환
          return script.split('\n').map(line => {
            // 이미 탭이 있는 경우 그대로, 없는 경우 탭 추가 여부 판단
            if (line.trim().startsWith('if ')) {
              return line.trim(); // if 문은 탭 없이
            } else if (line.trim() && !line.trim().startsWith('//')) {
              return line.startsWith('\t') ? line : '\t' + line.trim(); // 일반 명령은 탭 추가
            }
            return line; // 빈 줄이나 주석은 그대로
          }).join('\n');
        } else {
          return `// 조건부 실행 스크립트가 정의되지 않음`;
        }
        
      default:
        return `// ${action.type} 타입은 스크립트 변환을 지원하지 않음`;
    }
  } catch (error) {
    console.error(`커넥터 액션 변환 오류 (행동 ${lineNumber}):`, error);
    return `// 행동 ${lineNumber}: 변환 오류 - ${action.name || '이름없음'}`;
  }
}

function clearScript() {
  scriptInput.value = '';
  scriptParseError.value = null;
  scriptValidationWarnings.value = [];
}

function parseAndAddScript() {
  try {
    scriptParseError.value = null;
    const parsedActions = parseAdvancedScript(scriptInput.value);
    
    // 기존 행동을 유지하지 않고 스크립트 내용으로 전체 교체
    editableActions.value = parsedActions;
    
    // 디바운스된 자동 저장
    debouncedAutoSave();
    
    showScriptEditor.value = false; // 스크립트 편집기 닫기
    console.log(`${parsedActions.length}개의 커넥터 행동이 스크립트로부터 적용되었습니다.`);
    
    if (parsedActions.length === 0) {
      console.log("스크립트가 비어있어 모든 커넥터 행동이 제거되었습니다.");
    }
    
  } catch (error) {
    scriptParseError.value = `스크립트 파싱 오류: ${error.message}`;
    console.error("Connector Script parsing error:", error);
  }
}

// 고급 스크립트 파싱 (조건부 실행 지원)
function parseAdvancedScript(scriptText) {
  const lines = scriptText.split('\n');
  const parsedActions = [];
  let i = 0;
  
  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    // 빈 줄이나 주석은 건너뛰기
    if (!trimmedLine || trimmedLine.startsWith('//')) {
      i++;
      continue;
    }
    
    // 조건부 실행 감지
    if (trimmedLine.startsWith('if ') && !line.startsWith('\t')) {
      // 조건부 실행 블록 파싱
      const { action, nextIndex } = parseConditionalBranch(lines, i);
      if (action) {
        parsedActions.push(action);
      }
      i = nextIndex;
    } else if (!line.startsWith('\t')) {
      // 일반 액션 파싱
      try {
        const action = parseScriptLine(trimmedLine, i + 1);
        if (action) {
          parsedActions.push(action);
        }
      } catch (error) {
        throw new Error(`라인 ${i + 1}: ${error.message}`);
      }
      i++;
    } else {
      // 탭으로 시작하는 줄은 조건부 실행 내부여야 함
      throw new Error(`라인 ${i + 1}: 탭으로 시작하는 줄이 조건부 실행 밖에 있습니다.`);
    }
  }
  
  return parsedActions;
}

// 조건부 실행 블록 파싱
function parseConditionalBranch(lines, startIndex) {
  const conditionalScript = [];
  let i = startIndex;
  
  // 연속된 if 블록들을 모두 수집
  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    // 빈 줄이나 주석은 건너뛰기
    if (!trimmedLine || trimmedLine.startsWith('//')) {
      i++;
      continue;
    }
    
    // if 블록이 아니면 종료
    if (!trimmedLine.startsWith('if ') || line.startsWith('\t')) {
      break;
    }
    
    // if 조건 추가
    conditionalScript.push(line);
    i++;
    
    // 해당 if에 속하는 탭 들여쓰기 줄들 수집
    while (i < lines.length) {
      const subLine = lines[i];
      const subTrimmedLine = subLine.trim();
      
      // 빈 줄이나 주석은 건너뛰기
      if (!subTrimmedLine || subTrimmedLine.startsWith('//')) {
        i++;
        continue;
      }
      
      // 탭으로 시작하지 않으면 이 if 블록 종료
      if (!subLine.startsWith('\t')) {
        break;
      }
      
      conditionalScript.push(subLine);
      i++;
    }
  }
  
  if (conditionalScript.length === 0) {
    return { action: null, nextIndex: i };
  }
  
  // 조건부 실행 액션 생성
  const action = {
    id: `script-cp-conditional-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    name: `조건부 실행 (${conditionalScript.filter(line => line.trim().startsWith('if ')).length}개 조건)`,
    type: 'conditional_branch',
    parameters: {
      script: conditionalScript.join('\n')
    }
  };
  
  return { action, nextIndex: i };
}

function parseScriptLine(line, lineNumber) {
  // delay 명령어 파싱
  if (line.startsWith('delay ')) {
    const duration = parseFloat(line.replace('delay ', ''));
    if (isNaN(duration)) {
      throw new Error(`라인 ${lineNumber}: delay 값이 숫자가 아닙니다.`);
    }
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `딜레이 ${duration}초`,
      type: 'delay',
      parameters: { duration }
    };
  }
  
  // wait 명령어 파싱 (신호가 특정 값이 될 때까지 대기)
  if (line.startsWith('wait ')) {
    const match = line.match(/^wait\s+(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`라인 ${lineNumber}: wait 문법이 잘못되었습니다. 예: wait 신호명 = true`);
    }
    const [, signalName, expectedValue] = match;
    const cleanSignalName = signalName.trim();
    
    // 신호명 유효성 검사
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`라인 ${lineNumber}: 신호 '${cleanSignalName}'이 존재하지 않습니다. 사용 가능한 신호: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} = ${expectedValue} 까지 대기`,
      type: 'signal_wait',
      parameters: { 
        signal_name: cleanSignalName, 
        expected_value: expectedValue === 'true' 
      }
    };
  }
  
  // if 명령어 파싱 (신호 체크)
  if (line.startsWith('if ')) {
    const match = line.match(/^if\s+(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`라인 ${lineNumber}: if 문법이 잘못되었습니다. 예: if 신호명 = true`);
    }
    const [, signalName, expectedValue] = match;
    const cleanSignalName = signalName.trim();
    
    // 신호명 유효성 검사
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`라인 ${lineNumber}: 신호 '${cleanSignalName}'이 존재하지 않습니다. 사용 가능한 신호: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} 체크`,
      type: 'signal_check',
      parameters: { 
        signal_name: cleanSignalName, 
        expected_value: expectedValue === 'true' 
      }
    };
  }
  
  // 신호 변경 파싱 (신호명 = 값)
  if (line.includes(' = ')) {
    const match = line.match(/^(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`라인 ${lineNumber}: 신호 변경 문법이 잘못되었습니다. 예: 신호명 = true`);
    }
    const [, signalName, value] = match;
    const cleanSignalName = signalName.trim();
    
    // 신호명 유효성 검사
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`라인 ${lineNumber}: 신호 '${cleanSignalName}'이 존재하지 않습니다. 사용 가능한 신호: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} 변경`,
      type: 'signal_update',
      parameters: { 
        signal_name: cleanSignalName, 
        value: value === 'true' 
      }
    };
  }
  
  // go to 명령어 파싱
  if (line.startsWith('go to ')) {
    const target = line.replace('go to ', '').trim();
    let targetPath = target;
    let delay = 0;
    
    // 딜레이가 포함된 경우 파싱 (go to 배출.load,3)
    if (target.includes(',')) {
      const parts = target.split(',');
      targetPath = parts[0].trim();
      const delayStr = parts[1].trim();
      delay = parseFloat(delayStr);
      if (isNaN(delay)) {
        throw new Error(`라인 ${lineNumber}: 딜레이 값이 숫자가 아닙니다: ${delayStr}`);
      }
    }
    
    if (targetPath.startsWith('self.')) {
      // self.블록명 형태 - 연결점에서 블록의 액션으로 이동
      const blockName = targetPath.replace('self.', '').trim();
      
      // 블록 찾기 (이름으로)
      const targetBlock = props.allBlocks.find(block => 
        block.name.toLowerCase() === blockName.toLowerCase()
      );
      
      if (!targetBlock) {
        const availableBlocks = props.allBlocks.map(b => b.name).join(', ');
        throw new Error(`라인 ${lineNumber}: 블록 '${blockName}'을 찾을 수 없습니다. 사용 가능한 블록: ${availableBlocks}`);
      }
      
      return {
        id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        name: `${blockName} 블록 액션으로 이동`,
        type: 'route_to_connector',
        parameters: { 
          target_block_id: targetBlock.id,
          target_connector_id: 'self',
          delay: delay
        }
      };
    } else if (targetPath.includes('.')) {
      // 블록이름.연결점이름 형태
      const [blockName, connectorName] = targetPath.split('.');
      const cleanBlockName = blockName.trim();
      const cleanConnectorName = connectorName.trim();
      
      // 블록 찾기 (이름으로)
      const targetBlock = props.allBlocks.find(block => 
        block.name.toLowerCase() === cleanBlockName.toLowerCase()
      );
      
      if (!targetBlock) {
        const availableBlocks = props.allBlocks.map(b => b.name).join(', ');
        throw new Error(`라인 ${lineNumber}: 블록 '${cleanBlockName}'을 찾을 수 없습니다. 사용 가능한 블록: ${availableBlocks}`);
      }
      
      // 연결점 찾기 (이름으로)
      const targetConnector = targetBlock.connectionPoints?.find(cp => 
        cp.name?.toLowerCase() === cleanConnectorName.toLowerCase()
      );
      
      if (!targetConnector) {
        const availableConnectors = targetBlock.connectionPoints?.map(cp => cp.name || cp.id).join(', ') || '없음';
        throw new Error(`라인 ${lineNumber}: 블록 '${cleanBlockName}'에서 연결점 '${cleanConnectorName}'을 찾을 수 없습니다. 사용 가능한 연결점: ${availableConnectors}`);
      }
      
      return {
        id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        name: delay > 0 ? `${cleanBlockName}의 ${cleanConnectorName}로 이동 (${delay}초 딜레이)` : `${cleanBlockName}의 ${cleanConnectorName}로 이동`,
        type: 'route_to_connector',
        parameters: { 
          target_block_id: targetBlock.id,
          target_connector_id: targetConnector.id,
          delay: delay
        }
      };
    } else {
      throw new Error(`라인 ${lineNumber}: go to 대상이 잘못되었습니다. 예: 'go to 배출.load' 또는 'go to self.공정1' 또는 'go to 배출.load,3'`);
    }
  }
  
  // jump to 명령어 파싱
  if (line.startsWith('jump to ')) {
    const targetLine = parseInt(line.replace('jump to ', ''));
    if (isNaN(targetLine)) {
      throw new Error(`라인 ${lineNumber}: jump to 값이 숫자가 아닙니다.`);
    }
    
    if (targetLine < 1 || targetLine > editableActions.value.length) {
      throw new Error(`라인 ${lineNumber}: jump to 대상 행동 번호가 범위를 벗어났습니다. (1-${editableActions.value.length})`);
    }
    
    // 현재 존재하는 액션 중에서 targetLine번째 액션의 이름을 찾아야 함
    const targetAction = editableActions.value[targetLine - 1];
    const targetActionName = targetAction ? targetAction.name : `행동 ${targetLine}`;
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${targetActionName}으로 이동`,
      type: 'action_jump',
      parameters: { 
        target_action_name: targetActionName
      }
    };
  }
  
  throw new Error(`라인 ${lineNumber}: 인식할 수 없는 명령어입니다: ${line}`);
}

// 스크립트 실시간 유효성 검사
function validateScriptInput() {
  scriptValidationWarnings.value = [];
  
  if (!scriptInput.value.trim()) {
    return;
  }
  
  try {
    const parsedActions = parseAdvancedScript(scriptInput.value);
    // 성공적으로 파싱되면 경고 없음
  } catch (error) {
    scriptValidationWarnings.value.push(error.message);
  }
}

// 행 번호 업데이트 함수
function updateLineNumbers() {
  const lines = scriptInput.value.split('\n');
  scriptLineCount.value = Math.max(lines.length, 1);
}

// 행 번호와 텍스트 영역 스크롤 동기화
function syncLineNumbersScroll() {
  if (lineNumbers.value && scriptTextarea.value) {
    lineNumbers.value.scrollTop = scriptTextarea.value.scrollTop;
  }
}

// 스크립트 편집기를 열 때 행 번호 초기화
watch(showScriptEditor, (newValue) => {
  if (newValue) {
    updateLineNumbers();
  }
});

function handleScriptKeydown(event) {
  if (event.key === 'Tab') {
    event.preventDefault();
    const textarea = event.target;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    
    // 현재 값 가져오기
    const currentValue = scriptInput.value;
    const newValue = currentValue.substring(0, start) + '\t' + currentValue.substring(end);
    
    // Vue의 반응성을 통해 값 업데이트
    scriptInput.value = newValue;
    
    // 다음 프레임에서 커서 위치 설정
    setTimeout(() => {
      textarea.setSelectionRange(start + 1, start + 1);
      textarea.focus();
    }, 0);
  }
}

// =============== 조건부 실행 GUI 편집기 함수들 ===============

// 조건부 실행 GUI 초기화
function initializeConditionalGUI() {
  conditionalConditions.value = [
    {
      signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
      value: true,
      actions: [
        {
          type: 'signal_update',
          signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
          value: false
        }
      ]
    }
  ];
}

// 스크립트를 GUI 형태로 파싱
function parseScriptToGUI(script) {
  try {
    const conditions = [];
    const lines = script.split('\n');
    let i = 0;
    
    while (i < lines.length) {
      const line = lines[i].trim();
      
      // if 문 찾기
      if (line.startsWith('if ')) {
        const ifMatch = line.match(/^if\s+(.+?)\s*=\s*(true|false)$/);
        if (ifMatch) {
          const [, signal, value] = ifMatch;
          const condition = {
            signal: signal.trim(),
            value: value === 'true',
            actions: []
          };
          
          // 해당 if의 하위 액션들 찾기
          i++;
          while (i < lines.length && lines[i].startsWith('\t')) {
            const subLine = lines[i].trim();
            
            if (subLine.includes(' = ')) {
              // 신호 변경
              const signalMatch = subLine.match(/^(.+?)\s*=\s*(true|false)$/);
              if (signalMatch) {
                condition.actions.push({
                  type: 'signal_update',
                  signal: signalMatch[1].trim(),
                  value: signalMatch[2] === 'true'
                });
              }
            } else if (subLine.startsWith('delay ')) {
              // 딜레이
              const duration = parseInt(subLine.replace('delay ', ''));
              condition.actions.push({
                type: 'delay',
                duration: duration
              });
            } else if (subLine.startsWith('go to ')) {
              // 커넥터로 이동
              const target = subLine.replace('go to ', '').trim();
              if (target.includes('.')) {
                const [blockName, connectorName] = target.split('.');
                condition.actions.push({
                  type: 'route_to_connector',
                  targetBlock: blockName.trim(),
                  targetConnector: connectorName.trim()
                });
              }
            }
            i++;
          }
          
          conditions.push(condition);
          continue;
        }
      }
      i++;
    }
    
    conditionalConditions.value = conditions.length > 0 ? conditions : [
      {
        signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
        value: true,
        actions: []
      }
    ];
  } catch (error) {
    console.error('스크립트 파싱 오류:', error);
    initializeConditionalGUI();
  }
}

// GUI에서 스크립트로 변환
function updateConditionalScript() {
  const scriptLines = [];
  
  conditionalConditions.value.forEach(condition => {
    if (condition.signal) {
      scriptLines.push(`if ${condition.signal} = ${condition.value ? 'true' : 'false'}`);
      
      condition.actions.forEach(action => {
        if (action.type === 'signal_update' && action.signal) {
          scriptLines.push(`\t${action.signal} = ${action.value ? 'true' : 'false'}`);
        } else if (action.type === 'delay' && action.duration) {
          scriptLines.push(`\tdelay ${action.duration}`);
        } else if (action.type === 'route_to_connector' && action.targetBlock && action.targetConnector) {
          scriptLines.push(`\tgo to ${action.targetBlock}.${action.targetConnector}`);
        }
      });
    }
  });
  
  newAction.value.parameters.script = scriptLines.join('\n');
}

// 조건 추가
function addCondition() {
  conditionalConditions.value.push({
    signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
    value: true,
    actions: [
      {
        type: 'signal_update',
        signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
        value: false
      }
    ]
  });
  updateConditionalScript();
}

// 조건 제거
function removeCondition(index) {
  if (conditionalConditions.value.length > 1) {
    conditionalConditions.value.splice(index, 1);
    updateConditionalScript();
  }
}

// 하위 액션 추가
function addSubAction(conditionIndex) {
  conditionalConditions.value[conditionIndex].actions.push({
    type: 'signal_update',
    signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
    value: false
  });
  updateConditionalScript();
}

// 하위 액션 제거
function removeSubAction(conditionIndex, actionIndex) {
  conditionalConditions.value[conditionIndex].actions.splice(actionIndex, 1);
  updateConditionalScript();
}

// 하위 액션 타입 변경 시 파라미터 초기화
function updateSubActionParams(conditionIndex, actionIndex) {
  const action = conditionalConditions.value[conditionIndex].actions[actionIndex];
  
  if (action.type === 'signal_update') {
    action.signal = props.allSignals.length > 0 ? props.allSignals[0] : '';
    action.value = false;
    delete action.duration;
    delete action.targetBlock;
    delete action.targetConnector;
  } else if (action.type === 'delay') {
    action.duration = 1;
    delete action.signal;
    delete action.value;
    delete action.targetBlock;
    delete action.targetConnector;
  } else if (action.type === 'route_to_connector') {
    action.targetBlock = props.allBlocks.length > 0 ? props.allBlocks[0].name : '';
    action.targetConnector = '';
    delete action.signal;
    delete action.value;
    delete action.duration;
  }
  
  updateConditionalScript();
}

// 블록에 따른 커넥터 목록 가져오기 (ConnectorSettingsPopup용)
function getConnectorsForBlock(blockName) {
  if (!blockName) return [];
  const block = props.allBlocks.find(b => b.name === blockName);
  return block ? (block.connectionPoints || []) : [];
}

// 하위 액션의 커넥터 목록 업데이트
function updateSubActionConnectors(conditionIndex, actionIndex) {
  const action = conditionalConditions.value[conditionIndex].actions[actionIndex];
  const connectors = getConnectorsForBlock(action.targetBlock);
  if (connectors.length > 0) {
    action.targetConnector = connectors[0].name || connectors[0].id;
  } else {
    action.targetConnector = '';
  }
  updateConditionalScript();
}

// 커넥터 이름 변경 감지하여 자동 저장
watch(currentConnectorName, () => {
  if (!isInitializingConnector) {
    debouncedAutoSave();
  }
}, { flush: 'sync' });

// scriptInput 변경 시 실시간 검사
watch(scriptInput, () => {
  validateScriptInput();
});

.actions-list-scrollable {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
}

.actions-list-container {
  flex: 1;
  overflow: hidden; /* 스크롤은 actions-list에서 처리 */
  display: flex;
  flex-direction: column;
}

.action-item {
</script>

<style scoped>
/* BlockSettingsPopup.vue와 유사한 스타일 사용 가능 */
.connector-settings-popup {
  width: 650px; /* 너비 약간 증가 */
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.connector-settings-popup h3, .connector-settings-popup h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.actions-list {
  list-style: none;
  padding: 0;
  max-height: 250px; 
  overflow-y: auto; 
  border: 1px solid #eee;
  margin-bottom: 15px;
}

.action-item {
  padding: 10px;
  border-bottom: 1px solid #eee;
  background-color: #fafafa;
  border-radius: 6px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.action-item:hover {
  background-color: #f0f0f0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.action-item:last-child {
  border-bottom: none;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.action-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-icon {
  font-size: 1.2em;
  width: 24px;
  text-align: center;
  color: #495057;
}

.action-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.action-name {
  font-weight: bold;
  color: #333;
  font-size: 0.95em;
}

.action-type-badge {
  font-size: 0.75em;
  padding: 2px 6px;
  border-radius: 12px;
  color: white;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-delay {
  background-color: #6c757d;
}

.badge-signal-update {
  background-color: #28a745;
}

.badge-signal-check {
  background-color: #007bff;
}

.badge-action-jump {
  background-color: #ffc107;
  color: #212529;
}

.badge-route {
  background-color: #dc3545;
}

.badge-conditional {
  background-color: #ff6b6b;
}

.badge-default {
  background-color: #6c757d;
}

.action-parameters {
  margin-top: 8px;
}

.parameter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.parameter-item {
  background-color: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  border: 1px solid #dee2e6;
}

.parameter-key {
  color: #495057;
  font-weight: 500;
  margin-right: 4px;
}

.parameter-value {
  color: #007bff;
  font-weight: 600;
}

.no-parameters {
  color: #6c757d;
  font-style: italic;
  font-size: 0.85em;
}

.action-btn {
  padding: 3px 6px;
  font-size: 0.9em;
  margin-left: 5px;
  border: 1px solid #ccc;
  background-color: #f0f0f0;
  cursor: pointer;
}
.action-btn:hover {
  background-color: #e0e0e0;
}
.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.move-up-btn { background-color: #c3e6cb; }
.move-up-btn:hover { background-color: #b1d6bb; }
.move-down-btn { background-color: #f5c6cb; }
.move-down-btn:hover { background-color: #e4b5ba; }


.add-action-section {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.new-action-form label {
  display: block;
  margin-top: 10px;
  margin-bottom: 3px;
  font-weight: bold;
}

.new-action-form input[type="text"],
.new-action-form input[type="number"],
.new-action-form select {
  width: calc(100% - 16px); 
  padding: 6px;
  margin-bottom: 10px;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.new-action-form .action-options {
  padding-left: 15px;
  border-left: 2px solid #f0f0f0;
  margin-top: 5px;
  margin-bottom: 10px;
}
.new-action-form .action-options label {
    font-weight: normal;
    margin-top: 5px;
}


.new-action-form button {
  margin-right: 10px;
  padding: 8px 12px;
}

.no-actions {
  padding: 15px;
  text-align: center;
  color: #777;
  border: 1px dashed #ddd;
  margin-bottom: 15px;
}

.popup-actions {
  margin-top: auto; 
  padding-top: 15px;
  border-top: 1px solid #eee;
  text-align: right;
}
.popup-actions button {
    margin-left: 10px;
}
.error-message {
    color: red;
    font-size: 0.8em;
}

.connector-name-edit {
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}
.connector-name-edit label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
.connector-name-edit input {
  width: calc(100% - 12px);
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.script-editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999999; /* 매우 높은 z-index로 설정 */
}

.script-editor-popup {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 95vw;
  max-width: 1400px;
  height: 90vh;
  max-height: 1000px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.script-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.script-editor-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5em;
  cursor: pointer;
  color: #666;
}

.close-btn:hover {
  color: #000;
}

.script-editor-content {
  flex: 1;
  display: flex;
  gap: 20px;
  overflow: hidden;
}

.script-help {
  flex: 0 0 350px;
  overflow-y: auto;
  padding-right: 10px;
  border-right: 1px solid #eee;
}

.script-help h5 {
  margin-top: 0;
  margin-bottom: 10px;
}

.script-examples {
  margin-bottom: 10px;
}

.script-examples span {
  font-weight: bold;
}

.available-items {
  margin-top: 10px;
  margin-bottom: 10px;
}

.available-items h6 {
  margin-top: 0;
  margin-bottom: 10px;
}

.item-list {
  margin-top: 5px;
  margin-bottom: 5px;
}

.item-tag {
  padding: 2px 5px;
  border: 1px solid #ccc;
  border-radius: 3px;
  margin-right: 5px;
  font-size: 0.8em;
  background-color: #f8f9fa;
}

.signal-tag {
  background-color: #e3f2fd;
  border-color: #2196f3;
  color: #1976d2;
}

.block-tag {
  background-color: #e8f5e8;
  border-color: #4caf50;
  color: #2e7d32;
}

.connector-tag {
  background-color: #fff3e0;
  border-color: #ff9800;
  color: #f57c00;
  font-size: 0.7em;
}

.no-items {
  color: #777;
  font-size: 0.8em;
}

.block-info {
  margin-bottom: 5px;
}

.connector-list {
  margin-left: 5px;
}

.script-input-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.script-input-section label {
  display: block;
  margin-bottom: 5px;
}

.script-editor-container {
  position: relative;
  display: flex;
  border: 1px solid #ccc;
  border-radius: 5px;
  overflow: hidden;
  background-color: #fafafa;
}

.line-numbers {
  background-color: #f8f9fa;
  border-right: 1px solid #dee2e6;
  padding: 10px 8px 10px 10px;
  color: #999;
  font-size: 14px;
  font-family: 'Courier New', monospace;
  line-height: 1.4;
  text-align: right;
  user-select: none;
  overflow: hidden;
}

.line-number {
  height: 1.4em;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.script-editor-textarea {
  flex: 1;
  padding: 10px;
  border: none;
  outline: none;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.4;
  resize: none;
  background-color: #fafafa;
  overflow-y: auto;
  overflow-x: auto;
}

.script-warnings {
  margin-bottom: 10px;
}

.script-warnings h6 {
  margin-top: 0;
  margin-bottom: 5px;
}

.warning-item {
  color: red;
  font-size: 0.8em;
  margin-top: 5px;
}

.script-editor-actions {
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px solid #eee;
  text-align: right;
}

.script-editor-actions button {
  margin-left: 10px;
  padding: 8px 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}

.apply-script-btn {
  background-color: #28a745 !important;
  color: white !important;
  border-color: #28a745 !important;
}

.apply-script-btn:hover {
  background-color: #218838 !important;
}

.apply-script-btn:disabled {
  background-color: #6c757d !important;
  border-color: #6c757d !important;
  cursor: not-allowed;
}

.script-error {
  color: red;
  font-size: 0.8em;
}

/* 구문 강조 스타일 */
.script-command {
  color: #0066cc; /* 파란색 - 명령어 */
  font-weight: bold;
}

.script-variable {
  color: #cc6600; /* 주황색 - 변수/신호명/블록명 */
  font-weight: normal;
}

.script-variable-valid {
  color: #009900; /* 녹색 - 유효한 변수/신호명/블록명 */
  font-weight: normal;
}

.script-variable-invalid {
  color: #cc0000; /* 빨간색 - 유효하지 않은 변수 */
  font-weight: normal;
  text-decoration: underline;
}

.script-value {
  color: #009900; /* 녹색 - 값/숫자/연결점명 */
  font-weight: normal;
}

.script-operator {
  color: #cc0066; /* 자주색 - 연산자 */
  font-weight: bold;
}

.script-comment {
  color: #808080; /* 회색 - 주석 */
  font-style: italic;
}

/* 공통 스타일 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  gap: 10px;
}

.add-action-btn {
  padding: 8px 16px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.add-action-btn:hover {
  background-color: #218838;
}

.script-editor-btn-small {
  padding: 6px 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}

.script-editor-btn-small:hover {
  background-color: #0056b3;
}

/* 조건부 실행 스타일 */
.conditional-script-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  resize: vertical;
  min-height: 120px;
  tab-size: 4;
  white-space: pre;
  background-color: #f8f9fa;
}

.conditional-script-textarea:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

/* 조건부 실행 액션 아이템 특별 스타일 */
.action-item.conditional-branch {
  border-left: 4px solid #ff6b6b;
  background: linear-gradient(135deg, #ffe6e6 0%, #fafafa 100%);
}

.conditional-preview {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 8px;
  margin-top: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #495057;
  white-space: pre-wrap;
  max-height: 80px;
  overflow-y: auto;
}

.conditional-preview .script-if {
  color: #007bff;
  font-weight: bold;
}

.conditional-preview .script-tab {
  color: #6c757d;
}

.badge-signal-wait {
  background-color: #ffc107;
  color: #212529;
}

.conditional-line {
  margin-bottom: 2px;
}

.script-sub-action {
  color: #6c757d;
  margin-left: 10px;
}

.indent-marker {
  color: #007bff;
  font-weight: bold;
  margin-right: 5px;
}

.conditional-branch-info {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 3px;
  background-color: #f9f9f9;
}

.conditional-example {
  margin-top: 5px;
  margin-bottom: 10px;
}

.open-script-editor-btn {
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 8px 12px;
}

.open-script-editor-btn:hover {
  background-color: #5a6268;
}

.conditional-gui-editor {
  margin-top: 15px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.conditions-list {
  margin-bottom: 15px;
}

.condition-block {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.condition-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.condition-if {
  margin-bottom: 5px;
}

.if-condition-row {
  display: flex;
  align-items: center;
  gap: 5px;
}

.remove-condition-btn {
  background: none;
  border: none;
  font-size: 1em;
  cursor: pointer;
  color: #6c757d;
}

.remove-condition-btn:hover {
  color: #dc3545;
}

.condition-actions {
  margin-top: 5px;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sub-action {
  display: flex;
  align-items: center;
  gap: 5px;
}

.add-sub-action-btn {
  background: none;
  border: none;
  font-size: 0.9em;
  cursor: pointer;
  color: #28a745;
}

.add-sub-action-btn:hover {
  text-decoration: underline;
}

.add-condition-btn {
  background: none;
  border: none;
  font-size: 0.9em;
  cursor: pointer;
  color: #007bff;
}

.add-condition-btn:hover {
  text-decoration: underline;
}

.remove-sub-action-btn {
  background: none;
  border: none;
  font-size: 1em;
  cursor: pointer;
  color: #dc3545;
}

.remove-sub-action-btn:hover {
  color: #6c757d;
}

.update-sub-action-params {
  display: flex;
  align-items: center;
  gap: 5px;
}

.update-sub-action-params select,
.update-sub-action-params input[type="number"] {
  width: 100px;
}

.update-sub-action-params span {
  font-weight: bold;
}

.update-sub-action-connectors {
  display: flex;
  align-items: center;
  gap: 5px;
}

.update-sub-action-connectors select {
  width: 150px;
}

.update-sub-action-connectors span {
  font-weight: bold;
}

.sidebar-container {
  width: 100%;
  height: 100%;
  background-color: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #eee;
  background-color: #f8f9fa;
  min-height: 60px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #495057;
}

.sidebar-content {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-actions {
  padding: 15px;
  border-top: 1px solid #eee;
  background-color: #f8f9fa;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.sidebar-actions button {
  padding: 6px 12px;
  font-size: 0.9em;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.2em;
  cursor: pointer;
  color: #666;
  padding: 5px;
}

.close-btn:hover {
  color: #000;
}

.connector-name-setting {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 3px;
  background-color: #f9f9f9;
}

.connector-name-setting label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.connector-name-setting input {
  width: calc(100% - 16px);
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.actions-list-scrollable {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
}

.actions-list-container {
  flex: 1;
  overflow: hidden; /* 스크롤은 actions-list에서 처리 */
  display: flex;
  flex-direction: column;
}

.action-item {
</style> 
<template>
  <!-- ?¨Ïù¥?úÎ∞î Î™®Îìú -->
  <div v-if="isSidebar" class="sidebar-container">
    <div class="sidebar-header">
      <h3 v-if="connectorInfo">{{ connectorInfo.blockName }}.{{ connectorInfo.connectorName }} - Ïª§ÎÑ•???§Ï†ï</h3>
      <h3 v-else>Ïª§ÎÑ•???§Ï†ï</h3>
      <button @click="closePopup" class="close-btn">??/button>
    </div>
    
    <div class="sidebar-content">
      <div v-if="connectorInfo">
        <!-- Ïª§ÎÑ•???¥Î¶Ñ ?∏Ïßë -->
        <div class="connector-name-setting">
          <label for="connector-name">Ïª§ÎÑ•???¥Î¶Ñ:</label>
          <input type="text" id="connector-name" v-model="editableConnectorName" placeholder="Ïª§ÎÑ•???¥Î¶Ñ???ÖÎ†•?òÏÑ∏?? />
        </div>
        
        <!-- ?âÎèô Í¥ÄÎ¶?Î≤ÑÌäº??-->
        <div class="add-action-section">
          <div class="section-header">
            <button v-if="!addingNewAction" @click="startAddingNewAction('')" class="add-action-btn">+ ?âÎèô Ï∂îÍ?</button>
            <button @click="openScriptEditor" class="script-editor-btn-small">?ìù ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏?/button>
          </div>
          <div v-if="addingNewAction" class="new-action-form">
            <label for="cp-action-name">?âÎèô ?¥Î¶Ñ:</label>
            <input type="text" id="cp-action-name" v-model="newAction.name">
            
            <label for="cp-action-type">?âÎèô ?Ä??</label>
            <select id="cp-action-type" v-model="newAction.type" @change="onNewActionTypeChange">
              <option value="delay">?úÎ†à??(Delay)</option>
              <option value="signal_update">?†Ìò∏ Î≥ÄÍ≤?(Signal Update)</option>
              <option value="signal_check">?†Ìò∏ Ï≤¥ÌÅ¨ (Signal Check)</option>
              <option value="signal_wait">?†Ìò∏ ?ÄÍ∏?(Signal Wait)</option>
              <option value="action_jump">?âÎèô ?¥Îèô (Action Jump)</option>
              <option value="route_to_connector">?§Ïùå Í≥µÏ†ï ÏßÑÌñâ (Route to Connector)</option>
              <option value="conditional_branch">Ï°∞Í±¥Î∂Ä ?§Ìñâ (Conditional Branch)</option>
            </select>

            <!-- Delay -->
            <div v-if="newAction.type === 'delay'" class="action-options">
              <label for="cp-delay-duration">ÏßÄ???úÍ∞Ñ(Ï¥?:</label>
              <input type="number" id="cp-delay-duration" v-model.number="newAction.parameters.duration" min="0">
            </div>
            
            <!-- Signal Update -->
            <div v-if="newAction.type === 'signal_update'" class="action-options">
              <label for="cp-signal-update-name">Î≥ÄÍ≤ΩÌï† ?†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-update-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-update-value">Î≥ÄÍ≤ΩÌï† ?†Ìò∏ Í∞?</label>
              <select id="cp-signal-update-value" v-model="newAction.parameters.value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Signal Check -->
            <div v-if="newAction.type === 'signal_check'" class="action-options">
              <label for="cp-signal-check-name">Ï≤¥ÌÅ¨???†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-check-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-check-value">Í∏∞Î? Í∞?</label>
              <select id="cp-signal-check-value" v-model="newAction.parameters.expected_value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Signal Wait -->
            <div v-if="newAction.type === 'signal_wait'" class="action-options">
              <label for="cp-signal-wait-name">?ÄÍ∏∞Ìï† ?†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-wait-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-wait-value">Í∏∞Î? Í∞?</label>
              <select id="cp-signal-wait-value" v-model="newAction.parameters.expected_value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Action Jump -->
            <div v-if="newAction.type === 'action_jump'" class="action-options">
              <label for="cp-action-jump-target">?¥Îèô???âÎèô ?¥Î¶Ñ (?ÑÏû¨ Ïª§ÎÑ•????:</label>
              <select id="cp-action-jump-target" v-model="newAction.parameters.target_action_name">
                 <option v-for="act in editableActions.filter(a => a.id !== newAction.id || editingActionIndex === null)" :key="act.id || act.name" :value="act.name">{{act.name}}</option>
              </select>
            </div>

            <!-- Route to Connector -->
            <div v-if="newAction.type === 'route_to_connector'" class="action-options">
              <label for="cp-route-block">?Ä??Î∏îÎ°ù:</label>
              <select id="cp-route-block" v-model="selectedTargetBlockId" @change="onTargetBlockChange">
                <option :value="null">Î∏îÎ°ù ?†ÌÉù...</option>
                <option :value="connectorInfo.blockId">{{ connectorInfo.blockName }} (?ÑÏû¨ Î∏îÎ°ù)</option> 
                <option v-for="block in connectorInfo.availableBlocks.filter(b => b.id !== connectorInfo.blockId)" :key="block.id" :value="block.id">
                    {{ block.name }} (ID: {{ block.id }})
                </option>
              </select>
              <div v-if="selectedTargetBlockId && targetBlockConnectors.length > 0">
                <label for="cp-route-connector">?Ä??Ïª§ÎÑ•??</label>
                <select id="cp-route-connector" v-model="newAction.parameters.target_connector_id">
                    <option v-if="parseInt(selectedTargetBlockId) === connectorInfo.blockId" value="self">
                        Î∏îÎ°ù ?°ÏÖò ?§Ìñâ (self)
                    </option>
                    <option v-for="cp in targetBlockConnectors" :key="cp.id" :value="cp.id">
                        {{ cp.name || cp.id }} ({{ getConnectionPointPosition(cp, getBlockById(selectedTargetBlockId)) }})
                    </option>
                </select>
              </div>
              <small v-else-if="selectedTargetBlockId && targetBlockConnectors.length === 0">?†ÌÉù??Î∏îÎ°ù???¨Ïö© Í∞Ä?•Ìïú Ïª§ÎÑ•?∞Í? ?ÜÏäµ?àÎã§.</small>
              
              <label for="cp-route-delay">Í≥µÏ†ï ?¥Îèô ?úÎ†à??Ï¥?:</label>
              <input type="number" id="cp-route-delay" v-model.number="newAction.parameters.delay" min="0">
            </div>

            <!-- Conditional Branch -->
            <div v-if="newAction.type === 'conditional_branch'" class="action-options">
              <div class="conditional-gui-editor">
                <h5>?? Ï°∞Í±¥Î∂Ä ?§Ìñâ ?∏ÏßëÍ∏?/h5>
                
                <!-- Ï°∞Í±¥ Î™©Î°ù -->
                <div class="conditions-list">
                  <div v-for="(condition, condIndex) in conditionalConditions" :key="condIndex" class="condition-block">
                    <div class="condition-header">
                      <h6>Ï°∞Í±¥ {{ condIndex + 1 }}</h6>
                      <button @click="removeCondition(condIndex)" class="remove-condition-btn" :disabled="conditionalConditions.length <= 1">?óëÔ∏?/button>
                    </div>
                    
                    <!-- IF Ï°∞Í±¥ ?§Ï†ï -->
                    <div class="condition-if">
                      <label>IF Ï°∞Í±¥:</label>
                      <div class="if-condition-row">
                        <select v-model="condition.signal" @change="updateConditionalScript">
                          <option value="">?†Ìò∏ ?†ÌÉù...</option>
                          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                        </select>
                        <span>=</span>
                        <select v-model="condition.value" @change="updateConditionalScript">
                          <option :value="true">true</option>
                          <option :value="false">false</option>
                        </select>
                      </div>
                    </div>
                    
                    <!-- THEN ?âÎèô??-->
                    <div class="condition-actions">
                      <label>THEN ?§Ìñâ???âÎèô??</label>
                      <div class="action-list">
                        <div v-for="(action, actionIndex) in condition.actions" :key="actionIndex" class="sub-action">
                          <select v-model="action.type" @change="updateSubActionParams(condIndex, actionIndex)">
                            <option value="signal_update">?†Ìò∏ Î≥ÄÍ≤?/option>
                            <option value="delay">?úÎ†à??/option>
                            <option value="route_to_connector">Ïª§ÎÑ•?∞Î°ú ?¥Îèô</option>
                          </select>
                          
                          <!-- ?†Ìò∏ Î≥ÄÍ≤?-->
                          <template v-if="action.type === 'signal_update'">
                            <select v-model="action.signal" @change="updateConditionalScript">
                              <option value="">?†Ìò∏ ?†ÌÉù...</option>
                              <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                            </select>
                            <span>=</span>
                            <select v-model="action.value" @change="updateConditionalScript">
                              <option :value="true">true</option>
                              <option :value="false">false</option>
                            </select>
                          </template>
                          
                          <!-- ?úÎ†à??-->
                          <template v-if="action.type === 'delay'">
                            <input type="number" v-model.number="action.duration" @input="updateConditionalScript" min="0" placeholder="Ï¥?>
                            <span>Ï¥?/span>
                          </template>
                          
                          <!-- Ïª§ÎÑ•?∞Î°ú ?¥Îèô -->
                          <template v-if="action.type === 'route_to_connector'">
                            <select v-model="action.targetBlock" @change="updateSubActionConnectors(condIndex, actionIndex)">
                              <option value="">Î∏îÎ°ù ?†ÌÉù...</option>
                              <option v-for="block in allBlocks" :key="block.id" :value="block.name">{{ block.name }}</option>
                            </select>
                            <span>.</span>
                            <select v-model="action.targetConnector" @change="updateConditionalScript">
                              <option value="">Ïª§ÎÑ•???†ÌÉù...</option>
                              <option v-for="cp in getConnectorsForBlock(action.targetBlock)" :key="cp.id" :value="cp.name || cp.id">{{ cp.name || cp.id }}</option>
                            </select>
                          </template>
                          
                          <button @click="removeSubAction(condIndex, actionIndex)" class="remove-sub-action-btn">?óëÔ∏?/button>
                        </div>
                        <button @click="addSubAction(condIndex)" class="add-sub-action-btn">+ ?âÎèô Ï∂îÍ?</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="conditional-controls">
                  <button @click="addCondition" class="add-condition-btn">+ Ï°∞Í±¥ Ï∂îÍ?</button>
                  <button type="button" @click="openScriptEditor" class="open-script-editor-btn">?ìù ?§ÌÅ¨Î¶ΩÌä∏Î°??∏Ïßë</button>
                </div>
              </div>
            </div>

            <button @click="confirmAddAction" :disabled="isSignalNameDuplicate && newAction.type === 'signal_create'">?ïÏù∏</button>
            <button @click="cancelAddingNewAction">Ï∑®ÏÜå</button>
          </div>
        </div>
        
        <h4>?âÎèô Î™©Î°ù</h4>
        <div class="actions-list-container">
          <div v-if="!editableActions || editableActions.length === 0" class="no-actions">
            ?ïÏùò???âÎèô???ÜÏäµ?àÎã§. "?âÎèô Ï∂îÍ?" Î≤ÑÌäº???åÎü¨ ???âÎèô??ÎßåÎìú?∏Ïöî.
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
                  <button @click="editAction(index)" class="action-btn edit-btn" title="?òÏ†ï">?èÔ∏è</button>
                  <button @click="moveAction(index, -1)" :disabled="index === 0" class="action-btn move-btn move-up-btn" title="?ÑÎ°ú">‚¨ÜÔ∏è</button>
                  <button @click="moveAction(index, 1)" :disabled="index === editableActions.length - 1" class="action-btn move-btn move-down-btn" title="?ÑÎûòÎ°?>‚¨áÔ∏è</button>
                  <button @click="deleteAction(index)" class="action-btn delete-btn" title="??†ú">?óëÔ∏?/button>
                </div>
              </div>
              <div class="action-parameters">
                <div v-if="Object.keys(action.parameters || {}).length > 0" class="parameter-list">
                  <!-- Ï°∞Í±¥Î∂Ä ?§Ìñâ??Í≤ΩÏö∞ ?πÎ≥Ñ??ÎØ∏Î¶¨Î≥¥Í∏∞ -->
                  <div v-if="action.type === 'conditional_branch'" class="conditional-preview">
                    <div v-for="(line, lineIndex) in (action.parameters.script || '').split('\n').slice(0, 5)" :key="lineIndex" class="conditional-line">
                      <span v-if="line.trim().startsWith('if ')" class="script-if">{{ line.trim() }}</span>
                      <span v-else-if="line.startsWith('\t')" class="script-sub-action">
                        <span class="indent-marker">?ó‚îÅ</span> {{ line.trim() }}
                      </span>
                      <span v-else-if="line.trim()">{{ line.trim() }}</span>
                    </div>
                    <div v-if="(action.parameters.script || '').split('\n').length > 5" style="color: #6c757d; font-style: italic;">
                      ... ({{ (action.parameters.script || '').split('\n').length - 5 }}Í∞?Ï§???
                    </div>
                  </div>
                  <!-- ?ºÎ∞ò ?åÎùºÎØ∏ÌÑ∞ -->
                  <div v-for="(value, key) in action.parameters" :key="key" v-show="!(action.type === 'conditional_branch' && key === 'script')" class="parameter-item">
                    <span class="parameter-key">{{ key }}:</span>
                    <span class="parameter-value">{{ formatParameterValue(key, value) }}</span>
                  </div>
                </div>
                <div v-else class="no-parameters">?åÎùºÎØ∏ÌÑ∞ ?ÜÏùå</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <div v-else>
        <p>?†ÌÉù??Ïª§ÎÑ•?∞Í? ?ÜÏäµ?àÎã§.</p>
      </div>
    </div>
    
    <div class="sidebar-actions">
      <button @click="closePopup">?´Í∏∞</button>
    </div>
  </div>
  
  <!-- ?ùÏóÖ Î™®Îìú (Í∏∞Ï°¥ ÏΩîÎìú) -->
  <div v-else class="popup-overlay" @click.self="closePopup">
    <div class="popup connector-settings-popup">
      <h3 v-if="connectorInfo">
        {{ connectorInfo.blockName }} - Ïª§ÎÑ•??[{{ currentConnectorName }}] ?§Ï†ï
      </h3>
      <h3 v-else>Ïª§ÎÑ•???§Ï†ï</h3>
      
      <div v-if="connectorInfo && editableActions !== null">
        <div class="connector-name-edit">
          <label for="connector-name-input">Ïª§ÎÑ•???¥Î¶Ñ:</label>
          <input type="text" id="connector-name-input" v-model="currentConnectorName" @blur="onConnectorNameBlur">
        </div>

        <h4>?âÎèô Î™©Î°ù</h4>
        <div v-if="!editableActions || editableActions.length === 0" class="no-actions">
          ?ïÏùò???âÎèô???ÜÏäµ?àÎã§. "?âÎèô Ï∂îÍ?" Î≤ÑÌäº???åÎü¨ ???âÎèô??ÎßåÎìú?∏Ïöî.
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
                <button @click="editAction(index)" class="action-btn edit-btn" title="?òÏ†ï">?èÔ∏è</button>
                <button @click="moveAction(index, -1)" :disabled="index === 0" class="action-btn move-btn move-up-btn" title="?ÑÎ°ú">‚¨ÜÔ∏è</button>
                <button @click="moveAction(index, 1)" :disabled="index === editableActions.length - 1" class="action-btn move-btn move-down-btn" title="?ÑÎûòÎ°?>‚¨áÔ∏è</button>
                <button @click="deleteAction(index)" class="action-btn delete-btn" title="??†ú">?óëÔ∏?/button>
              </div>
            </div>
            <div class="action-parameters">
              <div v-if="Object.keys(action.parameters || {}).length > 0" class="parameter-list">
                <!-- Ï°∞Í±¥Î∂Ä ?§Ìñâ??Í≤ΩÏö∞ ?πÎ≥Ñ??ÎØ∏Î¶¨Î≥¥Í∏∞ -->
                <div v-if="action.type === 'conditional_branch'" class="conditional-preview">
                  <div v-for="(line, lineIndex) in (action.parameters.script || '').split('\n').slice(0, 5)" :key="lineIndex" class="conditional-line">
                    <span v-if="line.trim().startsWith('if ')" class="script-if">{{ line.trim() }}</span>
                    <span v-else-if="line.startsWith('\t')" class="script-sub-action">
                      <span class="indent-marker">?ó‚îÅ</span> {{ line.trim() }}
                    </span>
                    <span v-else-if="line.trim()">{{ line.trim() }}</span>
                  </div>
                  <div v-if="(action.parameters.script || '').split('\n').length > 5" style="color: #6c757d; font-style: italic;">
                    ... ({{ (action.parameters.script || '').split('\n').length - 5 }}Í∞?Ï§???
                  </div>
                </div>
                <!-- ?ºÎ∞ò ?åÎùºÎØ∏ÌÑ∞ -->
                <div v-for="(value, key) in action.parameters" :key="key" v-show="!(action.type === 'conditional_branch' && key === 'script')" class="parameter-item">
                  <span class="parameter-key">{{ key }}:</span>
                  <span class="parameter-value">{{ formatParameterValue(key, value) }}</span>
                </div>
              </div>
              <div v-else class="no-parameters">?åÎùºÎØ∏ÌÑ∞ ?ÜÏùå</div>
            </div>
          </li>
        </ul>

        <div class="add-action-section">
          <div class="section-header">
            <button @click="openScriptEditor" class="script-editor-btn-small">?ìù ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏?/button>
          </div>
          <div v-if="!addingNewAction">
            <button @click="startAddingNewAction('')">+ ?âÎèô Ï∂îÍ?</button>
          </div>
          <div v-if="addingNewAction" class="new-action-form">
            <label for="cp-action-name">?âÎèô ?¥Î¶Ñ:</label>
            <input type="text" id="cp-action-name" v-model="newAction.name">
            
            <label for="cp-action-type">?âÎèô ?Ä??</label>
            <select id="cp-action-type" v-model="newAction.type" @change="onNewActionTypeChange">
              <option value="delay">?úÎ†à??(Delay)</option>
              <option value="signal_update">?†Ìò∏ Î≥ÄÍ≤?(Signal Update)</option>
              <option value="signal_check">?†Ìò∏ Ï≤¥ÌÅ¨ (Signal Check)</option>
              <option value="signal_wait">?†Ìò∏ ?ÄÍ∏?(Signal Wait)</option>
              <option value="action_jump">?âÎèô ?¥Îèô (Action Jump)</option>
              <option value="route_to_connector">?§Ïùå Í≥µÏ†ï ÏßÑÌñâ (Route to Connector)</option>
              <option value="conditional_branch">Ï°∞Í±¥Î∂Ä ?§Ìñâ (Conditional Branch)</option>
            </select>

            <!-- Delay -->
            <div v-if="newAction.type === 'delay'" class="action-options">
              <label for="cp-delay-duration">ÏßÄ???úÍ∞Ñ(Ï¥?:</label>
              <input type="number" id="cp-delay-duration" v-model.number="newAction.parameters.duration" min="0">
            </div>
            
            <!-- Signal Update -->
            <div v-if="newAction.type === 'signal_update'" class="action-options">
              <label for="cp-signal-update-name">Î≥ÄÍ≤ΩÌï† ?†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-update-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-update-value">Î≥ÄÍ≤ΩÌï† ?†Ìò∏ Í∞?</label>
              <select id="cp-signal-update-value" v-model="newAction.parameters.value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Signal Check -->
            <div v-if="newAction.type === 'signal_check'" class="action-options">
              <label for="cp-signal-check-name">Ï≤¥ÌÅ¨???†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-check-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-check-value">Í∏∞Î? Í∞?</label>
              <select id="cp-signal-check-value" v-model="newAction.parameters.expected_value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Signal Wait -->
            <div v-if="newAction.type === 'signal_wait'" class="action-options">
              <label for="cp-signal-wait-name">?ÄÍ∏∞Ìï† ?†Ìò∏ ?¥Î¶Ñ:</label>
              <select id="cp-signal-wait-name" v-model="newAction.parameters.signal_name">
                <option value="" disabled>?†Ìò∏ ?†ÌÉù...</option>
                <option v-for="name in allSignals" :key="name" :value="name">{{ name }}</option>
              </select>
              <label for="cp-signal-wait-value">Í∏∞Î? Í∞?</label>
              <select id="cp-signal-wait-value" v-model="newAction.parameters.expected_value">
                <option :value="true">Ï∞?(True)</option>
                <option :value="false">Í±∞Ïßì (False)</option>
              </select>
            </div>

            <!-- Action Jump -->
            <div v-if="newAction.type === 'action_jump'" class="action-options">
              <label for="cp-action-jump-target">?¥Îèô???âÎèô ?¥Î¶Ñ (?ÑÏû¨ Ïª§ÎÑ•????:</label>
              <select id="cp-action-jump-target" v-model="newAction.parameters.target_action_name">
                 <option v-for="act in editableActions.filter(a => a.id !== newAction.id || editingActionIndex === null)" :key="act.id || act.name" :value="act.name">{{act.name}}</option>
              </select>
            </div>

            <!-- Route to Connector -->
            <div v-if="newAction.type === 'route_to_connector'" class="action-options">
              <label for="cp-route-block">?Ä??Î∏îÎ°ù:</label>
              <select id="cp-route-block" v-model="selectedTargetBlockId" @change="onTargetBlockChange">
                <option :value="null">Î∏îÎ°ù ?†ÌÉù...</option>
                <option :value="connectorInfo.blockId">{{ connectorInfo.blockName }} (?ÑÏû¨ Î∏îÎ°ù)</option> 
                <option v-for="block in connectorInfo.availableBlocks.filter(b => b.id !== connectorInfo.blockId)" :key="block.id" :value="block.id">
                    {{ block.name }} (ID: {{ block.id }})
                </option>
              </select>
              <div v-if="selectedTargetBlockId && targetBlockConnectors.length > 0">
                <label for="cp-route-connector">?Ä??Ïª§ÎÑ•??</label>
                <select id="cp-route-connector" v-model="newAction.parameters.target_connector_id">
                    <option v-if="parseInt(selectedTargetBlockId) === connectorInfo.blockId" value="self">
                        Î∏îÎ°ù ?°ÏÖò ?§Ìñâ (self)
                    </option>
                    <option v-for="cp in targetBlockConnectors" :key="cp.id" :value="cp.id">
                        {{ cp.name || cp.id }} ({{ getConnectionPointPosition(cp, getBlockById(selectedTargetBlockId)) }})
                    </option>
                </select>
              </div>
              <small v-else-if="selectedTargetBlockId && targetBlockConnectors.length === 0">?†ÌÉù??Î∏îÎ°ù???¨Ïö© Í∞Ä?•Ìïú Ïª§ÎÑ•?∞Í? ?ÜÏäµ?àÎã§.</small>
              
              <label for="cp-route-delay">Í≥µÏ†ï ?¥Îèô ?úÎ†à??Ï¥?:</label>
              <input type="number" id="cp-route-delay" v-model.number="newAction.parameters.delay" min="0">
            </div>

            <!-- Conditional Branch -->
            <div v-if="newAction.type === 'conditional_branch'" class="action-options">
              <div class="conditional-gui-editor">
                <h5>?? Ï°∞Í±¥Î∂Ä ?§Ìñâ ?∏ÏßëÍ∏?/h5>
                
                <!-- Ï°∞Í±¥ Î™©Î°ù -->
                <div class="conditions-list">
                  <div v-for="(condition, condIndex) in conditionalConditions" :key="condIndex" class="condition-block">
                    <div class="condition-header">
                      <h6>Ï°∞Í±¥ {{ condIndex + 1 }}</h6>
                      <button @click="removeCondition(condIndex)" class="remove-condition-btn" :disabled="conditionalConditions.length <= 1">?óëÔ∏?/button>
                    </div>
                    
                    <!-- IF Ï°∞Í±¥ ?§Ï†ï -->
                    <div class="condition-if">
                      <label>IF Ï°∞Í±¥:</label>
                      <div class="if-condition-row">
                        <select v-model="condition.signal" @change="updateConditionalScript">
                          <option value="">?†Ìò∏ ?†ÌÉù...</option>
                          <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                        </select>
                        <span>=</span>
                        <select v-model="condition.value" @change="updateConditionalScript">
                          <option :value="true">true</option>
                          <option :value="false">false</option>
                        </select>
                      </div>
                    </div>
                    
                    <!-- THEN ?âÎèô??-->
                    <div class="condition-actions">
                      <label>THEN ?§Ìñâ???âÎèô??</label>
                      <div class="action-list">
                        <div v-for="(action, actionIndex) in condition.actions" :key="actionIndex" class="sub-action">
                          <select v-model="action.type" @change="updateSubActionParams(condIndex, actionIndex)">
                            <option value="signal_update">?†Ìò∏ Î≥ÄÍ≤?/option>
                            <option value="delay">?úÎ†à??/option>
                            <option value="route_to_connector">Ïª§ÎÑ•?∞Î°ú ?¥Îèô</option>
                          </select>
                          
                          <!-- ?†Ìò∏ Î≥ÄÍ≤?-->
                          <template v-if="action.type === 'signal_update'">
                            <select v-model="action.signal" @change="updateConditionalScript">
                              <option value="">?†Ìò∏ ?†ÌÉù...</option>
                              <option v-for="signal in allSignals" :key="signal" :value="signal">{{ signal }}</option>
                            </select>
                            <span>=</span>
                            <select v-model="action.value" @change="updateConditionalScript">
                              <option :value="true">true</option>
                              <option :value="false">false</option>
                            </select>
                          </template>
                          
                          <!-- ?úÎ†à??-->
                          <template v-if="action.type === 'delay'">
                            <input type="number" v-model.number="action.duration" @input="updateConditionalScript" min="0" placeholder="Ï¥?>
                            <span>Ï¥?/span>
                          </template>
                          
                          <!-- Ïª§ÎÑ•?∞Î°ú ?¥Îèô -->
                          <template v-if="action.type === 'route_to_connector'">
                            <select v-model="action.targetBlock" @change="updateSubActionConnectors(condIndex, actionIndex)">
                              <option value="">Î∏îÎ°ù ?†ÌÉù...</option>
                              <option v-for="block in allBlocks" :key="block.id" :value="block.name">{{ block.name }}</option>
                            </select>
                            <span>.</span>
                            <select v-model="action.targetConnector" @change="updateConditionalScript">
                              <option value="">Ïª§ÎÑ•???†ÌÉù...</option>
                              <option v-for="cp in getConnectorsForBlock(action.targetBlock)" :key="cp.id" :value="cp.name || cp.id">{{ cp.name || cp.id }}</option>
                            </select>
                          </template>
                          
                          <button @click="removeSubAction(condIndex, actionIndex)" class="remove-sub-action-btn">?óëÔ∏?/button>
                        </div>
                        <button @click="addSubAction(condIndex)" class="add-sub-action-btn">+ ?âÎèô Ï∂îÍ?</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="conditional-controls">
                  <button @click="addCondition" class="add-condition-btn">+ Ï°∞Í±¥ Ï∂îÍ?</button>
                  <button type="button" @click="openScriptEditor" class="open-script-editor-btn">?ìù ?§ÌÅ¨Î¶ΩÌä∏Î°??∏Ïßë</button>
                </div>
              </div>
            </div>

            <button @click="confirmAddAction" :disabled="isSignalNameDuplicate && newAction.type === 'signal_create'">?ïÏù∏</button>
            <button @click="cancelAddingNewAction">Ï∑®ÏÜå</button>
          </div>
        </div>

      </div>
      <div v-else>
        <p>?†ÌÉù??Ïª§ÎÑ•???ïÎ≥¥Í∞Ä ?ÜÏäµ?àÎã§.</p>
      </div>

      <div class="popup-actions">
        <button @click="closePopup">?´Í∏∞</button>
      </div>
    </div>
  </div>

  <!-- ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏??ùÏóÖ - ?ÑÏ†Ñ???ÖÎ¶Ω??ÏµúÏÉÅ???àÎ≤® -->
  <div v-if="showScriptEditor" class="script-editor-overlay" @click.self="closeScriptEditor">
    <div class="script-editor-popup">
      <div class="script-editor-header">
        <h3>?ìù Ïª§ÎÑ•???§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏?/h3>
        <button @click="closeScriptEditor" class="close-btn">??/button>
      </div>
      
      <div class="script-editor-content">
        <div class="script-help">
          <h5>?ìã Î¨∏Î≤ï Í∞Ä?¥Îìú:</h5>
          <div class="script-examples">
            <span class="script-command">delay</span> <span class="script-value">5</span> - 5Ï¥??úÎ†à??br>
            <span class="script-command">if</span> <span class="script-variable">Í≥µÏ†ï1 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span> - ?†Ìò∏ Í∞?Ï≤¥ÌÅ¨<br>
            <span class="script-command">wait</span> <span class="script-variable">Í≥µÏ†ï2 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span> - ?†Ìò∏Í∞Ä Í∞íÏù¥ ???åÍπåÏßÄ ?ÄÍ∏?br>
            <span class="script-variable">Í≥µÏ†ï1 load enable</span> <span class="script-operator">=</span> <span class="script-value">false</span> - ?†Ìò∏ Í∞?Î≥ÄÍ≤?br>
            <span class="script-command">go to</span> <span class="script-value">self.unload</span> - ?ÑÏû¨ Î∏îÎ°ù??Ïª§ÎÑ•?∞Î°ú ?¥Îèô<br>
            <span class="script-command">go to</span> <span class="script-variable">Î∞∞Ï∂ú</span>.<span class="script-value">load</span> - ?§Î•∏ Î∏îÎ°ù??Ïª§ÎÑ•?∞Î°ú ?¥Îèô<br>
            <span class="script-command">jump to</span> <span class="script-value">2</span> - 2Î≤àÏß∏ ?âÎèô?ºÎ°ú ?¥Îèô<br>
            <br><strong>?? Ï°∞Í±¥Î∂Ä ?§Ìñâ:</strong><br>
            <span class="script-command">if</span> <span class="script-variable">Í≥µÏ†ï1 load enable</span> <span class="script-operator">=</span> <span class="script-value">true</span><br>
            &nbsp;&nbsp;&nbsp;&nbsp;<span class="script-variable">Í≥µÏ†ï1 load enable</span> <span class="script-operator">=</span> <span class="script-value">false</span><br>
            &nbsp;&nbsp;&nbsp;&nbsp;<span class="script-command">go to</span> <span class="script-variable">Í≥µÏ†ï1</span>.<span class="script-value">LOAD</span><br>
            <span class="script-comment">// ?¥Í≤É?Ä Ï£ºÏÑù?ÖÎãà??/span> - Ï£ºÏÑù Ï≤òÎ¶¨
          </div>
          
          <!-- ?¨Ïö© Í∞Ä?•Ìïú ?†Ìò∏ Î™©Î°ù -->
          <div class="available-items">
            <h6>?îó ?¨Ïö© Í∞Ä?•Ìïú ?†Ìò∏:</h6>
            <div class="item-list">
              <span v-for="signal in allSignals" :key="signal" class="item-tag signal-tag">{{ signal }}</span>
              <span v-if="allSignals.length === 0" class="no-items">?ïÏùò???†Ìò∏Í∞Ä ?ÜÏäµ?àÎã§</span>
            </div>
          </div>
          
          <!-- ?¨Ïö© Í∞Ä?•Ìïú Î∏îÎ°ù Î™©Î°ù -->
          <div class="available-items">
            <h6>?ì¶ ?¨Ïö© Í∞Ä?•Ìïú Î∏îÎ°ù:</h6>
            <div class="item-list">
              <div v-for="block in allBlocks" :key="block.id" class="block-info">
                <span class="item-tag block-tag">{{ block.name }}</span>
                <span class="connector-list">
                  Ïª§ÎÑ•?? 
                  <span v-for="cp in block.connectionPoints" :key="cp.id" class="item-tag connector-tag">{{ cp.name || cp.id }}</span>
                  <span v-if="!block.connectionPoints || block.connectionPoints.length === 0">?ÜÏùå</span>
                </span>
              </div>
              <span v-if="allBlocks.length === 0" class="no-items">?ïÏùò??Î∏îÎ°ù???ÜÏäµ?àÎã§</span>
            </div>
          </div>
        </div>
        
        <div class="script-input-section">
          <label for="script-editor-input-connector">?§ÌÅ¨Î¶ΩÌä∏ ?ÖÎ†•:</label>
          <div class="script-editor-container">
            <div class="line-numbers" ref="lineNumbers">
              <div v-for="lineNum in scriptLineCount" :key="lineNum" class="line-number">
                {{ lineNum }}
              </div>
            </div>
            <textarea 
              id="script-editor-input-connector" 
              v-model="scriptInput" 
              placeholder="// ?§ÌÅ¨Î¶ΩÌä∏Î•??ÖÎ†•?òÏÑ∏??
              rows="25"
              class="script-editor-textarea"
              @scroll="syncLineNumbersScroll"
              @input="updateLineNumbers"
              @keydown="handleScriptKeydown"
              ref="scriptTextarea"
            ></textarea>
          </div>
          
          <!-- ?§ÏãúÍ∞??†Ìö®??Í≤Ä??Í≤∞Í≥º ?úÏãú -->
          <div v-if="scriptValidationWarnings.length > 0" class="script-warnings">
            <h6>?†Ô∏è Í≤Ä??Í≤∞Í≥º:</h6>
            <div v-for="warning in scriptValidationWarnings" :key="warning" class="warning-item">
              {{ warning }}
            </div>
          </div>
        </div>
      </div>
      
      <div class="script-editor-actions">
        <button @click="parseAndAddScript" :disabled="!scriptInput.trim() || scriptValidationWarnings.length > 0" class="apply-script-btn">?§ÌÅ¨Î¶ΩÌä∏ ?ÅÏö©</button>
        <button @click="closeScriptEditor">Ï∑®ÏÜå</button>
      </div>
      
      <div v-if="scriptParseError" class="script-error">
        ??{{ scriptParseError }}
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
  name: '??Ïª§ÎÑ•???âÎèô',
  type: 'delay', 
  parameters: {}
});
const newAction = ref(newActionTemplate());
const editingActionIndex = ref(null); 

const selectedTargetBlockId = ref(null); // "?§Ïùå Í≥µÏ†ï ÏßÑÌñâ" ???Ä??Î∏îÎ°ù ID
const isSignalNameDuplicate = ref(false);
const currentConnectorName = ref(''); // Ïª§ÎÑ•???¥Î¶Ñ ?∏Ïßë??
const editableConnectorName = ref(''); // ?∏Ïßë Í∞Ä?•Ìïú Ïª§ÎÑ•???¥Î¶Ñ

// ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏?Í¥Ä??Î≥Ä?òÎì§ Ï∂îÍ?
const showScriptEditor = ref(false);
const scriptInput = ref('');
const scriptParseError = ref(null);
const scriptValidationWarnings = ref([]);
const scriptLineCount = ref(1);
const lineNumbers = ref(null);
const scriptTextarea = ref(null);

// Ï°∞Í±¥Î∂Ä ?§Ìñâ GUI ?∏ÏßëÍ∏∞Î? ?ÑÌïú Î≥Ä?òÎì§
const conditionalConditions = ref([]);

// Î¨¥Ìïú Î£®ÌîÑ Î∞©Ï?Î•??ÑÌïú ?åÎûòÍ∑?
let isInitializingConnector = false;

watch(() => props.connectorInfo, (newInfo) => {
  isInitializingConnector = true; // Ï¥àÍ∏∞???úÏûë
  
  if (newInfo) {
    editableActions.value = JSON.parse(JSON.stringify(newInfo.actions || []));
    currentConnectorName.value = newInfo.connectorName || newInfo.connectorId; // Ï¥àÍ∏∞ ?¥Î¶Ñ ?§Ï†ï
    editableConnectorName.value = newInfo.connectorName || newInfo.connectorId; // ?∏Ïßë Í∞Ä?•Ìïú ?¥Î¶Ñ ?§Ï†ï
  } else {
    editableActions.value = [];
    currentConnectorName.value = '';
    editableConnectorName.value = '';
  }
  addingNewAction.value = false;
  editingActionIndex.value = null;
  selectedTargetBlockId.value = null;
  
  // ?§Ïùå ?±Ïóê??Ï¥àÍ∏∞???ÑÎ£å
  setTimeout(() => {
    isInitializingConnector = false;
  }, 0);
}, { immediate: true, deep: true });

const actionTypeDisplayNames = {
  delay: '?úÎ†à??,
  signal_update: '?†Ìò∏ Î≥ÄÍ≤?,
  signal_check: '?†Ìò∏ Ï≤¥ÌÅ¨',
  signal_wait: '?†Ìò∏ ?ÄÍ∏?,
  action_jump: '?âÎèô ?¥Îèô',
  route_to_connector: '?§Ïùå Í≥µÏ†ï ÏßÑÌñâ',
  conditional_branch: 'Ï°∞Í±¥Î∂Ä ?§Ìñâ'
};

function getActionTypeDisplayName(type) {
  return actionTypeDisplayNames[type] || type;
}

function getActionTypeIcon(type) {
  const icons = {
    delay: '?±Ô∏è',
    signal_update: '?îÑ',
    signal_check: '?îç',
    signal_wait: '??,
    action_jump: '?™Ô∏è',
    route_to_connector: '?îó',
    conditional_branch: '??'
  };
  return icons[type] || '??;
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
    return targetBlock ? targetBlock.name : `Î∏îÎ°ù${value}`;
  }
  if (key === 'target_connector_id') {
    if (value === 'self') return 'Î∏îÎ°ù ?°ÏÖò';
    // Ïª§ÎÑ•???¥Î¶Ñ Ï∞æÍ∏∞ Î°úÏßÅ?Ä Î≥µÏû°?òÎ?Î°??ºÎã® ID Í∑∏Î?Î°??úÏãú
    return value;
  }
  if (key === 'signal_name') {
    return value;
  }
  if (key === 'expected_value' || key === 'value') {
    return value ? 'Ï∞?true)' : 'Í±∞Ïßì(false)';
  }
  if (key === 'duration' || key === 'delay') {
    return `${value}Ï¥?;
  }
  if (key === 'script') {
    // ?§ÌÅ¨Î¶ΩÌä∏??Ï≤?Î≤àÏß∏ Ï§ÑÎßå ÎØ∏Î¶¨Î≥¥Í∏∞Î°??úÏãú
    const firstLine = value.split('\n')[0];
    return firstLine.length > 30 ? firstLine.substring(0, 30) + '...' : firstLine;
  }
  return value;
}

function formatParameters(params) {
    if (!params || Object.keys(params).length === 0) return '?ÜÏùå';
    let parts = [];
    if (params.target_block_id && params.target_connector_id) {
        const targetBlock = props.allBlocks.find(b => b.id === parseInt(params.target_block_id));
        let targetText = `?Ä?? ${targetBlock ? targetBlock.name : '?????ÜÎäî Î∏îÎ°ù'}`;
        if (parseInt(params.target_block_id) === props.connectorInfo?.blockId) {
             targetText += ` (?êÏã†) -> Î∏îÎ°ù ?âÎèô`;
        } else {
            targetText += `.${params.target_connector_id}`;
        }
       
        if (params.delay !== undefined) {
            targetText += `, ?úÎ†à?? ${params.delay}s`;
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
  selectedTargetBlockId.value = null; // ?Ä??Î∏îÎ°ù ?†ÌÉù Ï¥àÍ∏∞??
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
        // GUI ?∏ÏßëÍ∏?Ï¥àÍ∏∞??
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

// ?êÎèô ?Ä???®Ïàò
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
  }, 1000); // 1Ï¥??îÎ∞î?¥Ïä§
}

function confirmAddAction() {
  if (!newAction.value.name.trim()) {
    alert('?âÎèô ?¥Î¶Ñ???ÖÎ†•?¥Ï£º?∏Ïöî.');
    return;
  }
  if (newAction.value.type === 'signal_create' && isSignalNameDuplicate.value) {
    alert('?¥Î? ?¨Ïö© Ï§ëÏù∏ ?†Ìò∏ ?¥Î¶Ñ?ÖÎãà?? ?§Î•∏ ?¥Î¶Ñ???¨Ïö©?¥Ï£º?∏Ïöî.');
    return;
  }
  if (newAction.value.type === 'signal_update' && !newAction.value.parameters.signal_name) {
    alert('Î≥ÄÍ≤ΩÌï† ?†Ìò∏Î•??†ÌÉù?¥Ï£º?∏Ïöî.');
    return;
  }
  if (newAction.value.type === 'route_to_connector') {
      if (!selectedTargetBlockId.value || !newAction.value.parameters.target_connector_id) {
          alert('?§Ïùå Í≥µÏ†ï ÏßÑÌñâ???ÑÌï¥?úÎäî ?Ä??Î∏îÎ°ùÍ≥?Ïª§ÎÑ•?∞Î? Î™®Îëê ?†ÌÉù?¥Ïïº ?©Îãà??');
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
  
  // ?îÎ∞î?¥Ïä§???êÎèô ?Ä??
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
  if (confirm(`'${editableActions.value[index].name}' ?âÎèô????†ú?òÏãúÍ≤†Ïäµ?àÍπå?`)) {
    editableActions.value.splice(index, 1);
    // ?îÎ∞î?¥Ïä§???êÎèô ?Ä??
    debouncedAutoSave();
  }
}

function moveAction(index, direction) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= editableActions.value.length) return;
  const item = editableActions.value.splice(index, 1)[0];
  editableActions.value.splice(newIndex, 0, item);
  // ?îÎ∞î?¥Ïä§???êÎèô ?Ä??
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
        newAction.value.parameters.target_connector_id = targetBlockConnectors.value[0].id; // Ï≤?Î≤àÏß∏ Ïª§ÎÑ•?∞Î°ú Í∏∞Î≥∏ ?§Ï†ï
    } else {
        newAction.value.parameters.target_connector_id = null;
    }
}
function getBlockById(blockId) {
    return props.allBlocks.find(b => b.id === blockId);
}

function getConnectionPointPosition(cp, block) {
    if (!cp || !block) return '';
    if (cp.x > block.width * 0.75 ) return `?§Î•∏Ï™?(${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.x < block.width * 0.25 ) return `?ºÏ™Ω (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.y > block.height * 0.75 ) return `?ÑÎûòÏ™?(${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    if (cp.y < block.height * 0.25 ) return `?ÑÏ™Ω (${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
    return `(${cp.x.toFixed(0)}, ${cp.y.toFixed(0)})`;
}

function closePopup() {
  emit('close-popup');
}

function onConnectorNameBlur() {
  // ?ÑÏöî???¥Î¶Ñ ?†Ìö®??Í≤Ä????Ï∂îÍ? Í∞Ä??
  if (!currentConnectorName.value.trim()) {
    // alert("Ïª§ÎÑ•???¥Î¶Ñ?Ä ÎπÑÏõå?????ÜÏäµ?àÎã§.");
    // currentConnectorName.value = props.connectorInfo?.connectorId || 'default'; // Í∏∞Î≥∏Í∞íÏúºÎ°?Î≥µÏõê
  }
}

function saveAndClose() {
  if (props.connectorInfo) {
    emit('save-connector-settings', 
      props.connectorInfo.blockId, 
      props.connectorInfo.connectorId, 
      JSON.parse(JSON.stringify(editableActions.value)),
      currentConnectorName.value.trim() // Ïª§ÎÑ•???¥Î¶Ñ???®Íªò ?ÑÎã¨
    );
  }
  closePopup();
}

function openScriptEditor() {
  console.log("[ConnectorSettingsPopup] openScriptEditor ?∏Ï∂ú??);
  console.log("[ConnectorSettingsPopup] ?ÑÏû¨ showScriptEditor.value:", showScriptEditor.value);
  showScriptEditor.value = true;
  console.log("[ConnectorSettingsPopup] showScriptEditor.value ?§Ï†ï ??", showScriptEditor.value);
  // ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏??¥Î©¥ ?êÎèô?ºÎ°ú ?ÑÏû¨ ?§Ï†ï Î∂àÎü¨?§Í∏∞
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
      // ?âÎèô???ÜÏùÑ ?åÎäî Îπ??§ÌÅ¨Î¶ΩÌä∏Î°??§Ï†ï
      scriptLines.push('// ?§Ï†ï???âÎèô???ÜÏäµ?àÎã§');
    }
    
    scriptInput.value = scriptLines.join('\n');
    console.log("Ïª§ÎÑ•???ÑÏû¨ ?§Ï†ï???§ÌÅ¨Î¶ΩÌä∏Î°?Î≥Ä?òÎêò?àÏäµ?àÎã§.");
    
  } catch (error) {
    console.error("Ïª§ÎÑ•???§Ï†ï???§ÌÅ¨Î¶ΩÌä∏Î°?Î≥Ä?òÌïò??Ï§??§Î•ò:", error);
    scriptParseError.value = `Î≥Ä???§Î•ò: ${error.message}`;
  }
}

function convertActionToScript(action, lineNumber) {
  if (!action || !action.type) {
    return `// ?âÎèô ${lineNumber}: ?Ä?ÖÏù¥ ?ïÏùò?òÏ? ?äÏùå`;
  }
  
  try {
    switch (action.type) {
      case 'delay':
        const duration = action.parameters?.duration || 3;
        return `delay ${duration}`;
        
      case 'signal_check':
        const checkSignal = action.parameters?.signal_name || '?†Ìò∏Î™?;
        const expectedValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `if ${checkSignal} = ${expectedValue}`;
        
      case 'signal_wait':
        const waitSignal = action.parameters?.signal_name || '?†Ìò∏Î™?;
        const waitValue = action.parameters?.expected_value === true ? 'true' : 'false';
        return `wait ${waitSignal} = ${waitValue}`;
        
      case 'signal_update':
        const updateSignal = action.parameters?.signal_name || '?†Ìò∏Î™?;
        const newValue = action.parameters?.value === true ? 'true' : 'false';
        return `${updateSignal} = ${newValue}`;
        
      case 'route_to_connector':
        if (action.parameters?.target_block_id && action.parameters?.target_connector_id) {
          // ?§Î•∏ Î∏îÎ°ù?ºÎ°ú ?¥Îèô
          const targetBlockId = action.parameters.target_block_id;
          const targetConnectorId = action.parameters.target_connector_id;
          const delay = action.parameters?.delay || 0;
          
          // Î∏îÎ°ù IDÎ°?Î∏îÎ°ù ?¥Î¶Ñ Ï∞æÍ∏∞
          const targetBlock = props.allBlocks.find(b => b.id == targetBlockId);
          const blockName = targetBlock ? targetBlock.name : `Î∏îÎ°ù${targetBlockId}`;
          
          // 'self' ?πÎ≥Ñ Ï≤òÎ¶¨ - ?ÑÏû¨ Î∏îÎ°ù??Ïª§ÎÑ•?∞Î°ú ?¥Îèô
          if (targetConnectorId === 'self') {
            return delay > 0 ? `go to self.${blockName},${delay}` : `go to self.${blockName}`;
          } else {
            // Ïª§ÎÑ•??IDÎ°?Ïª§ÎÑ•???¥Î¶Ñ Ï∞æÍ∏∞
            const targetConnector = targetBlock?.connectionPoints?.find(cp => cp.id === targetConnectorId);
            const connectorName = targetConnector?.name || targetConnectorId;
            
            return delay > 0 ? `go to ${blockName}.${connectorName},${delay}` : `go to ${blockName}.${connectorName}`;
          }
        } else if (action.parameters?.connector_id) {
          // ?ÑÏû¨ Î∏îÎ°ù ??Ïª§ÎÑ•?∞Î°ú ?¥Îèô
          const connectorId = action.parameters.connector_id;
          const connector = props.connectorInfo?.connectionPoints?.find(cp => cp.id === connectorId);
          const connectorName = connector?.name || connectorId;
          const delay = action.parameters?.delay || 0;
          return delay > 0 ? `go to self.${connectorName},${delay}` : `go to self.${connectorName}`;
        } else {
          return `// go to ?Ä?ÅÏù¥ Î™ÖÌôï?òÏ? ?äÏùå`;
        }
        
      case 'action_jump':
        const targetActionName = action.parameters?.target_action_name;
        if (targetActionName) {
          // ?ÄÍ≤??°ÏÖò???∏Îç±??Ï∞æÍ∏∞
          const targetIndex = editableActions.value.findIndex(a => a.name === targetActionName);
          if (targetIndex !== -1) {
            return `jump to ${targetIndex + 1}`;
          } else {
            return `// jump to ${targetActionName} (?Ä?ÅÏùÑ Ï∞æÏùÑ ???ÜÏùå)`;
          }
        } else {
          return `// jump to ?Ä?ÅÏù¥ ?ïÏùò?òÏ? ?äÏùå`;
        }
        
      case 'conditional_branch':
        const script = action.parameters?.script || '';
        if (script.trim()) {
          // Ï°∞Í±¥Î∂Ä ?§Ìñâ ?§ÌÅ¨Î¶ΩÌä∏Î•???ù¥ ?¨Ìï®???ïÌÉúÎ°?Î∞òÌôò
          return script.split('\n').map(line => {
            // ?¥Î? ??ù¥ ?àÎäî Í≤ΩÏö∞ Í∑∏Î?Î°? ?ÜÎäî Í≤ΩÏö∞ ??Ï∂îÍ? ?¨Î? ?êÎã®
            if (line.trim().startsWith('if ')) {
              return line.trim(); // if Î¨∏Ï? ???ÜÏù¥
            } else if (line.trim() && !line.trim().startsWith('//')) {
              return line.startsWith('\t') ? line : '\t' + line.trim(); // ?ºÎ∞ò Î™ÖÎ†π?Ä ??Ï∂îÍ?
            }
            return line; // Îπ?Ï§ÑÏù¥??Ï£ºÏÑù?Ä Í∑∏Î?Î°?
          }).join('\n');
        } else {
          return `// Ï°∞Í±¥Î∂Ä ?§Ìñâ ?§ÌÅ¨Î¶ΩÌä∏Í∞Ä ?ïÏùò?òÏ? ?äÏùå`;
        }
        
      default:
        return `// ${action.type} ?Ä?ÖÏ? ?§ÌÅ¨Î¶ΩÌä∏ Î≥Ä?òÏùÑ ÏßÄ?êÌïòÏßÄ ?äÏùå`;
    }
  } catch (error) {
    console.error(`Ïª§ÎÑ•???°ÏÖò Î≥Ä???§Î•ò (?âÎèô ${lineNumber}):`, error);
    return `// ?âÎèô ${lineNumber}: Î≥Ä???§Î•ò - ${action.name || '?¥Î¶Ñ?ÜÏùå'}`;
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
    
    // Í∏∞Ï°¥ ?âÎèô???†Ï??òÏ? ?äÍ≥† ?§ÌÅ¨Î¶ΩÌä∏ ?¥Ïö©?ºÎ°ú ?ÑÏ≤¥ ÍµêÏ≤¥
    editableActions.value = parsedActions;
    
    // ?îÎ∞î?¥Ïä§???êÎèô ?Ä??
    debouncedAutoSave();
    
    showScriptEditor.value = false; // ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏??´Í∏∞
    console.log(`${parsedActions.length}Í∞úÏùò Ïª§ÎÑ•???âÎèô???§ÌÅ¨Î¶ΩÌä∏Î°úÎ????ÅÏö©?òÏóà?µÎãà??`);
    
    if (parsedActions.length === 0) {
      console.log("?§ÌÅ¨Î¶ΩÌä∏Í∞Ä ÎπÑÏñ¥?àÏñ¥ Î™®Îì† Ïª§ÎÑ•???âÎèô???úÍ±∞?òÏóà?µÎãà??");
    }
    
  } catch (error) {
    scriptParseError.value = `?§ÌÅ¨Î¶ΩÌä∏ ?åÏã± ?§Î•ò: ${error.message}`;
    console.error("Connector Script parsing error:", error);
  }
}

// Í≥†Í∏â ?§ÌÅ¨Î¶ΩÌä∏ ?åÏã± (Ï°∞Í±¥Î∂Ä ?§Ìñâ ÏßÄ??
function parseAdvancedScript(scriptText) {
  const lines = scriptText.split('\n');
  const parsedActions = [];
  let i = 0;
  
  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    // Îπ?Ï§ÑÏù¥??Ï£ºÏÑù?Ä Í±¥ÎÑà?∞Í∏∞
    if (!trimmedLine || trimmedLine.startsWith('//')) {
      i++;
      continue;
    }
    
    // Ï°∞Í±¥Î∂Ä ?§Ìñâ Í∞êÏ?
    if (trimmedLine.startsWith('if ') && !line.startsWith('\t')) {
      // Ï°∞Í±¥Î∂Ä ?§Ìñâ Î∏îÎ°ù ?åÏã±
      const { action, nextIndex } = parseConditionalBranch(lines, i);
      if (action) {
        parsedActions.push(action);
      }
      i = nextIndex;
    } else if (!line.startsWith('\t')) {
      // ?ºÎ∞ò ?°ÏÖò ?åÏã±
      try {
        const action = parseScriptLine(trimmedLine, i + 1);
        if (action) {
          parsedActions.push(action);
        }
      } catch (error) {
        throw new Error(`?ºÏù∏ ${i + 1}: ${error.message}`);
      }
      i++;
    } else {
      // ??úºÎ°??úÏûë?òÎäî Ï§ÑÏ? Ï°∞Í±¥Î∂Ä ?§Ìñâ ?¥Î??¨Ïïº ??
      throw new Error(`?ºÏù∏ ${i + 1}: ??úºÎ°??úÏûë?òÎäî Ï§ÑÏù¥ Ï°∞Í±¥Î∂Ä ?§Ìñâ Î∞ñÏóê ?àÏäµ?àÎã§.`);
    }
  }
  
  return parsedActions;
}

// Ï°∞Í±¥Î∂Ä ?§Ìñâ Î∏îÎ°ù ?åÏã±
function parseConditionalBranch(lines, startIndex) {
  const conditionalScript = [];
  let i = startIndex;
  
  // ?∞ÏÜç??if Î∏îÎ°ù?§ÏùÑ Î™®Îëê ?òÏßë
  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    // Îπ?Ï§ÑÏù¥??Ï£ºÏÑù?Ä Í±¥ÎÑà?∞Í∏∞
    if (!trimmedLine || trimmedLine.startsWith('//')) {
      i++;
      continue;
    }
    
    // if Î∏îÎ°ù???ÑÎãàÎ©?Ï¢ÖÎ£å
    if (!trimmedLine.startsWith('if ') || line.startsWith('\t')) {
      break;
    }
    
    // if Ï°∞Í±¥ Ï∂îÍ?
    conditionalScript.push(line);
    i++;
    
    // ?¥Îãπ if???çÌïò?????§Ïó¨?∞Í∏∞ Ï§ÑÎì§ ?òÏßë
    while (i < lines.length) {
      const subLine = lines[i];
      const subTrimmedLine = subLine.trim();
      
      // Îπ?Ï§ÑÏù¥??Ï£ºÏÑù?Ä Í±¥ÎÑà?∞Í∏∞
      if (!subTrimmedLine || subTrimmedLine.startsWith('//')) {
        i++;
        continue;
      }
      
      // ??úºÎ°??úÏûë?òÏ? ?äÏúºÎ©???if Î∏îÎ°ù Ï¢ÖÎ£å
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
  
  // Ï°∞Í±¥Î∂Ä ?§Ìñâ ?°ÏÖò ?ùÏÑ±
  const action = {
    id: `script-cp-conditional-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    name: `Ï°∞Í±¥Î∂Ä ?§Ìñâ (${conditionalScript.filter(line => line.trim().startsWith('if ')).length}Í∞?Ï°∞Í±¥)`,
    type: 'conditional_branch',
    parameters: {
      script: conditionalScript.join('\n')
    }
  };
  
  return { action, nextIndex: i };
}

function parseScriptLine(line, lineNumber) {
  // delay Î™ÖÎ†π???åÏã±
  if (line.startsWith('delay ')) {
    const duration = parseFloat(line.replace('delay ', ''));
    if (isNaN(duration)) {
      throw new Error(`?ºÏù∏ ${lineNumber}: delay Í∞íÏù¥ ?´ÏûêÍ∞Ä ?ÑÎãô?àÎã§.`);
    }
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `?úÎ†à??${duration}Ï¥?,
      type: 'delay',
      parameters: { duration }
    };
  }
  
  // wait Î™ÖÎ†π???åÏã± (?†Ìò∏Í∞Ä ?πÏ†ï Í∞íÏù¥ ???åÍπåÏßÄ ?ÄÍ∏?
  if (line.startsWith('wait ')) {
    const match = line.match(/^wait\s+(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`?ºÏù∏ ${lineNumber}: wait Î¨∏Î≤ï???òÎ™ª?òÏóà?µÎãà?? ?? wait ?†Ìò∏Î™?= true`);
    }
    const [, signalName, expectedValue] = match;
    const cleanSignalName = signalName.trim();
    
    // ?†Ìò∏Î™??†Ìö®??Í≤Ä??
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`?ºÏù∏ ${lineNumber}: ?†Ìò∏ '${cleanSignalName}'??Ï°¥Ïû¨?òÏ? ?äÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú ?†Ìò∏: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} = ${expectedValue} ÍπåÏ? ?ÄÍ∏?,
      type: 'signal_wait',
      parameters: { 
        signal_name: cleanSignalName, 
        expected_value: expectedValue === 'true' 
      }
    };
  }
  
  // if Î™ÖÎ†π???åÏã± (?†Ìò∏ Ï≤¥ÌÅ¨)
  if (line.startsWith('if ')) {
    const match = line.match(/^if\s+(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`?ºÏù∏ ${lineNumber}: if Î¨∏Î≤ï???òÎ™ª?òÏóà?µÎãà?? ?? if ?†Ìò∏Î™?= true`);
    }
    const [, signalName, expectedValue] = match;
    const cleanSignalName = signalName.trim();
    
    // ?†Ìò∏Î™??†Ìö®??Í≤Ä??
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`?ºÏù∏ ${lineNumber}: ?†Ìò∏ '${cleanSignalName}'??Ï°¥Ïû¨?òÏ? ?äÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú ?†Ìò∏: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} Ï≤¥ÌÅ¨`,
      type: 'signal_check',
      parameters: { 
        signal_name: cleanSignalName, 
        expected_value: expectedValue === 'true' 
      }
    };
  }
  
  // ?†Ìò∏ Î≥ÄÍ≤??åÏã± (?†Ìò∏Î™?= Í∞?
  if (line.includes(' = ')) {
    const match = line.match(/^(.+?)\s*=\s*(true|false)$/);
    if (!match) {
      throw new Error(`?ºÏù∏ ${lineNumber}: ?†Ìò∏ Î≥ÄÍ≤?Î¨∏Î≤ï???òÎ™ª?òÏóà?µÎãà?? ?? ?†Ìò∏Î™?= true`);
    }
    const [, signalName, value] = match;
    const cleanSignalName = signalName.trim();
    
    // ?†Ìò∏Î™??†Ìö®??Í≤Ä??
    if (!props.allSignals.includes(cleanSignalName)) {
      throw new Error(`?ºÏù∏ ${lineNumber}: ?†Ìò∏ '${cleanSignalName}'??Ï°¥Ïû¨?òÏ? ?äÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú ?†Ìò∏: ${props.allSignals.join(', ')}`);
    }
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${cleanSignalName} Î≥ÄÍ≤?,
      type: 'signal_update',
      parameters: { 
        signal_name: cleanSignalName, 
        value: value === 'true' 
      }
    };
  }
  
  // go to Î™ÖÎ†π???åÏã±
  if (line.startsWith('go to ')) {
    const target = line.replace('go to ', '').trim();
    let targetPath = target;
    let delay = 0;
    
    // ?úÎ†à?¥Í? ?¨Ìï®??Í≤ΩÏö∞ ?åÏã± (go to Î∞∞Ï∂ú.load,3)
    if (target.includes(',')) {
      const parts = target.split(',');
      targetPath = parts[0].trim();
      const delayStr = parts[1].trim();
      delay = parseFloat(delayStr);
      if (isNaN(delay)) {
        throw new Error(`?ºÏù∏ ${lineNumber}: ?úÎ†à??Í∞íÏù¥ ?´ÏûêÍ∞Ä ?ÑÎãô?àÎã§: ${delayStr}`);
      }
    }
    
    if (targetPath.startsWith('self.')) {
      // self.Î∏îÎ°ùÎ™??ïÌÉú - ?∞Í≤∞?êÏóê??Î∏îÎ°ù???°ÏÖò?ºÎ°ú ?¥Îèô
      const blockName = targetPath.replace('self.', '').trim();
      
      // Î∏îÎ°ù Ï∞æÍ∏∞ (?¥Î¶Ñ?ºÎ°ú)
      const targetBlock = props.allBlocks.find(block => 
        block.name.toLowerCase() === blockName.toLowerCase()
      );
      
      if (!targetBlock) {
        const availableBlocks = props.allBlocks.map(b => b.name).join(', ');
        throw new Error(`?ºÏù∏ ${lineNumber}: Î∏îÎ°ù '${blockName}'??Ï∞æÏùÑ ???ÜÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú Î∏îÎ°ù: ${availableBlocks}`);
      }
      
      return {
        id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        name: `${blockName} Î∏îÎ°ù ?°ÏÖò?ºÎ°ú ?¥Îèô`,
        type: 'route_to_connector',
        parameters: { 
          target_block_id: targetBlock.id,
          target_connector_id: 'self',
          delay: delay
        }
      };
    } else if (targetPath.includes('.')) {
      // Î∏îÎ°ù?¥Î¶Ñ.?∞Í≤∞?êÏù¥Î¶??ïÌÉú
      const [blockName, connectorName] = targetPath.split('.');
      const cleanBlockName = blockName.trim();
      const cleanConnectorName = connectorName.trim();
      
      // Î∏îÎ°ù Ï∞æÍ∏∞ (?¥Î¶Ñ?ºÎ°ú)
      const targetBlock = props.allBlocks.find(block => 
        block.name.toLowerCase() === cleanBlockName.toLowerCase()
      );
      
      if (!targetBlock) {
        const availableBlocks = props.allBlocks.map(b => b.name).join(', ');
        throw new Error(`?ºÏù∏ ${lineNumber}: Î∏îÎ°ù '${cleanBlockName}'??Ï∞æÏùÑ ???ÜÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú Î∏îÎ°ù: ${availableBlocks}`);
      }
      
      // ?∞Í≤∞??Ï∞æÍ∏∞ (?¥Î¶Ñ?ºÎ°ú)
      const targetConnector = targetBlock.connectionPoints?.find(cp => 
        cp.name?.toLowerCase() === cleanConnectorName.toLowerCase()
      );
      
      if (!targetConnector) {
        const availableConnectors = targetBlock.connectionPoints?.map(cp => cp.name || cp.id).join(', ') || '?ÜÏùå';
        throw new Error(`?ºÏù∏ ${lineNumber}: Î∏îÎ°ù '${cleanBlockName}'?êÏÑú ?∞Í≤∞??'${cleanConnectorName}'??Ï∞æÏùÑ ???ÜÏäµ?àÎã§. ?¨Ïö© Í∞Ä?•Ìïú ?∞Í≤∞?? ${availableConnectors}`);
      }
      
      return {
        id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        name: delay > 0 ? `${cleanBlockName}??${cleanConnectorName}Î°??¥Îèô (${delay}Ï¥??úÎ†à??` : `${cleanBlockName}??${cleanConnectorName}Î°??¥Îèô`,
        type: 'route_to_connector',
        parameters: { 
          target_block_id: targetBlock.id,
          target_connector_id: targetConnector.id,
          delay: delay
        }
      };
    } else {
      throw new Error(`?ºÏù∏ ${lineNumber}: go to ?Ä?ÅÏù¥ ?òÎ™ª?òÏóà?µÎãà?? ?? 'go to Î∞∞Ï∂ú.load' ?êÎäî 'go to self.Í≥µÏ†ï1' ?êÎäî 'go to Î∞∞Ï∂ú.load,3'`);
    }
  }
  
  // jump to Î™ÖÎ†π???åÏã±
  if (line.startsWith('jump to ')) {
    const targetLine = parseInt(line.replace('jump to ', ''));
    if (isNaN(targetLine)) {
      throw new Error(`?ºÏù∏ ${lineNumber}: jump to Í∞íÏù¥ ?´ÏûêÍ∞Ä ?ÑÎãô?àÎã§.`);
    }
    
    if (targetLine < 1 || targetLine > editableActions.value.length) {
      throw new Error(`?ºÏù∏ ${lineNumber}: jump to ?Ä???âÎèô Î≤àÌò∏Í∞Ä Î≤îÏúÑÎ•?Î≤óÏñ¥?¨Ïäµ?àÎã§. (1-${editableActions.value.length})`);
    }
    
    // ?ÑÏû¨ Ï°¥Ïû¨?òÎäî ?°ÏÖò Ï§ëÏóê??targetLineÎ≤àÏß∏ ?°ÏÖò???¥Î¶Ñ??Ï∞æÏïÑ????
    const targetAction = editableActions.value[targetLine - 1];
    const targetActionName = targetAction ? targetAction.name : `?âÎèô ${targetLine}`;
    
    return {
      id: `script-cp-action-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: `${targetActionName}?ºÎ°ú ?¥Îèô`,
      type: 'action_jump',
      parameters: { 
        target_action_name: targetActionName
      }
    };
  }
  
  throw new Error(`?ºÏù∏ ${lineNumber}: ?∏Ïãù?????ÜÎäî Î™ÖÎ†π?¥ÏûÖ?àÎã§: ${line}`);
}

// ?§ÌÅ¨Î¶ΩÌä∏ ?§ÏãúÍ∞??†Ìö®??Í≤Ä??
function validateScriptInput() {
  scriptValidationWarnings.value = [];
  
  if (!scriptInput.value.trim()) {
    return;
  }
  
  try {
    const parsedActions = parseAdvancedScript(scriptInput.value);
    // ?±Í≥µ?ÅÏúºÎ°??åÏã±?òÎ©¥ Í≤ΩÍ≥† ?ÜÏùå
  } catch (error) {
    scriptValidationWarnings.value.push(error.message);
  }
}

// ??Î≤àÌò∏ ?ÖÎç∞?¥Ìä∏ ?®Ïàò
function updateLineNumbers() {
  const lines = scriptInput.value.split('\n');
  scriptLineCount.value = Math.max(lines.length, 1);
}

// ??Î≤àÌò∏?Ä ?çÏä§???ÅÏó≠ ?§ÌÅ¨Î°??ôÍ∏∞??
function syncLineNumbersScroll() {
  if (lineNumbers.value && scriptTextarea.value) {
    lineNumbers.value.scrollTop = scriptTextarea.value.scrollTop;
  }
}

// ?§ÌÅ¨Î¶ΩÌä∏ ?∏ÏßëÍ∏∞Î? ??????Î≤àÌò∏ Ï¥àÍ∏∞??
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
    
    // ?ÑÏû¨ Í∞?Í∞Ä?∏Ïò§Í∏?
    const currentValue = scriptInput.value;
    const newValue = currentValue.substring(0, start) + '\t' + currentValue.substring(end);
    
    // Vue??Î∞òÏùë?±ÏùÑ ?µÌï¥ Í∞??ÖÎç∞?¥Ìä∏
    scriptInput.value = newValue;
    
    // ?§Ïùå ?ÑÎ†à?ÑÏóê??Ïª§ÏÑú ?ÑÏπò ?§Ï†ï
    setTimeout(() => {
      textarea.setSelectionRange(start + 1, start + 1);
      textarea.focus();
    }, 0);
  }
}

// =============== Ï°∞Í±¥Î∂Ä ?§Ìñâ GUI ?∏ÏßëÍ∏??®Ïàò??===============

// Ï°∞Í±¥Î∂Ä ?§Ìñâ GUI Ï¥àÍ∏∞??
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

// ?§ÌÅ¨Î¶ΩÌä∏Î•?GUI ?ïÌÉúÎ°??åÏã±
function parseScriptToGUI(script) {
  try {
    const conditions = [];
    const lines = script.split('\n');
    let i = 0;
    
    while (i < lines.length) {
      const line = lines[i].trim();
      
      // if Î¨?Ï∞æÍ∏∞
      if (line.startsWith('if ')) {
        const ifMatch = line.match(/^if\s+(.+?)\s*=\s*(true|false)$/);
        if (ifMatch) {
          const [, signal, value] = ifMatch;
          const condition = {
            signal: signal.trim(),
            value: value === 'true',
            actions: []
          };
          
          // ?¥Îãπ if???òÏúÑ ?°ÏÖò??Ï∞æÍ∏∞
          i++;
          while (i < lines.length && lines[i].startsWith('\t')) {
            const subLine = lines[i].trim();
            
            if (subLine.includes(' = ')) {
              // ?†Ìò∏ Î≥ÄÍ≤?
              const signalMatch = subLine.match(/^(.+?)\s*=\s*(true|false)$/);
              if (signalMatch) {
                condition.actions.push({
                  type: 'signal_update',
                  signal: signalMatch[1].trim(),
                  value: signalMatch[2] === 'true'
                });
              }
            } else if (subLine.startsWith('delay ')) {
              // ?úÎ†à??
              const duration = parseInt(subLine.replace('delay ', ''));
              condition.actions.push({
                type: 'delay',
                duration: duration
              });
            } else if (subLine.startsWith('go to ')) {
              // Ïª§ÎÑ•?∞Î°ú ?¥Îèô
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
    console.error('?§ÌÅ¨Î¶ΩÌä∏ ?åÏã± ?§Î•ò:', error);
    initializeConditionalGUI();
  }
}

// GUI?êÏÑú ?§ÌÅ¨Î¶ΩÌä∏Î°?Î≥Ä??
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

// Ï°∞Í±¥ Ï∂îÍ?
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

// Ï°∞Í±¥ ?úÍ±∞
function removeCondition(index) {
  if (conditionalConditions.value.length > 1) {
    conditionalConditions.value.splice(index, 1);
    updateConditionalScript();
  }
}

// ?òÏúÑ ?°ÏÖò Ï∂îÍ?
function addSubAction(conditionIndex) {
  conditionalConditions.value[conditionIndex].actions.push({
    type: 'signal_update',
    signal: props.allSignals.length > 0 ? props.allSignals[0] : '',
    value: false
  });
  updateConditionalScript();
}

// ?òÏúÑ ?°ÏÖò ?úÍ±∞
function removeSubAction(conditionIndex, actionIndex) {
  conditionalConditions.value[conditionIndex].actions.splice(actionIndex, 1);
  updateConditionalScript();
}

// ?òÏúÑ ?°ÏÖò ?Ä??Î≥ÄÍ≤????åÎùºÎØ∏ÌÑ∞ Ï¥àÍ∏∞??
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

// Î∏îÎ°ù???∞Î•∏ Ïª§ÎÑ•??Î™©Î°ù Í∞Ä?∏Ïò§Í∏?(ConnectorSettingsPopup??
function getConnectorsForBlock(blockName) {
  if (!blockName) return [];
  const block = props.allBlocks.find(b => b.name === blockName);
  return block ? (block.connectionPoints || []) : [];
}

// ?òÏúÑ ?°ÏÖò??Ïª§ÎÑ•??Î™©Î°ù ?ÖÎç∞?¥Ìä∏
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

// Ïª§ÎÑ•???¥Î¶Ñ Î≥ÄÍ≤?Í∞êÏ??òÏó¨ ?êÎèô ?Ä??
watch(currentConnectorName, () => {
  if (!isInitializingConnector) {
    debouncedAutoSave();
  }
}, { flush: 'sync' });

// scriptInput Î≥ÄÍ≤????§ÏãúÍ∞?Í≤Ä??
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
  overflow: hidden; /* ?§ÌÅ¨Î°§Ï? actions-list?êÏÑú Ï≤òÎ¶¨ */
  display: flex;
  flex-direction: column;
}

.action-item {
</script>

<style scoped>
/* BlockSettingsPopup.vue?Ä ?†ÏÇ¨???§Ì????¨Ïö© Í∞Ä??*/
.connector-settings-popup {
  width: 650px; /* ?àÎπÑ ?ΩÍ∞Ñ Ï¶ùÍ? */
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
  z-index: 999999; /* Îß§Ïö∞ ?íÏ? z-indexÎ°??§Ï†ï */
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

/* Íµ¨Î¨∏ Í∞ïÏ°∞ ?§Ì???*/
.script-command {
  color: #0066cc; /* ?åÎ???- Î™ÖÎ†π??*/
  font-weight: bold;
}

.script-variable {
  color: #cc6600; /* Ï£ºÌô©??- Î≥Ä???†Ìò∏Î™?Î∏îÎ°ùÎ™?*/
  font-weight: normal;
}

.script-variable-valid {
  color: #009900; /* ?πÏÉâ - ?†Ìö®??Î≥Ä???†Ìò∏Î™?Î∏îÎ°ùÎ™?*/
  font-weight: normal;
}

.script-variable-invalid {
  color: #cc0000; /* Îπ®Í∞Ñ??- ?†Ìö®?òÏ? ?äÏ? Î≥Ä??*/
  font-weight: normal;
  text-decoration: underline;
}

.script-value {
  color: #009900; /* ?πÏÉâ - Í∞??´Ïûê/?∞Í≤∞?êÎ™Ö */
  font-weight: normal;
}

.script-operator {
  color: #cc0066; /* ?êÏ£º??- ?∞ÏÇ∞??*/
  font-weight: bold;
}

.script-comment {
  color: #808080; /* ?åÏÉâ - Ï£ºÏÑù */
  font-style: italic;
}

/* Í≥µÌÜµ ?§Ì???*/
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

/* Ï°∞Í±¥Î∂Ä ?§Ìñâ ?§Ì???*/
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

/* Ï°∞Í±¥Î∂Ä ?§Ìñâ ?°ÏÖò ?ÑÏù¥???πÎ≥Ñ ?§Ì???*/
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
  overflow: hidden; /* ?§ÌÅ¨Î°§Ï? actions-list?êÏÑú Ï≤òÎ¶¨ */
  display: flex;
  flex-direction: column;
}

.action-item {
</style> 

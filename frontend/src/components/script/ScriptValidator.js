/**
 * 스크립트 검증 유틸리티
 * 스크립트 문법 검사와 파싱 기능을 제공합니다.
 */

/**
 * 스크립트 전체 검증
 */
export function validateScript(script, props) {
  const errors = []
  const lines = script.split('\n')
  
  console.log('[ScriptValidator] validateScript 시작:', { script, props })
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const lineNum = i + 1
    const lowerLine = line.toLowerCase() // 대소문자 구분 없는 검사를 위해 추가
    
    console.log(`[ScriptValidator] 라인 ${lineNum} 검증:`, { line, lowerLine })
    
    // 빈 줄이나 주석은 건너뛰기
    if (!line || line.startsWith('//')) {
      console.log(`[ScriptValidator] 라인 ${lineNum} 건너뛰기 (빈 줄 또는 주석)`)
      continue
    }
    
    const lineErrors = validateScriptLine(line, lowerLine, lineNum, props)
    console.log(`[ScriptValidator] 라인 ${lineNum} 검증 결과:`, lineErrors)
    errors.push(...lineErrors)
  }
  
  console.log('[ScriptValidator] validateScript 완료:', { valid: errors.length === 0, errors })
  
  return {
    valid: errors.length === 0,
    errors: errors
  }
}

/**
 * 개별 라인 검증
 */
function validateScriptLine(line, lowerLine, lineNum, props) {
  const errors = []
  
  if (lowerLine.startsWith('delay ')) {
    const delayPart = line.replace(/delay /i, '').trim()
    if (!/^(\d+(\.\d+)?|\d+-\d+|[a-zA-Z_][a-zA-Z0-9_]*)$/.test(delayPart)) {
      errors.push(`라인 ${lineNum}: 잘못된 딜레이 형식 "${delayPart}" (예: 5, 3-10)`)
    }
  }
  else if (lowerLine.startsWith('jump to ')) {
    const target = line.replace(/jump to /i, '').trim()
    if (!target) {
      errors.push(`라인 ${lineNum}: jump to 대상이 지정되지 않았습니다`)
    }
  }
  else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('wait ') && !line.trim().toLowerCase().startsWith('log ')) {
    const signalErrors = validateSignalAssignment(line, lineNum, props)
    errors.push(...signalErrors)
  }
  else if (lowerLine.startsWith('wait ')) {
    const waitErrors = validateWaitStatement(line, lineNum, props)
    errors.push(...waitErrors)
  }
  else if (lowerLine.startsWith('go to ') || lowerLine.startsWith('go from ')) {
    const gotoErrors = validateGotoStatement(line, lineNum, props)
    errors.push(...gotoErrors)
  }
  else if (lowerLine.startsWith('if ')) {
    const ifErrors = validateIfStatement(line, lineNum, props)
    errors.push(...ifErrors)
  }
  else if (line.trim().toLowerCase().startsWith('log ')) {
    const logErrors = validateLogStatement(line, lineNum)
    errors.push(...logErrors)
  }
  else if (line.includes('product type +=') || line.includes('product type -=')) {
    // product type 명령은 유효함 - 에러 없음
  }
  else {
    errors.push(`라인 ${lineNum}: 인식되지 않는 명령어 "${line}"`)
  }
  
  return errors
}

/**
 * 신호 할당 검증
 */
function validateSignalAssignment(line, lineNum, props) {
  const errors = []
  const parts = line.split(' = ')
  
  if (parts.length !== 2) {
    errors.push(`라인 ${lineNum}: 잘못된 신호 설정 형식 (예: 신호명 = true)`)
  } else {
    const signalName = parts[0].trim()
    const value = parts[1].trim().toLowerCase()
    
    // 신호 이름 유효성 검사
    if (props.allSignals && props.allSignals.length > 0 && !props.allSignals.includes(signalName)) {
      errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${signalName}"`)
    }
    
    if (value !== 'true' && value !== 'false') {
      errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
    }
  }
  
  return errors
}

/**
 * wait 문 검증
 */
function validateWaitStatement(line, lineNum, props) {
  const errors = []
  const waitPart = line.replace(/wait /i, '').trim()
  
  // product type 조건 체크
  if (waitPart.includes('product type =')) {
    // product type 조건은 항상 유효함
    return errors
  }
  
  // AND 조건 체크
  if (waitPart.includes(' and ')) {
    const conditions = waitPart.split(' and ')
    for (const condition of conditions) {
      const condErrors = validateSingleWaitCondition(condition.trim(), lineNum, props)
      errors.push(...condErrors)
    }
    return errors
  }
  
  // OR 조건 체크
  if (waitPart.includes(' or ')) {
    const conditions = waitPart.split(' or ')
    for (const condition of conditions) {
      const condErrors = validateSingleWaitCondition(condition.trim(), lineNum, props)
      errors.push(...condErrors)
    }
    return errors
  }
  
  // 단일 조건 체크
  const condErrors = validateSingleWaitCondition(waitPart, lineNum, props)
  errors.push(...condErrors)
  
  return errors
}

/**
 * 단일 wait 조건 검증
 */
function validateSingleWaitCondition(condition, lineNum, props) {
  const errors = []
  
  if (!condition.includes(' = ')) {
    errors.push(`라인 ${lineNum}: 잘못된 대기 형식 (예: wait 신호명 = true)`)
  } else {
    const parts = condition.split(' = ')
    if (parts.length === 2) {
      const signalName = parts[0].trim()
      const value = parts[1].trim().toLowerCase()
      
      // 신호 이름 유효성 검사
      if (props.allSignals && props.allSignals.length > 0 && !props.allSignals.includes(signalName)) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${signalName}"`)
      }
      
      if (value !== 'true' && value !== 'false') {
        errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
      }
    }
  }
  
  return errors
}

/**
 * go to 문 검증
 */
function validateGotoStatement(line, lineNum, props) {
  const errors = []
  let target = ''
  
  // go from 처리
  if (line.toLowerCase().startsWith('go from ')) {
    const goFromPattern = /^go\s+from\s+([^\s]+)\s+to\s+(.+)$/i
    const match = line.match(goFromPattern)
    if (match) {
      target = match[2].trim()
    } else {
      errors.push(`라인 ${lineNum}: 잘못된 go from 형식 (예: go from R to 블록명.커넥터명,3)`)
      return errors
    }
  }
  // go to 처리
  else {
    target = line.replace(/go to /i, '').trim()
  }
  
  if (!target) {
    errors.push(`라인 ${lineNum}: go to 대상이 지정되지 않았습니다`)
    return errors
  }
  
  let targetPath = target
  let delay = null
  
  if (target.includes(',')) {
    const parts = target.split(',')
    targetPath = parts[0].trim()
    delay = parts[1].trim()
    
    // 딜레이 형식 검사
    if (delay && !/^(\d+(\.\d+)?|\d+-\d+)$/.test(delay)) {
      errors.push(`라인 ${lineNum}: 잘못된 딜레이 형식 "${delay}" (예: 3, 2-5)`)
    }
  }
  
  // self 라우팅 검증
  if (targetPath.startsWith('self.')) {
    const selfErrors = validateSelfTarget(targetPath, lineNum, props)
    errors.push(...selfErrors)
  }
  // 다른 블록으로 이동 검증
  else if (targetPath.includes('.')) {
    const blockErrors = validateBlockTarget(targetPath, lineNum, props)
    errors.push(...blockErrors)
  }
  
  return errors
}

/**
 * self 타겟 검증
 */
function validateSelfTarget(targetPath, lineNum, props) {
  const errors = []
  const selfTarget = targetPath.replace('self.', '').trim()
  
  if (props.entityType === 'connector') {
    // 커넥터에서는 self.블록명, self.커넥터명 모두 허용
    if (props.currentBlock) {
      // self.블록명 체크 (블록 이름만 허용, 블록 ID는 허용하지 않음)
      const isBlockTarget = (selfTarget === props.currentBlock.name)
      
      // self.커넥터명 체크
      const isConnectorTarget = props.currentBlock.connectionPoints?.some(cp => 
        cp.name === selfTarget
      )
      
      if (!isBlockTarget && !isConnectorTarget) {
        const availableTargets = [
          props.currentBlock.name,
          ...(props.currentBlock.connectionPoints?.map(cp => cp.name).filter(name => name) || [])
        ]
        errors.push(`라인 ${lineNum}: 현재 블록에 "${selfTarget}"로 이동할 수 없습니다 (사용 가능: ${availableTargets.join(', ')})`)
      }
      
      // 블록 ID가 사용된 경우 경고 추가
      if (selfTarget === props.currentBlock.id.toString()) {
        errors.push(`라인 ${lineNum}: 블록 ID "${selfTarget}" 대신 블록 이름 "${props.currentBlock.name}"을 사용해주세요`)
      }
    }
  } else if (props.entityType === 'block') {
    // 블록에서는 self.커넥터명만 허용
    if (props.currentBlock && props.currentBlock.connectionPoints) {
      const connector = props.currentBlock.connectionPoints.find(cp => 
        cp.name === selfTarget
      )
      if (!connector) {
        const availableConnectors = props.currentBlock.connectionPoints.map(cp => cp.name).filter(name => name).join(', ')
        errors.push(`라인 ${lineNum}: 현재 블록에 "${selfTarget}" 커넥터가 없습니다 (사용 가능: ${availableConnectors || '없음'})`)
      }
    }
  }
  
  return errors
}

/**
 * 블록 타겟 검증
 */
function validateBlockTarget(targetPath, lineNum, props) {
  const errors = []
  const [blockName, connectorName] = targetPath.split('.')
  const targetBlock = props.allBlocks.find(b => b.name === blockName.trim())
  
  // 블록 ID가 사용된 경우 감지
  const blockByIdMatch = props.allBlocks.find(b => b.id.toString() === blockName.trim())
  if (blockByIdMatch && !targetBlock) {
    errors.push(`라인 ${lineNum}: 블록 ID "${blockName}" 대신 블록 이름 "${blockByIdMatch.name}"을 사용해주세요`)
  }
  else if (!targetBlock) {
    const availableBlocks = props.allBlocks.map(b => b.name).join(', ')
    errors.push(`라인 ${lineNum}: 존재하지 않는 블록 "${blockName}" (사용 가능: ${availableBlocks || '없음'})`)
  } else {
    const targetConnector = targetBlock.connectionPoints?.find(cp => 
      cp.name === connectorName.trim()
    )
    if (!targetConnector) {
      const availableConnectors = targetBlock.connectionPoints?.map(cp => cp.name).filter(name => name).join(', ')
      errors.push(`라인 ${lineNum}: 블록 "${blockName}"에 "${connectorName}" 커넥터가 없습니다 (사용 가능: ${availableConnectors || '없음'})`)
    }
  }
  
  return errors
}

/**
 * if 문 검증
 */
function validateIfStatement(line, lineNum, props) {
  const errors = []
  const condition = line.replace(/if /i, '').trim()
  
  // product type 조건 체크
  if (condition.includes('product type =')) {
    // product type 조건은 항상 유효함
    return errors
  }
  
  // AND 조건 체크
  if (condition.includes(' and ')) {
    const conditions = condition.split(' and ')
    for (const cond of conditions) {
      const condErrors = validateSingleIfCondition(cond.trim(), lineNum, props)
      errors.push(...condErrors)
    }
    return errors
  }
  
  // OR 조건 체크
  if (condition.includes(' or ')) {
    const conditions = condition.split(' or ')
    for (const cond of conditions) {
      const condErrors = validateSingleIfCondition(cond.trim(), lineNum, props)
      errors.push(...condErrors)
    }
    return errors
  }
  
  // 단일 조건 체크
  const condErrors = validateSingleIfCondition(condition, lineNum, props)
  errors.push(...condErrors)
  
  return errors
}

/**
 * 단일 if 조건 검증
 */
function validateSingleIfCondition(condition, lineNum, props) {
  const errors = []
  
  if (condition.includes(' = ')) {
    const parts = condition.split(' = ')
    if (parts.length === 2) {
      const signalName = parts[0].trim()
      const value = parts[1].trim().toLowerCase()
      
      if (props.allSignals && props.allSignals.length > 0 && !props.allSignals.includes(signalName)) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${signalName}"`)
      }
      
      if (value !== 'true' && value !== 'false') {
        errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
      }
    }
  }
  
  return errors
}

/**
 * log 문 검증
 */
function validateLogStatement(line, lineNum) {
  const errors = []
  const trimmedLine = line.trim()
  const logPart = trimmedLine.replace(/^log /i, '').trim()
  
  // 디버깅을 위한 로그
  console.log('Log validation:', { line, trimmedLine, logPart, lineNum })
  
  // 로그 메시지가 있는지 확인
  if (!logPart) {
    errors.push(`라인 ${lineNum}: 로그 메시지가 지정되지 않았습니다`)
  }
  // 따옴표 검사는 선택적이므로 오류로 처리하지 않음
  
  console.log('Log validation result:', errors)
  return errors
}

/**
 * 스크립트를 액션으로 파싱
 */
export function parseScriptToActions(script, props) {
  const lines = script.split('\n')
  const actions = []
  let actionCounter = 1
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const lineNumber = i + 1
    const lowerLine = line.toLowerCase()
    
    // 빈 줄이나 주석은 건너뛰기
    if (!line || line.startsWith('//')) {
      continue
    }
    
    const action = parseScriptLineToAction(line, lowerLine, lineNumber, actionCounter++, props)
    if (action) {
      actions.push(action)
    }
  }
  
  return actions
}

/**
 * 개별 라인을 액션으로 파싱
 */
function parseScriptLineToAction(line, lowerLine, lineNumber, actionCounter, props) {
  if (lowerLine.startsWith('delay ')) {
    return parseDelayAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('jump to ')) {
    return parseJumpAction(line, actionCounter)
  }
  else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('wait ')) {
    return parseSignalUpdateAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('wait ')) {
    return parseWaitAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('go to ') || lowerLine.startsWith('go from ')) {
    return parseGotoAction(line, lowerLine, lineNumber, actionCounter, props)
  }
  else if (lowerLine.startsWith('if ')) {
    return parseConditionalAction(line, actionCounter, props.script || line)
  }
  else if (lowerLine.startsWith('log ')) {
    return parseLogAction(line, actionCounter)
  }
  else if (line.includes('product type +=') || line.includes('product type -=')) {
    return parseProductTypeAction(line, actionCounter)
  }
  else {
    return parseErrorAction(line, lineNumber, actionCounter, '인식되지 않는 명령어')
  }
}

/**
 * delay 액션 파싱
 */
function parseDelayAction(line, actionCounter) {
  const duration = line.replace(/delay /i, '').trim()
  return {
    id: `script-action-${actionCounter}`,
    name: `딜레이 ${duration}초`,
    type: 'delay',
    parameters: { duration: duration }
  }
}

/**
 * jump to 액션 파싱
 */
function parseJumpAction(line, actionCounter) {
  const target = line.replace(/jump to /i, '').trim()
  return {
    id: `script-action-${actionCounter}`,
    name: `${target}로 점프`,
    type: 'action_jump',
    parameters: { target: target }
  }
}

/**
 * 신호 업데이트 액션 파싱
 */
function parseSignalUpdateAction(line, actionCounter) {
  const [signalName, value] = line.split(' = ').map(s => s.trim())
  return {
    id: `script-action-${actionCounter}`,
    name: `${signalName} = ${value}`,
    type: 'signal_update',
    parameters: { 
      signal_name: signalName, 
      value: value.toLowerCase() === 'true'
    }
  }
}

/**
 * wait 액션 파싱
 */
function parseWaitAction(line, actionCounter) {
  const waitPart = line.replace(/wait /i, '').trim()
  
  // product type 조건
  if (waitPart.includes('product type =')) {
    return {
      id: `script-action-${actionCounter}`,
      name: `${waitPart} 대기`,
      type: 'script',
      parameters: { script: line }
    }
  }
  
  // AND/OR 조건이 있는 경우
  if (waitPart.includes(' and ') || waitPart.includes(' or ')) {
    return {
      id: `script-action-${actionCounter}`,
      name: `${waitPart} 대기`,
      type: 'script',
      parameters: { script: line }
    }
  }
  
  // 단일 신호 조건
  if (waitPart.includes(' = ')) {
    const [signalName, value] = waitPart.split(' = ').map(s => s.trim())
    return {
      id: `script-action-${actionCounter}`,
      name: `${signalName} = ${value} 대기`,
      type: 'signal_wait',
      parameters: { 
        signal_name: signalName, 
        expected_value: value.toLowerCase() === 'true'
      }
    }
  }
  return null
}

/**
 * go to 액션 파싱
 */
function parseGotoAction(line, lowerLine, lineNumber, actionCounter, props) {
  let target = ''
  
  // go from 처리
  if (lowerLine.startsWith('go from ')) {
    const goFromPattern = /^go\s+from\s+([^\s]+)\s+to\s+(.+)$/i
    const match = line.match(goFromPattern)
    if (match) {
      target = match[2].trim()
    } else {
      return parseErrorAction(line, lineNumber, actionCounter, '잘못된 go from 형식')
    }
  }
  // go to 처리
  else {
    target = line.replace(/go to /i, '').trim()
  }
  
  let targetPath = target
  let delay = '0'
  
  // 딜레이 파싱
  if (target.includes(',')) {
    const parts = target.split(',')
    targetPath = parts[0].trim()
    const delayPart = parts[1].trim()
    
    if (/^(\d+(\.\d+)?|\d+-\d+)$/.test(delayPart)) {
      delay = delayPart
    } else {
      return parseErrorAction(line, lineNumber, actionCounter, `잘못된 딜레이 형식: ${delayPart}`)
    }
  }
  
  // self 라우팅 처리
  if (targetPath.startsWith('self.')) {
    return parseSelfGotoAction(line, targetPath, delay, lineNumber, actionCounter, props)
  }
  // 다른 블록으로 이동
  else if (targetPath.includes('.')) {
    return parseBlockGotoAction(line, targetPath, delay, lineNumber, actionCounter, props)
  }
  // 단순 블록 이름만 있는 경우
  else {
    return parseSimpleGotoAction(line, targetPath, delay, lineNumber, actionCounter, props)
  }
}

/**
 * self goto 액션 파싱
 */
function parseSelfGotoAction(line, targetPath, delay, lineNumber, actionCounter, props) {
  const selfTarget = targetPath.replace('self.', '').trim()
  
  if (props.entityType === 'connector') {
    // 커넥터에서는 conditional_branch 액션으로 생성
    return {
      id: `script-action-${actionCounter}`,
      name: `${line}`,
      type: 'conditional_branch',
      parameters: { script: line }
    }
  } else if (props.entityType === 'block') {
    // 블록에서는 route_to_connector 액션으로 생성
    if (props.currentBlock && props.currentBlock.connectionPoints) {
      const connector = props.currentBlock.connectionPoints.find(cp => 
        cp.name === selfTarget
      )
      if (connector) {
        return {
          id: `script-action-${actionCounter}`,
          name: `${targetPath}로 이동`,
          type: 'route_to_connector',
          parameters: { 
            connector_id: connector.id,
            delay: delay,
            target_block_name: 'self',
            target_connector_name: selfTarget
          }
        }
      }
    }
    
    return parseErrorAction(line, lineNumber, actionCounter, `존재하지 않는 커넥터: ${selfTarget}`)
  }
  
  return null
}

/**
 * 블록 goto 액션 파싱
 */
function parseBlockGotoAction(line, targetPath, delay, lineNumber, actionCounter, props) {
  const [blockName, connectorName] = targetPath.split('.')
  const targetBlock = props.allBlocks.find(b => b.name === blockName.trim())
  
  if (!targetBlock) {
    return parseErrorAction(line, lineNumber, actionCounter, `존재하지 않는 블록: ${blockName}`)
  }
  
  const targetConnector = targetBlock.connectionPoints?.find(cp => 
    cp.name === connectorName.trim()
  )
  
  if (!targetConnector) {
    return parseErrorAction(line, lineNumber, actionCounter, `블록 "${blockName}"에 "${connectorName}" 커넥터가 없습니다`)
  }
  
  return {
    id: `script-action-${actionCounter}`,
    name: `${blockName}.${connectorName}로 이동`,
    type: 'route_to_connector',
    parameters: { 
      target_block_id: targetBlock.id,
      target_connector_id: targetConnector.id,
      delay: delay,
      target_block_name: blockName.trim(),
      target_connector_name: connectorName.trim()
    }
  }
}

/**
 * 단순 goto 액션 파싱
 */
function parseSimpleGotoAction(line, targetPath, delay, lineNumber, actionCounter, props) {
  const targetBlock = props.allBlocks.find(b => b.name === targetPath.trim())
  
  if (!targetBlock) {
    return parseErrorAction(line, lineNumber, actionCounter, `존재하지 않는 블록: ${targetPath}`)
  }
  
  return {
    id: `script-action-${actionCounter}`,
    name: `${targetPath}로 이동`,
    type: 'route_to_connector',
    parameters: { 
      target_block_id: targetBlock.id,
      target_connector_id: 'self',
      delay: delay,
      target_block_name: targetPath.trim(),
      target_connector_name: 'self'
    }
  }
}

/**
 * 조건부 실행 액션 파싱
 */
function parseConditionalAction(line, actionCounter, script) {
  return {
    id: `script-action-${actionCounter}`,
    name: '조건부 실행',
    type: 'conditional_branch',
    parameters: { script: script }
  }
}

/**
 * 오류 액션 생성
 */
function parseErrorAction(line, lineNumber, actionCounter, error) {
  return {
    id: `script-action-${actionCounter}`,
    name: `❌ 오류: ${line}`,
    type: 'script_error',
    parameters: { 
      originalLine: line,
      lineNumber: lineNumber,
      error: error
    }
  }
}

/**
 * log 액션 파싱
 */
function parseLogAction(line, actionCounter) {
  const logMessage = line.replace(/log /i, '').trim()
  // 따옴표 제거
  const cleanMessage = logMessage.replace(/^"|"$/g, '')
  
  return {
    id: `script-action-${actionCounter}`,
    name: `로그: ${cleanMessage}`,
    type: 'script',
    parameters: { script: line }
  }
}

/**
 * product type 액션 파싱
 */
function parseProductTypeAction(line, actionCounter) {
  const isAdd = line.includes('product type +=')
  const operation = isAdd ? '추가' : '제거'
  const params = line.split(isAdd ? 'product type +=' : 'product type -=')[1].trim()
  
  return {
    id: `script-action-${actionCounter}`,
    name: `제품 타입 ${operation}: ${params}`,
    type: 'script',
    parameters: { script: line }
  }
} 
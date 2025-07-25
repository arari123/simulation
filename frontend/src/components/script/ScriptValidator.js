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
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const lineNum = i + 1
    const lowerLine = line.toLowerCase() // 대소문자 구분 없는 검사를 위해 추가
    
    // 빈 줄이나 주석은 건너뛰기
    if (!line || line.startsWith('//')) {
      continue
    }
    
    const lineErrors = validateScriptLine(line, lowerLine, lineNum, props)
    errors.push(...lineErrors)
  }
  
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
  
  // execute 명령어 특별 체크
  // 디버깅 코드 제거됨
  
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
  else if (lowerLine.startsWith('int ')) {
    const intErrors = validateIntOperation(line, lineNum, props)
    errors.push(...intErrors)
  }
  else if (lowerLine.startsWith('execute ')) {
    const executeErrors = validateExecuteStatement(line, lineNum, props)
    errors.push(...executeErrors)
  }
  else if (line.match(/^product\s+type\(\d+\)\s*=\s*.+$/)) {
    // product type(index) = value 형식은 유효함 - 에러 없음
  }
  else if (line.includes('.status = ')) {
    // 블록 상태 명령 (블록이름.status = "값")
    const statusErrors = validateBlockStatusAssignment(line, lineNum, props)
    errors.push(...statusErrors)
  }
  else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('elif ') && !lowerLine.startsWith('wait ') && !line.trim().toLowerCase().startsWith('log ') && !lowerLine.startsWith('int ')) {
    // 신호 설정 명령
    const signalErrors = validateSignalAssignment(line, lineNum, props)
    errors.push(...signalErrors)
  }
  else if (lowerLine.startsWith('wait ')) {
    const waitErrors = validateWaitStatement(line, lineNum, props)
    errors.push(...waitErrors)
  }
  else if (lowerLine.startsWith('go to ')) {
    errors.push(`라인 ${lineNum}: "go to" 명령은 더 이상 지원되지 않습니다. "go" 명령을 사용해주세요 (예: go R to 공정1.L(0,3))`)
  }
  else if (lowerLine.startsWith('go ') && !lowerLine.startsWith('go to ')) {
    const gotoErrors = validateGotoStatement(line, lineNum, props)
    errors.push(...gotoErrors)
  }
  else if (lowerLine.startsWith('if ') || lowerLine === 'if') {
    const ifErrors = validateIfStatement(line, lineNum, props)
    errors.push(...ifErrors)
  }
  else if (lowerLine.startsWith('elif ') || lowerLine === 'elif') {
    const elifLine = lowerLine === 'elif' ? 'if' : line.replace(/^elif\s+/i, 'if ')
    const elifErrors = validateIfStatement(elifLine, lineNum, props)
    errors.push(...elifErrors)
  }
  else if (line.trim().toLowerCase() === 'else') {
    // else는 조건이 없으므로 별도 검증 없음
  }
  else if (line.trim().toLowerCase().startsWith('log ')) {
    const logErrors = validateLogStatement(line, lineNum)
    errors.push(...logErrors)
  }
  else if (line.includes('product type +=') || line.includes('product type -=')) {
    // product type 명령은 유효함 - 에러 없음
  }
  else if (line.trim() === 'create product' || line.trim() === 'dispose product' || line.trim() === 'force execution') {
    // 엔티티 관련 명령어는 유효함 - 에러 없음
  }
  else {
    errors.push(`라인 ${lineNum}: 인식되지 않는 명령어 "${line}"`)
  }
  
  return errors
}

/**
 * execute 명령 검증
 */
function validateExecuteStatement(line, lineNum, props) {
  const errors = []
  const targetBlock = line.replace(/execute /i, '').trim()
  
  if (!targetBlock) {
    errors.push(`라인 ${lineNum}: execute 명령에 대상 블록이 지정되지 않았습니다`)
  } else if (props.allBlocks && props.allBlocks.length > 0) {
    // 블록 이름 검증
    const blockExists = props.allBlocks.some(block => block.name === targetBlock)
    if (!blockExists) {
      errors.push(`라인 ${lineNum}: 존재하지 않는 블록 "${targetBlock}"`)
    }
  }
  
  return errors
}

/**
 * 정수 변수 연산 검증
 */
function validateIntOperation(line, lineNum, props) {
  const errors = []
  
  // int 변수명 연산자 값 형식 파싱 (한글 변수명 지원)
  const intMatch = line.match(/^int\s+([a-zA-Z0-9_가-힣]+)\s*([\+\-\*\/]?=)\s*(.+)$/)
  
  if (!intMatch) {
    errors.push(`라인 ${lineNum}: 잘못된 int 명령어 형식 (예: int counter += 5)`)
    return errors
  }
  
  const varName = intMatch[1]
  const operator = intMatch[2]
  const value = intMatch[3].trim()
  
  // 연산자 유효성 검사
  const validOperators = ['=', '+=', '-=', '*=', '/=']
  if (!validOperators.includes(operator)) {
    errors.push(`라인 ${lineNum}: 잘못된 연산자 "${operator}" (사용 가능: =, +=, -=, *=, /=)`)
  }
  
  // 값 유효성 검사 - 숫자 또는 변수명 (한글 포함)
  if (!/^-?\d+$/.test(value) && !/^[a-zA-Z_가-힣][a-zA-Z0-9_가-힣]*$/.test(value)) {
    errors.push(`라인 ${lineNum}: 잘못된 값 "${value}" (정수 또는 변수명이어야 합니다)`)
  }
  
  // 0으로 나누기 검사
  if (operator === '/=' && value === '0') {
    errors.push(`라인 ${lineNum}: 0으로 나눌 수 없습니다`)
  }
  
  return errors
}

/**
 * 블록 상태 설정 문 검증
 */
function validateBlockStatusAssignment(line, lineNum, props) {
  const errors = []
  const parts = line.split('.status = ')
  
  if (parts.length !== 2) {
    errors.push(`라인 ${lineNum}: 잘못된 블록 상태 설정 형식 (예: 블록이름.status = "running")`)
  } else {
    const blockName = parts[0].trim()
    const statusValue = parts[1].trim()
    
    // 블록 이름 유효성 검사
    if (props.allBlocks && props.allBlocks.length > 0) {
      const blockExists = props.allBlocks.some(block => block.name === blockName)
      if (!blockExists) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 블록 "${blockName}"`)
      }
    }
    
    // 상태 값이 따옴표로 감싸져 있는지 확인
    if (!((statusValue.startsWith('"') && statusValue.endsWith('"')) || 
          (statusValue.startsWith("'") && statusValue.endsWith("'")))) {
      errors.push(`라인 ${lineNum}: 상태 값은 따옴표로 감싸야 합니다 (예: "running" 또는 'idle')`)
    } else if (statusValue.length <= 2) {
      errors.push(`라인 ${lineNum}: 빈 상태 값은 허용되지 않습니다`)
    }
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
  
  // 정수 비교 연산자 확인
  const intOperators = ['>=', '<=', '!=', '>', '<', '=']
  let hasIntOperator = false
  let usedOperator = null
  
  for (const op of intOperators) {
    if (condition.includes(` ${op} `)) {
      hasIntOperator = true
      usedOperator = op
      break
    }
  }
  
  if (!hasIntOperator) {
    errors.push(`라인 ${lineNum}: 잘못된 대기 형식 (예: wait 신호명 = true 또는 wait counter > 5)`)
    return errors
  }
  
  const parts = condition.split(` ${usedOperator} `)
  if (parts.length === 2) {
    const leftSide = parts[0].trim()
    const rightSide = parts[1].trim()
    
    // 정수 비교인지 확인 (값이 숫자이거나 변수명인 경우)
    if (/^-?\d+$/.test(rightSide) || /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(rightSide)) {
      // 정수 비교 - 추가 검증 없음 (런타임에 확인)
      return errors
    }
    
    // 불린 비교
    if (usedOperator === '=') {
      const value = rightSide.toLowerCase()
      
      // 신호 이름 유효성 검사
      if (props.allSignals && props.allSignals.length > 0 && !props.allSignals.includes(leftSide)) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${leftSide}"`)
      }
      
      if (value !== 'true' && value !== 'false') {
        errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
      }
    }
  }
  
  return errors
}

/**
 * go 문 검증 (새로운 형식: go R to 블록.커넥터(0,3))
 */
function validateGotoStatement(line, lineNum, props) {
  const errors = []
  
  // 새로운 go 형식 파싱: go R to 블록.커넥터(0,3)
  const goPattern = /^go\s+([^\s]+)\s+to\s+([^(]+)(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$/i
  const match = line.match(goPattern)
  
  if (!match) {
    errors.push(`라인 ${lineNum}: 잘못된 go 형식 (예: go R to 블록.L(0,3))`)
    return errors
  }
  
  const fromConnector = match[1].trim()
  const toTarget = match[2].trim()
  const entityIndex = match[3]  // 엔티티 인덱스 (옵션)
  const delay = match[4]  // 딜레이 (옵션)
  
  // 출발 커넥터 유효성 검사
  if (props.currentBlock && props.currentBlock.connectionPoints) {
    const foundConnector = props.currentBlock.connectionPoints.find(cp => cp.name === fromConnector)
    if (!foundConnector) {
      const availableConnectors = props.currentBlock.connectionPoints.map(cp => cp.name).filter(name => name).join(', ')
      errors.push(`라인 ${lineNum}: 현재 블록에 "${fromConnector}" 커넥터가 없습니다 (사용 가능: ${availableConnectors || '없음'})`)
    }
  }
  
  // 도착 대상 검사
  if (toTarget.includes('.')) {
    const [blockName, connectorName] = toTarget.split('.')
    const targetBlock = props.allBlocks.find(b => b.name === blockName.trim())
    
    if (!targetBlock) {
      errors.push(`라인 ${lineNum}: 존재하지 않는 블록: ${blockName}`)
    } else {
      const targetConnector = targetBlock.connectionPoints?.find(cp => 
        cp.name === connectorName.trim()
      )
      
      if (!targetConnector) {
        errors.push(`라인 ${lineNum}: 블록 "${blockName}"에 "${connectorName}" 커넥터가 없습니다`)
      }
    }
  } else {
    errors.push(`라인 ${lineNum}: go 명령의 도착지는 "블록명.커넥터명" 형식이어야 합니다`)
  }
  
  // 딜레이 형식 검사
  if (delay && !/^(\d+(\.\d+)?|\d+-\d+)$/.test(delay)) {
    errors.push(`라인 ${lineNum}: 잘못된 딜레이 형식 "${delay}" (예: 3, 2-5)`)
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
  
  // 조건이 없으면 오류
  if (!condition) {
    errors.push(`라인 ${lineNum}: 조건이 없습니다`)
    return errors
  }
  
  // product type 조건 체크
  if (condition.includes('product type =') || condition.includes('product type !=') || 
      condition.match(/product\s+type\(\d+\)\s*=/) || condition.match(/product\s+type\(\d+\)\s*!=/)) {
    // product type 조건은 항상 유효함 (인덱스 문법 및 != 연산자 포함)
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
  
  // 정수 비교 연산자 확인
  const intOperators = ['>=', '<=', '!=', '>', '<', '=']
  let hasOperator = false
  let usedOperator = null
  
  for (const op of intOperators) {
    if (condition.includes(` ${op} `)) {
      hasOperator = true
      usedOperator = op
      break
    }
  }
  
  if (!hasOperator) {
    errors.push(`라인 ${lineNum}: 조건문에 비교 연산자가 없습니다`)
    return errors
  }
  
  const parts = condition.split(` ${usedOperator} `)
  if (parts.length === 2) {
    const leftSide = parts[0].trim()
    const rightSide = parts[1].trim()
    
    // 정수 비교인지 확인 (값이 숫자이거나 변수명인 경우)
    if (/^-?\d+$/.test(rightSide) || /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(rightSide)) {
      // 정수 비교 - 추가 검증 없음 (런타임에 확인)
      return errors
    }
    
    // 불린 비교
    if (usedOperator === '=') {
      const value = rightSide.toLowerCase()
      
      if (props.allSignals && props.allSignals.length > 0 && !props.allSignals.includes(leftSide)) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${leftSide}"`)
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
  
  // 로그 메시지가 있는지 확인
  if (!logPart) {
    errors.push(`라인 ${lineNum}: 로그 메시지가 지정되지 않았습니다`)
  }
  // 따옴표 검사는 선택적이므로 오류로 처리하지 않음
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
  else if (lowerLine.startsWith('int ')) {
    return parseIntOperationAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('execute ')) {
    return parseExecuteAction(line, actionCounter)
  }
  else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('elif ') && !lowerLine.startsWith('wait ') && !lowerLine.startsWith('int ')) {
    return parseSignalUpdateAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('wait ')) {
    return parseWaitAction(line, actionCounter)
  }
  else if (lowerLine.startsWith('go to ')) {
    return parseErrorAction(line, lineNumber, actionCounter, '"go to" 명령은 더 이상 지원되지 않습니다. "go" 명령을 사용해주세요 (예: go R to 공정1.L(0,3))')
  }
  else if (lowerLine.startsWith('go ') && !lowerLine.startsWith('go to ')) {
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
  else if (line.trim() === 'create product' || line.trim() === 'dispose product' || line.trim() === 'force execution') {
    return parseScriptAction(line, actionCounter)
  }
  else {
    return parseErrorAction(line, lineNumber, actionCounter, '인식되지 않는 명령어')
  }
}

/**
 * execute 액션 파싱
 */
function parseExecuteAction(line, actionCounter) {
  const targetBlock = line.replace(/execute /i, '').trim()
  return {
    id: `script-action-${actionCounter}`,
    name: `블록 "${targetBlock}" 실행`,
    type: 'script',
    parameters: { script: line }
  }
}

/**
 * 스크립트 액션 파싱 (create product, dispose product, force execution 등)
 */
function parseScriptAction(line, actionCounter) {
  return {
    id: `script-action-${actionCounter}`,
    name: line,
    type: 'script',
    parameters: { script: line }
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
 * go 액션 파싱 (새로운 형식)
 */
function parseGotoAction(line, lowerLine, lineNumber, actionCounter, props) {
  // 새로운 go 형식: go R to 블록.커넥터(0,3)
  // 백엔드로 전체 스크립트를 전달하여 처리
  return {
    id: `script-action-${actionCounter}`,
    name: 'go 명령 실행',
    type: 'script',
    parameters: { 
      script: line
    }
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

/**
 * int 연산 액션 파싱
 */
function parseIntOperationAction(line, actionCounter) {
  const intMatch = line.match(/^int\s+(\w+)\s*([\+\-\*\/]?=)\s*(.+)$/)
  
  if (!intMatch) {
    return parseErrorAction(line, 0, actionCounter, '잘못된 int 명령어 형식')
  }
  
  const varName = intMatch[1]
  const operator = intMatch[2]
  const value = intMatch[3].trim()
  
  return {
    id: `script-action-${actionCounter}`,
    name: `정수 변수: ${varName} ${operator} ${value}`,
    type: 'script',
    parameters: { script: line }
  }
} 
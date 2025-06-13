// 주석을 제거하는 헬퍼 함수
function removeComment(line) {
  const commentIndex = line.indexOf('//')
  if (commentIndex !== -1) {
    return line.substring(0, commentIndex).trim()
  }
  return line.trim()
}

// 단일 wait/if 조건 검증 헬퍼 함수
function validateSingleWaitCondition(condition, lineNum, errors, allSignals) {
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
    errors.push(`라인 ${lineNum}: 잘못된 조건 형식 "${condition}" (예: 신호명 = true 또는 counter > 5)`)
    return
  }
  
  const parts = condition.split(` ${usedOperator} `)
  if (parts.length === 2) {
    const leftSide = parts[0].trim()
    const rightSide = parts[1].trim()
    
    // 정수 비교인지 확인 (값이 숫자이거나 변수명인 경우)
    if (/^-?\d+$/.test(rightSide) || /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(rightSide)) {
      // 정수 비교 - 추가 검증 없음 (런타임에 확인)
      return
    }
    
    // 불린 비교
    if (usedOperator === '=') {
      const value = rightSide.toLowerCase()
      
      // 신호 이름 유효성 검사
      if (allSignals && allSignals.length > 0 && !allSignals.includes(leftSide)) {
        errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${leftSide}"`)
      }
      
      if (value !== 'true' && value !== 'false') {
        errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
      }
    }
  }
}

// 스크립트 검증 함수
export function validateScript(script, allSignals, allBlocks, currentBlock, entityType) {
  const errors = []
  const lines = script.split('\n')
  
  for (let i = 0; i < lines.length; i++) {
    const originalLine = lines[i].trim()
    const lineNum = i + 1
    
    // 빈 줄이나 주석은 건너뛰기
    if (!originalLine || originalLine.startsWith('//')) {
      continue
    }
    
    // 주석 제거 후 검증
    const line = removeComment(originalLine).trim()  // trim 추가
    const lowerLine = line.toLowerCase()
    
    // 주석 제거 후 빈 줄이면 건너뛰기
    if (!line) {
      continue
    }
    
    if (lowerLine.startsWith('delay ')) {
      const delayPart = line.replace(/delay /i, '').trim()
      // 숫자 또는 숫자 범위만 허용 (변수명 제외)
      if (!/^(\d+(\.\d+)?|\d+-\d+)$/.test(delayPart)) {
        errors.push(`라인 ${lineNum}: 잘못된 딜레이 형식 "${delayPart}" (예: 5, 3.5, 3-10)`)
      }
    }
    else if (lowerLine.startsWith('jump to ')) {
      const target = line.replace(/jump to /i, '').trim()
      if (!target) {
        errors.push(`라인 ${lineNum}: jump to 대상이 지정되지 않았습니다`)
      }
    }
    else if (lowerLine.startsWith('int ')) {
      // int 변수명 연산자 값 형식 검증 (한글 변수명 지원)
      const intMatch = line.match(/^int\s+([a-zA-Z0-9_가-힣]+)\s*([\+\-\*\/]?=)\s*(.+)$/)
      
      if (!intMatch) {
        errors.push(`라인 ${lineNum}: 잘못된 int 명령어 형식 (예: int counter += 5)`)
      } else {
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
      }
    }
    else if (line.match(/^product\s+type\(\d+\)\s*=\s*.+$/)) {
      // product type(index) = value 형식은 유효함
    }
    else if (line.includes('.status = ')) {
      // 블록 상태 명령 (블록이름.status = "값")
      const parts = line.split('.status = ')
      if (parts.length !== 2) {
        errors.push(`라인 ${lineNum}: 잘못된 블록 상태 설정 형식 (예: 블록이름.status = "running")`)
      } else {
        const blockName = parts[0].trim()
        const statusValue = parts[1].trim()
        
        // 블록 이름 유효성 검사
        if (allBlocks && allBlocks.length > 0) {
          const blockExists = allBlocks.some(block => block.name === blockName)
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
    }
    else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('elif ') && !lowerLine.startsWith('wait ') && !lowerLine.startsWith('int ')) {
      const parts = line.split(' = ')
      if (parts.length !== 2) {
        errors.push(`라인 ${lineNum}: 잘못된 신호 설정 형식 (예: 신호명 = true)`)
      } else {
        const signalName = parts[0].trim()
        const value = parts[1].trim().toLowerCase()
        
        // 신호 이름 유효성 검사
        if (allSignals && allSignals.length > 0 && !allSignals.includes(signalName)) {
          errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${signalName}"`)
        }
        
        if (value !== 'true' && value !== 'false') {
          errors.push(`라인 ${lineNum}: 신호 값은 true 또는 false여야 합니다`)
        }
      }
    }
    else if (lowerLine.startsWith('wait ')) {
      const waitPart = line.replace(/wait /i, '').trim()
      
      // product type 조건은 유효함
      if (waitPart.includes('product type =')) {
        // product type 조건은 항상 유효함
      }
      // AND 조건 처리
      else if (waitPart.toLowerCase().includes(' and ')) {
        const conditions = waitPart.split(/\s+and\s+/i)
        for (const condition of conditions) {
          validateSingleWaitCondition(condition.trim(), lineNum, errors, allSignals)
        }
      }
      // OR 조건 처리
      else if (waitPart.toLowerCase().includes(' or ')) {
        const conditions = waitPart.split(/\s+or\s+/i)
        for (const condition of conditions) {
          validateSingleWaitCondition(condition.trim(), lineNum, errors, allSignals)
        }
      } else {
        // Simple wait condition
        validateSingleWaitCondition(waitPart, lineNum, errors, allSignals)
      }
    }
    else if (lowerLine.startsWith('go ') && !lowerLine.startsWith('go to ')) {
      // 새로운 "go R to 공정1.L(0,3)" 형식
      const goPattern = /^go\s+([^\s]+)\s+to\s+([^(]+)(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$/i
      const match = line.match(goPattern)
      
      if (!match) {
        errors.push(`라인 ${lineNum}: 잘못된 go 형식 (예: go R to 공정1.L(0,3))`)
      } else {
        const fromConnector = match[1].trim()
        const toTarget = match[2].trim()
        const entityIndex = match[3]  // 엔티티 인덱스 (옵션)
        const delay = match[4]  // 딜레이 (옵션)
        
        // 출발 커넥터 유효성 검사
        if (currentBlock && currentBlock.connectionPoints) {
          const foundConnector = currentBlock.connectionPoints.find(cp => cp.name === fromConnector)
          if (!foundConnector) {
            const availableConnectors = currentBlock.connectionPoints.map(cp => cp.name).filter(name => name).join(', ')
            errors.push(`라인 ${lineNum}: 현재 블록에 "${fromConnector}" 커넥터가 없습니다 (사용 가능: ${availableConnectors || '없음'})`)
          }
        }
        
        // 도착 대상 검사
        if (toTarget.includes('.')) {
          const [blockName, connectorName] = toTarget.split('.')
          const targetBlock = allBlocks.find(b => b.name.toLowerCase() === blockName.trim().toLowerCase())
          
          if (!targetBlock) {
            errors.push(`라인 ${lineNum}: 존재하지 않는 블록: ${blockName}`)
          } else {
            const targetConnector = targetBlock.connectionPoints?.find(cp => 
              cp.name.toLowerCase() === connectorName.trim().toLowerCase()
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
      }
    }
    else if (lowerLine.startsWith('go to ')) {
      errors.push(`라인 ${lineNum}: "go to" 명령은 더 이상 지원되지 않습니다. "go" 명령을 사용해주세요 (예: go R to 블록명.L(0,3))`)
    }
    else if (lowerLine.startsWith('if ') || lowerLine === 'if') {
      // 조건부 실행의 신호 이름도 검사
      const condition = line.replace(/if /i, '').trim()
      
      // 조건이 없으면 오류
      if (!condition) {
        errors.push(`라인 ${lineNum}: if 문에 조건이 없습니다`)
      }
      // product type 조건은 유효함
      else if (condition.includes('product type =')) {
        // product type 조건은 항상 유효함
      }
      // AND 조건 처리
      else if (condition.toLowerCase().includes(' and ')) {
        const conditions = condition.split(/\s+and\s+/i)
        for (const cond of conditions) {
          validateSingleWaitCondition(cond.trim(), lineNum, errors, allSignals)
        }
      }
      // OR 조건 처리
      else if (condition.toLowerCase().includes(' or ')) {
        const conditions = condition.split(/\s+or\s+/i)
        for (const cond of conditions) {
          validateSingleWaitCondition(cond.trim(), lineNum, errors, allSignals)
        }
      }
      // 단일 조건
      else {
        validateSingleWaitCondition(condition, lineNum, errors, allSignals)
      }
    }
    else if (lowerLine.startsWith('elif ') || lowerLine === 'elif') {
      // elif도 if와 동일하게 처리
      const condition = line.replace(/elif /i, '').trim()
      
      // 조건이 없으면 오류
      if (!condition) {
        errors.push(`라인 ${lineNum}: elif 문에 조건이 없습니다`)
      }
      // product type 조건은 유효함
      else if (condition.includes('product type =')) {
        // product type 조건은 항상 유효함
      }
      // AND 조건 처리
      else if (condition.toLowerCase().includes(' and ')) {
        const conditions = condition.split(/\s+and\s+/i)
        for (const cond of conditions) {
          validateSingleWaitCondition(cond.trim(), lineNum, errors, allSignals)
        }
      }
      // OR 조건 처리
      else if (condition.toLowerCase().includes(' or ')) {
        const conditions = condition.split(/\s+or\s+/i)
        for (const cond of conditions) {
          validateSingleWaitCondition(cond.trim(), lineNum, errors, allSignals)
        }
      }
      // 단일 조건
      else {
        validateSingleWaitCondition(condition, lineNum, errors, allSignals)
      }
    }
    else if (lowerLine === 'else') {
      // else는 조건이 없으므로 별도 검증 없음
    }
    else if (lowerLine.startsWith('log ')) {
      const logMessage = line.replace(/log /i, '').trim()
      if (!logMessage) {
        errors.push(`라인 ${lineNum}: 로그 메시지가 지정되지 않았습니다`)
      }
      // 따옴표 검사는 선택사항이므로 에러로 처리하지 않음
    }
    else if (line.includes('product type +=') || line.includes('product type -=') || line.match(/^product\s+type\s*=\s*.+$/)) {
      // product type 명령은 항상 유효함 (=, +=, -= 모두 포함)
    }
    else if (lowerLine === 'create product') {
      // create product 명령은 항상 유효함
    }
    else if (lowerLine === 'dispose product') {
      // dispose product 명령은 항상 유효함
    }
    else if (lowerLine === 'force execution') {
      // force execution 명령은 첫 번째 줄에만 유효함
      if (lineNum !== 1) {
        errors.push(`라인 ${lineNum}: "force execution"은 첫 번째 줄에만 사용할 수 있습니다`)
      }
    }
    else if (lowerLine.startsWith('execute ')) {
      // execute 명령어 검증
      const targetBlock = line.replace(/execute /i, '').trim()
      
      if (!targetBlock) {
        errors.push(`라인 ${lineNum}: execute 명령에 대상 블록이 지정되지 않았습니다`)
      } else if (allBlocks && allBlocks.length > 0) {
        // 블록 이름 검증
        const blockExists = allBlocks.some(block => block.name === targetBlock)
        if (!blockExists) {
          errors.push(`라인 ${lineNum}: 존재하지 않는 블록 "${targetBlock}"`)
        }
      }
    }
    else {
      errors.push(`라인 ${lineNum}: 인식되지 않는 명령어 "${line}"`)
    }
  }
  
  return {
    valid: errors.length === 0,
    errors: errors
  }
}

// 스크립트를 액션으로 파싱하는 함수
export function parseScriptToActions(script, allBlocks, currentBlock, entityType) {
  const lines = script.split('\n')
  const actions = []
  let actionCounter = 1
  
  // Check if the entire script is a multi-line conditional script
  // This happens when editing an existing conditional_branch action
  const firstLine = lines[0]?.trim().toLowerCase() || ''
  const hasComplexWait = firstLine.startsWith('wait ') && (firstLine.includes(' or ') || firstLine.includes(' and '))
  const hasIfStatement = lines.some(line => {
    const trimmed = line.trim().toLowerCase()
    return trimmed.startsWith('if ') || trimmed.startsWith('elif ') || trimmed === 'else'
  })
  const hasProductType = lines.some(line => line.includes('product type +=') || line.includes('product type -='))
  const hasLog = lines.some(line => line.trim().toLowerCase().startsWith('log '))
  const hasCreateEntity = lines.some(line => line.trim().toLowerCase() === 'create product')
  const hasDisposeEntity = lines.some(line => line.trim().toLowerCase() === 'dispose product')
  const hasForceExecution = lines.some(line => line.trim().toLowerCase() === 'force execution')
  const hasIntCommand = lines.some(line => line.trim().toLowerCase().startsWith('int '))
  
  // If script contains complex wait, if statements, product type, log, create entity, dispose entity, force execution, or int commands, treat entire script as script type
  if (hasComplexWait || hasIfStatement || hasProductType || hasLog || hasCreateEntity || hasDisposeEntity || hasForceExecution || hasIntCommand) {
    actions.push({
      id: `script-action-${actionCounter++}`,
      name: '스크립트 실행',
      type: 'script',
      parameters: { 
        script: script  // Keep the entire script as-is
      }
    })
    return actions
  }
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const lineNumber = i + 1
    const lowerLine = line.toLowerCase()
    
    // 빈 줄이나 주석은 건너뛰기
    if (!line || line.startsWith('//')) {
      continue
    }
    
    if (lowerLine.startsWith('delay ')) {
      const duration = line.replace(/delay /i, '').trim()
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `딜레이 ${duration}초`,
        type: 'delay',
        parameters: { duration: duration }
      })
    }
    else if (lowerLine.startsWith('jump to ')) {
      const target = line.replace(/jump to /i, '').trim()
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `${target}로 점프`,
        type: 'action_jump',
        parameters: { target: target }
      })
    }
    else if (lowerLine.startsWith('int ')) {
      // int 연산 액션 파싱
      const intMatch = line.match(/^int\s+(\w+)\s*([\+\-\*\/]?=)\s*(.+)$/)
      
      if (!intMatch) {
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `❌ 오류: ${line}`,
          type: 'script_error',
          parameters: { 
            originalLine: line,
            lineNumber: lineNumber,
            error: '잘못된 int 명령어 형식'
          }
        })
      } else {
        const varName = intMatch[1]
        const operator = intMatch[2]
        const value = intMatch[3].trim()
        
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `정수 변수: ${varName} ${operator} ${value}`,
          type: 'script',
          parameters: { script: line }
        })
      }
    }
    else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('elif ') && !lowerLine.startsWith('wait ') && !lowerLine.startsWith('int ')) {
      const [signalName, value] = line.split(' = ').map(s => s.trim())
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `${signalName} = ${value}`,
        type: 'signal_update',
        parameters: { 
          signal_name: signalName, 
          value: value.toLowerCase() === 'true'
        }
      })
    }
    else if (lowerLine.startsWith('wait ')) {
      const waitPart = line.replace(/wait /i, '').trim()
      
      // product type 조건이나 복잡한 조건은 script type으로 처리
      if (waitPart.includes('product type =') || waitPart.toLowerCase().includes(' or ') || waitPart.toLowerCase().includes(' and ')) {
        // Complex wait - treat as script
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `복합 대기 조건`,
          type: 'script',
          parameters: { 
            script: line  // Store the entire wait line as script
          }
        })
      } else if (waitPart.includes(' = ')) {
        // Simple wait condition
        const [signalName, value] = waitPart.split(' = ').map(s => s.trim())
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `${signalName} = ${value} 대기`,
          type: 'signal_wait',
          parameters: { 
            signal_name: signalName, 
            expected_value: value.toLowerCase() === 'true'
          }
        })
      }
    }
    else if (lowerLine.startsWith('go ') && !lowerLine.startsWith('go to ')) {
      // 새로운 "go 커넥터명 to 블록명.커넥터명(인덱스,딜레이)" 형식
      // 백엔드로 전체 스크립트를 전달
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `go 명령 실행`,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else if (lowerLine.startsWith('go to ')) {
      const target = line.replace(/go to /i, '').trim()
      let targetPath = target
      let delay = '0'
      
      // 딜레이 파싱 - 유효성 검사 후에만 파싱
      if (target.includes(',')) {
        const parts = target.split(',')
        targetPath = parts[0].trim()
        const delayPart = parts[1].trim()
        
        // 딜레이 형식이 올바른 경우만 적용
        if (/^(\d+(\.\d+)?|\d+-\d+)$/.test(delayPart)) {
          delay = delayPart
        } else {
          // 잘못된 딜레이 형식이면 오류 액션으로 생성
          actions.push({
            id: `script-action-${actionCounter++}`,
            name: `❌ 오류: ${line}`,
            type: 'script_error',
            parameters: { 
              originalLine: line,
              lineNumber: lineNumber,
              error: `잘못된 딜레이 형식: ${delayPart}`
            }
          })
          continue
        }
      }
      
      // self 라우팅 처리
      if (targetPath.startsWith('self.')) {
        const selfTarget = targetPath.replace('self.', '').trim()
        
        if (entityType === 'connector') {
          // 🔥 커넥터에서 블록명으로 이동하는 경우 block_entry 타입으로 생성
          const isBlockTarget = allBlocks && allBlocks.some(block => 
            block.name === selfTarget || block.id.toString() === selfTarget
          )
          
          if (isBlockTarget) {
            // 블록으로 이동하는 액션 - block_entry 타입 사용
            actions.push({
              id: `script-action-${actionCounter++}`,
              name: `${selfTarget} 블록으로 이동`,
              type: 'block_entry',
              parameters: { 
                delay: delay.toString(),
                target_block_name: selfTarget
              }
            })
          } else {
            // 기존 방식 - conditional_branch로 스크립트 실행
            actions.push({
              id: `script-action-${actionCounter++}`,
              name: `${line}`,
              type: 'conditional_branch',
              parameters: { 
                script: line
              }
            })
          }
        } else if (entityType === 'block') {
          // 블록에서는 route_to_connector 액션으로 생성
          let connectorId = null
          let validConnector = false
          
          if (currentBlock && currentBlock.connectionPoints) {
            const connector = currentBlock.connectionPoints.find(cp => 
              cp.name === selfTarget
            )
            if (connector) {
              connectorId = connector.id
              validConnector = true
            }
          }
          
          // 유효한 커넥터가 아니면 오류 액션 생성
          if (!validConnector) {
            actions.push({
              id: `script-action-${actionCounter++}`,
              name: `❌ 오류: ${line}`,
              type: 'script_error',
              parameters: { 
                originalLine: line,
                lineNumber: lineNumber,
                error: `존재하지 않는 커넥터: ${selfTarget}`
              }
            })
            continue
          }
          
          actions.push({
            id: `script-action-${actionCounter++}`,
            name: `${targetPath}로 이동`,
            type: 'route_to_connector',
            parameters: { 
              connector_id: connectorId,
              delay: delay,
              target_block_name: 'self',
              target_connector_name: selfTarget
            }
          })
        }
      }
      // 다른 블록으로 이동
      else if (targetPath.includes('.')) {
        const [blockName, connectorName] = targetPath.split('.')
        const targetBlock = allBlocks.find(b => b.name.toLowerCase() === blockName.trim().toLowerCase())
        
        if (!targetBlock) {
          // 블록을 찾을 수 없으면 오류 액션 생성
          actions.push({
            id: `script-action-${actionCounter++}`,
            name: `❌ 오류: ${line}`,
            type: 'script_error',
            parameters: { 
              originalLine: line,
              lineNumber: lineNumber,
              error: `존재하지 않는 블록: ${blockName}`
            }
          })
          continue
        }
        
        const targetConnector = targetBlock.connectionPoints?.find(cp => 
          cp.name.toLowerCase() === connectorName.trim().toLowerCase()
        )
        
        if (!targetConnector) {
          // 커넥터를 찾을 수 없으면 오류 액션 생성
          actions.push({
            id: `script-action-${actionCounter++}`,
            name: `❌ 오류: ${line}`,
            type: 'script_error',
            parameters: { 
              originalLine: line,
              lineNumber: lineNumber,
              error: `블록 "${blockName}"에 "${connectorName}" 커넥터가 없습니다`
            }
          })
          continue
        }
        
        // 유효한 블록과 커넥터가 있을 때만 액션 생성
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `${blockName}.${connectorName}로 이동`,
          type: 'route_to_connector',
          parameters: { 
            target_block_id: targetBlock.id,
            target_connector_id: targetConnector.id,
            delay: delay,
            target_block_name: blockName.trim(),
            target_connector_name: connectorName.trim()
          }
        })
      }
      // 단순 블록 이름만 있는 경우
      else {
        const targetBlock = allBlocks.find(b => b.name === targetPath.trim())
        if (!targetBlock) {
          actions.push({
            id: `script-action-${actionCounter++}`,
            name: `❌ 오류: ${line}`,
            type: 'script_error',
            parameters: { 
              originalLine: line,
              lineNumber: lineNumber,
              error: `존재하지 않는 블록: ${targetPath}`
            }
          })
          continue
        }
        
        actions.push({
          id: `script-action-${actionCounter++}`,
          name: `${targetPath}로 이동`,
          type: 'route_to_connector',
          parameters: { 
            target_block_id: targetBlock.id,
            target_connector_id: 'self',
            delay: delay,
            target_block_name: targetPath.trim(),
            target_connector_name: 'self'
          }
        })
      }
    }
    else if (lowerLine.startsWith('if ')) {
      // This should not happen anymore as we handle if statements at the beginning
      // If we reach here, it means there's a parsing error
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `조건부 실행`,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else if (lowerLine.startsWith('log ')) {
      const logMessage = line.replace(/log /i, '').trim()
      // 따옴표 제거
      const cleanMessage = logMessage.replace(/^"|"$/g, '')
      
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `로그: ${cleanMessage}`,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else if (line.includes('product type +=') || line.includes('product type -=')) {
      const isAdd = line.includes('product type +=')
      const operation = isAdd ? '추가' : '제거'
      const params = line.split(isAdd ? 'product type +=' : 'product type -=')[1].trim()
      
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `제품 타입 ${operation}: ${params}`,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else if (lowerLine === 'create product' || lowerLine === 'dispose product' || lowerLine === 'force execution') {
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: line,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else if (lowerLine.startsWith('execute ')) {
      const targetBlock = line.replace(/execute /i, '').trim()
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `블록 "${targetBlock}" 실행`,
        type: 'script',
        parameters: { 
          script: line
        }
      })
    }
    else {
      // 인식되지 않는 명령어도 오류 액션으로 생성
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: `❌ 오류: ${line}`,
        type: 'script_error',
        parameters: { 
          originalLine: line,
          lineNumber: lineNumber,
          error: `인식되지 않는 명령어`
        }
      })
    }
  }
  
  return actions
} 
// 스크립트 검증 함수
export function validateScript(script, allSignals, allBlocks, currentBlock, entityType) {
  const errors = []
  const lines = script.split('\n')
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const lineNum = i + 1
    const lowerLine = line.toLowerCase()
    
    // 빈 줄이나 주석은 건너뛰기
    if (!line || line.startsWith('//')) {
      continue
    }
    
    if (lowerLine.startsWith('delay ')) {
      const delayPart = line.replace(/delay /i, '').trim()
      // 숫자, 숫자-숫자, 또는 변수명 형태 허용
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
    else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('wait ')) {
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
      if (!waitPart.includes(' = ')) {
        errors.push(`라인 ${lineNum}: 잘못된 대기 형식 (예: wait 신호명 = true)`)
      } else {
        const parts = waitPart.split(' = ')
        if (parts.length === 2) {
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
    }
    else if (lowerLine.startsWith('go to ')) {
      const target = line.replace(/go to /i, '').trim()
      if (!target) {
        errors.push(`라인 ${lineNum}: go to 대상이 지정되지 않았습니다`)
      } else {
        let targetPath = target
        let delay = null
        
        if (target.includes(',')) {
          const parts = target.split(',')
          targetPath = parts[0].trim()
          delay = parts[1].trim()
          
          // 딜레이 형식 검사 강화
          if (delay && !/^(\d+(\.\d+)?|\d+-\d+)$/.test(delay)) {
            errors.push(`라인 ${lineNum}: 잘못된 딜레이 형식 "${delay}" (예: 3, 2-5)`)
          }
        }
        
        // 엔티티 타입에 따른 다른 검증 로직 적용
        if (targetPath.startsWith('self.')) {
          const selfTarget = targetPath.replace('self.', '').trim()
          
          if (entityType === 'connector') {
            // 커넥터에서는 self.블록명, self.커넥터명 모두 허용
            if (currentBlock) {
              // self.블록명 체크 (블록 이름만 허용, 블록 ID는 허용하지 않음)
              const isBlockTarget = (selfTarget === currentBlock.name)
              
              // self.커넥터명 체크
              const isConnectorTarget = currentBlock.connectionPoints?.some(cp => 
                cp.name === selfTarget
              )
              
              if (!isBlockTarget && !isConnectorTarget) {
                const availableTargets = [
                  currentBlock.name,
                  ...(currentBlock.connectionPoints?.map(cp => cp.name).filter(name => name) || [])
                ]
                errors.push(`라인 ${lineNum}: 현재 블록에 "${selfTarget}"로 이동할 수 없습니다 (사용 가능: ${availableTargets.join(', ')})`)
              }
              
              // 블록 ID가 사용된 경우 경고 추가
              if (selfTarget === currentBlock.id.toString()) {
                errors.push(`라인 ${lineNum}: 블록 ID "${selfTarget}" 대신 블록 이름 "${currentBlock.name}"을 사용해주세요`)
              }
            }
          } else if (entityType === 'block') {
            // 블록에서는 self.커넥터명만 허용
            if (currentBlock && currentBlock.connectionPoints) {
              const connector = currentBlock.connectionPoints.find(cp => 
                cp.name === selfTarget
              )
              if (!connector) {
                const availableConnectors = currentBlock.connectionPoints.map(cp => cp.name).filter(name => name).join(', ')
                errors.push(`라인 ${lineNum}: 현재 블록에 "${selfTarget}" 커넥터가 없습니다 (사용 가능: ${availableConnectors || '없음'})`)
              }
            }
          }
        }
        // 다른 블록으로 이동
        else if (targetPath.includes('.')) {
          const [blockName, connectorName] = targetPath.split('.')
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
        }
      }
    }
    else if (lowerLine.startsWith('if ')) {
      // 조건부 실행의 신호 이름도 검사
      const condition = line.replace(/if /i, '').trim()
      if (condition.includes(' = ')) {
        const parts = condition.split(' = ')
        if (parts.length === 2) {
          const signalName = parts[0].trim()
          if (allSignals && allSignals.length > 0 && !allSignals.includes(signalName)) {
            errors.push(`라인 ${lineNum}: 존재하지 않는 신호 "${signalName}"`)
          }
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
    else if (line.includes(' = ') && !lowerLine.startsWith('if ') && !lowerLine.startsWith('wait ')) {
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
      if (waitPart.includes(' = ')) {
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
      // 조건부 실행은 복잡하므로 일단 스크립트 그대로 저장
      actions.push({
        id: `script-action-${actionCounter++}`,
        name: '조건부 실행',
        type: 'conditional_branch',
        parameters: { 
          script: script  // 전체 스크립트를 저장
        }
      })
      break  // 조건부 실행이 있으면 나머지는 그 안에 포함된 것으로 간주
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
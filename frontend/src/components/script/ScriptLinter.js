/**
 * 실시간 스크립트 문법 검사기
 * CodeMirror 6용 linter
 */

import { linter } from '@codemirror/lint'
import { validateScript } from '../../utils/ScriptUtils.js'

/**
 * 디바운싱 함수
 */
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

/**
 * 스크립트 검증 결과를 CodeMirror Diagnostic으로 변환
 * 정확한 위치에 간단한 빨간 밑줄 표시
 */
function convertValidationToDiagnostics(validationResult, doc) {
  const diagnostics = []
  
  if (!validationResult.valid && validationResult.errors) {
    for (const error of validationResult.errors) {
      // 라인 번호 추출 (예: "라인 3: 오류 메시지")
      const lineMatch = error.match(/라인 (\d+):(.*)/)
      if (lineMatch) {
        const lineNum = parseInt(lineMatch[1]) - 1 // 0-based
        const message = lineMatch[2].trim()
        
        // 정확한 오류 위치 찾기
        const position = findErrorPosition(doc, lineNum, message)
        
        // 심각도 결정
        let severity = 'error'
        if (message.includes('권장') || message.includes('제안')) {
          severity = 'info'
        } else if (message.includes('경고') || message.includes('주의')) {
          severity = 'warning'
        }
        
        diagnostics.push({
          from: position.from,
          to: position.to,
          severity,
          message,
          source: 'simulation-script'
        })
      } else {
        // 라인 번호가 없는 일반 오류 - 첫 단어만
        const firstLine = doc.line(1)
        const lineText = doc.sliceString(firstLine.from, firstLine.to)
        const firstWord = lineText.trim().split(/\s+/)[0]
        const wordLength = firstWord ? firstWord.length : 1
        
        diagnostics.push({
          from: 0,
          to: wordLength,
          severity: 'error',
          message: error,
          source: 'simulation-script'
        })
      }
    }
  }
  
  return diagnostics
}

/**
 * 라인과 컬럼 위치에서 문서 위치 계산
 */
function getPositionFromLineCol(doc, line, col = 0) {
  try {
    const docLine = doc.line(line + 1) // 1-based line
    return Math.min(docLine.from + col, docLine.to)
  } catch {
    return 0
  }
}

/**
 * 더 정확한 오류 위치 찾기 - 특정 단어/구문만 하이라이트
 */
function findErrorPosition(doc, lineNum, errorMessage) {
  try {
    const line = doc.line(lineNum + 1)
    let lineText = doc.sliceString(line.from, line.to)
    
    // 따옴표가 양쪽에 있으면 제거 (디버깅에서 확인된 문제)
    if (lineText.startsWith('"') && lineText.endsWith('"')) {
      lineText = lineText.slice(1, -1)
    }
    
    // 주석을 제거한 부분만 검증 대상으로 사용
    const commentIndex = lineText.indexOf('//')
    const cleanLineText = commentIndex !== -1 ? lineText.substring(0, commentIndex).trim() : lineText
    
    
    // 따옴표 제거에 따른 오프셋 계산
    const originalLineText = doc.sliceString(line.from, line.to)
    const quoteOffset = originalLineText.startsWith('"') ? 1 : 0
    
    // 1. 존재하지 않는 신호명 오류
    if (errorMessage.includes('존재하지 않는 신호')) {
      const signalMatch = errorMessage.match(/"([^"]+)"/)
      if (signalMatch) {
        const signalName = signalMatch[1]
        const index = cleanLineText.indexOf(signalName)
        if (index !== -1) {
          return {
            from: line.from + index + quoteOffset,
            to: line.from + index + signalName.length + quoteOffset
          }
        }
      }
    }
    
    // 2. 존재하지 않는 블록명 오류
    if (errorMessage.includes('존재하지 않는 블록')) {
      // 다양한 형태의 블록 오류 메시지 처리
      let blockName = null
      
      // "존재하지 않는 블록: 블록1" 형태
      const colonMatch = errorMessage.match(/존재하지 않는 블록:?\s*(.+)/)
      if (colonMatch) {
        blockName = colonMatch[1].trim()
      }
      
      // "블록명" 형태
      if (!blockName) {
        const quotedMatch = errorMessage.match(/"([^"]+)"/)
        if (quotedMatch) {
          blockName = quotedMatch[1]
        }
      }
      
      if (blockName) {
        const index = cleanLineText.indexOf(blockName)
        if (index !== -1) {
          return {
            from: line.from + index + quoteOffset,
            to: line.from + index + blockName.length + quoteOffset
          }
        }
      }
    }
    
    // 3. 잘못된 딜레이 형식 오류
    if (errorMessage.includes('잘못된 딜레이 형식')) {
      const delayMatch = errorMessage.match(/"([^"]+)"/)
      if (delayMatch) {
        const delayValue = delayMatch[1]
        // 주석이 제거된 부분에서 delay 뒤의 값만 찾기
        const delayIndex = cleanLineText.toLowerCase().indexOf('delay ')
        if (delayIndex !== -1) {
          const afterDelay = cleanLineText.substring(delayIndex + 6).trim()
          const delayValueIndex = cleanLineText.indexOf(afterDelay, delayIndex)
          return {
            from: line.from + delayValueIndex + quoteOffset,
            to: line.from + delayValueIndex + afterDelay.length + quoteOffset
          }
        }
      }
    }
    
    // 4. 잘못된 대기 조건 형식 오류
    if (errorMessage.includes('잘못된 대기 조건 형식')) {
      const conditionMatch = errorMessage.match(/"([^"]+)"/)
      if (conditionMatch) {
        const condition = conditionMatch[1]
        const index = lineText.indexOf(condition)
        if (index !== -1) {
          return {
            from: line.from + index + quoteOffset,
            to: line.from + index + condition.length + quoteOffset
          }
        }
      }
    }
    
    // 5. 신호 값은 true 또는 false여야 합니다
    if (errorMessage.includes('신호 값은 true 또는 false여야 합니다')) {
      // = 기호 뒤의 값을 찾기 (주석 제거된 부분에서)
      const equalIndex = cleanLineText.indexOf('=')
      if (equalIndex !== -1) {
        const afterEqual = cleanLineText.substring(equalIndex + 1).trim()
        const valueMatch = afterEqual.match(/^\S+/)
        if (valueMatch) {
          const value = valueMatch[0]
          const valueIndex = cleanLineText.indexOf(value, equalIndex)
          return {
            from: line.from + valueIndex + quoteOffset,
            to: line.from + valueIndex + value.length + quoteOffset
          }
        }
      }
    }
    
    // 6. 잘못된 신호 설정 형식
    if (errorMessage.includes('잘못된 신호 설정 형식')) {
      // = 기호가 없거나 잘못된 경우
      const firstWord = lineText.trim().split(/\s+/)[0]
      if (firstWord) {
        const index = lineText.indexOf(firstWord)
        return {
          from: line.from + index + quoteOffset,
          to: line.from + index + firstWord.length + quoteOffset
        }
      }
    }
    
    // 7. 커넥터 오류
    if (errorMessage.includes('커넥터가 없습니다')) {
      // "현재 블록에 "L" 커넥터가 없습니다" 형태
      const connectorMatch = errorMessage.match(/"([^"]+)"\s*커넥터가 없습니다/)
      if (connectorMatch) {
        const connectorName = connectorMatch[1]
        const index = cleanLineText.indexOf(connectorName)
        if (index !== -1) {
          return {
            from: line.from + index + quoteOffset,
            to: line.from + index + connectorName.length + quoteOffset
          }
        }
      }
    }
    
    // 8. 알 수 없는 명령어
    if (errorMessage.includes('알 수 없는 명령어') || errorMessage.includes('지원되지 않는 명령어') || errorMessage.includes('인식되지 않는 명령어')) {
      // 불완전한 명령어 (wait, if만 있는 경우) 특별 처리
      if (cleanLineText.trim() === 'wait' || cleanLineText.trim() === 'if') {
        const index = lineText.indexOf(cleanLineText.trim())
        return {
          from: line.from + index + quoteOffset,
          to: line.from + index + cleanLineText.trim().length + quoteOffset
        }
      }
      
      const firstWord = cleanLineText.trim().split(/\s+/)[0]
      if (firstWord) {
        const index = lineText.indexOf(firstWord)
        return {
          from: line.from + index + quoteOffset,
          to: line.from + index + firstWord.length + quoteOffset
        }
      }
    }
    
    // 9. 기본값: 첫 번째 단어만 하이라이트
    const trimmedText = cleanLineText.trim()
    if (trimmedText) {
      const firstWordMatch = trimmedText.match(/^\S+/)
      if (firstWordMatch) {
        const firstWord = firstWordMatch[0]
        const index = lineText.indexOf(firstWord)
        return {
          from: line.from + index + quoteOffset,
          to: line.from + index + firstWord.length + quoteOffset
        }
      }
    }
    
    // 최후의 수단: 첫 문자 1개
    return {
      from: line.from + quoteOffset,
      to: line.from + 1 + quoteOffset
    }
  } catch (error) {
    return {
      from: 0,
      to: 1
    }
  }
}

/**
 * 실시간 스크립트 linter 생성
 */
export function createScriptLinter(allSignals = [], allBlocks = [], currentBlock = null, entityType = 'block') {
  // 디바운싱된 검증 함수
  const debouncedValidate = debounce((view, callback) => {
    const text = view.state.doc.toString()
    
    try {
      
      const validationResult = validateScript(
        text,
        allSignals,
        allBlocks,
        currentBlock,
        entityType
      )
      
      
      const diagnostics = convertValidationToDiagnostics(validationResult, view.state.doc)
      callback(diagnostics)
    } catch (error) {
      callback([{
        from: 0,
        to: 50,
        severity: 'error',
        message: `검증 오류: ${error.message}`,
        source: 'simulation-script'
      }])
    }
  }, 300) // 300ms 디바운싱
  
  return linter((view) => {
    return new Promise((resolve) => {
      debouncedValidate(view, resolve)
    })
  })
}

/**
 * 간단한 동기 linter (디바운싱 없음)
 */
export function createSimpleLinter(allSignals = [], allBlocks = [], currentBlock = null, entityType = 'block') {
  return linter((view) => {
    const text = view.state.doc.toString()
    
    // 빈 텍스트는 검증하지 않음
    if (!text.trim()) {
      return []
    }
    
    try {
      const validationResult = validateScript(
        text,
        allSignals,
        allBlocks,
        currentBlock,
        entityType
      )
      
      return convertValidationToDiagnostics(validationResult, view.state.doc)
    } catch (error) {
      return [{
        from: 0,
        to: Math.min(text.length, 100),
        severity: 'error',
        message: `검증 오류: ${error.message}`,
        source: 'simulation-script'
      }]
    }
  })
}

export default createScriptLinter
/**
 * 시뮬레이션 스크립트 전용 언어 정의
 * CodeMirror 6용 간단한 구문 하이라이팅
 */

import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags as t } from '@lezer/highlight'

// 시뮬레이션 스크립트 키워드 정의
const simulationKeywords = [
  'delay', 'wait', 'if', 'go', 'to', 'from', 'jump', 'log', 'product', 'type',
  'and', 'or', 'true', 'false'
]

// 연산자 정의
const simulationOperators = ['=', '+=', '-=', ',']

/**
 * 시뮬레이션 스크립트 언어 파서 정의
 * 간단한 토큰 기반 파싱을 사용
 */
const simulationScriptParser = {
  // 토큰 매칭 함수
  token(stream, state) {
    // 공백 건너뛰기
    if (stream.eatSpace()) return null
    
    // 주석 처리
    if (stream.match('//')) {
      stream.skipToEnd()
      return 'comment'
    }
    
    // 문자열 처리 (따옴표)
    if (stream.match(/^"([^"\\\\]|\\\\.)*"/)) {
      return 'string'
    }
    
    // 숫자 처리
    if (stream.match(/^[0-9]+(\.[0-9]+)?/)) {
      return 'number'
    }
    
    // 연산자 처리
    for (const op of simulationOperators) {
      if (stream.match(op)) {
        return 'operator'
      }
    }
    
    // 키워드와 식별자 처리
    const word = stream.match(/^[a-zA-Z가-힣_][a-zA-Z가-힣0-9_]*/)
    if (word) {
      const wordStr = word[0]
      
      // 키워드 확인
      if (simulationKeywords.includes(wordStr)) {
        // 특별한 키워드들에 대한 추가 분류
        if (['delay', 'wait', 'if', 'go', 'jump', 'log'].includes(wordStr)) {
          return 'keyword'
        }
        if (['and', 'or'].includes(wordStr)) {
          return 'operator'
        }
        if (['true', 'false'].includes(wordStr)) {
          return 'atom'
        }
        if (['product', 'type'].includes(wordStr)) {
          return 'property'
        }
        return 'keyword'
      }
      
      // 신호명인지 확인 (동적으로 주입될 예정)
      if (state.signals && state.signals.includes(wordStr)) {
        return 'variable-2'
      }
      
      // 블록명인지 확인 (동적으로 주입될 예정)
      if (state.blocks && state.blocks.includes(wordStr)) {
        return 'variable-3'
      }
      
      return 'variable'
    }
    
    // 기타 문자
    stream.next()
    return null
  },
  
  startState() {
    return {
      signals: [], // 동적으로 설정될 신호 목록
      blocks: []   // 동적으로 설정될 블록 목록
    }
  }
}

/**
 * CodeMirror 6용 언어 정의
 */
const simulationScriptLanguage = LRLanguage.define({
  name: 'simulation-script',
  parser: simulationScriptParser,
  languageData: {
    commentTokens: { line: '//' },
    closeBrackets: { brackets: ['(', '[', '{', '"'] }
  }
})

/**
 * 구문 하이라이팅 스타일 정의
 */
const simulationScriptHighlighting = styleTags({
  'keyword': t.keyword,
  'operator': t.operator,
  'string': t.string,
  'number': t.number,
  'comment': t.comment,
  'atom': t.atom,
  'property': t.propertyName,
  'variable': t.variableName,
  'variable-2': t.special(t.variableName), // 신호명
  'variable-3': t.definition(t.variableName) // 블록명
})

/**
 * 간단한 토큰 기반 하이라이팅 (fallback)
 */
function createSimpleHighlighter() {
  return {
    token(stream, state) {
      return simulationScriptParser.token(stream, state)
    },
    startState() {
      return simulationScriptParser.startState()
    }
  }
}

/**
 * 시뮬레이션 스크립트 언어 지원 객체 생성
 */
export function simulationScript(options = {}) {
  const { signals = [], blocks = [] } = options
  
  // 간단한 모드 정의 (CodeMirror 5 스타일)
  const simpleMode = {
    name: 'simulation-script',
    
    token(stream, state) {
      // 상태에 동적 데이터 설정
      state.signals = signals
      state.blocks = blocks
      
      return simulationScriptParser.token(stream, state)
    },
    
    startState() {
      return {
        signals: signals,
        blocks: blocks
      }
    }
  }
  
  return simpleMode
}

/**
 * 스타일 맵핑 (CSS 클래스)
 */
export const simulationScriptStyles = {
  'keyword': 'cm-keyword',      // 파란색 - delay, wait, if, go 등
  'operator': 'cm-operator',    // 빨간색 - =, and, or 등
  'string': 'cm-string',        // 갈색 - "텍스트"
  'number': 'cm-number',        // 보라색 - 숫자
  'comment': 'cm-comment',      // 회색 - // 주석
  'atom': 'cm-atom',           // 초록색 - true, false
  'property': 'cm-property',    // 주황색 - product, type
  'variable': 'cm-variable',    // 기본색 - 일반 변수
  'variable-2': 'cm-variable-2', // 초록색 - 신호명
  'variable-3': 'cm-variable-3'  // 주황색 - 블록명
}

/**
 * 기본 CSS 스타일 정의
 */
export const simulationScriptCSS = `
.cm-keyword { color: #0000ff; font-weight: bold; }
.cm-operator { color: #ff0000; }
.cm-string { color: #8b4513; }
.cm-number { color: #800080; }
.cm-comment { color: #999999; font-style: italic; }
.cm-atom { color: #008000; }
.cm-property { color: #ff8c00; }
.cm-variable { color: #333333; }
.cm-variable-2 { color: #008000; font-weight: bold; } /* 신호명 */
.cm-variable-3 { color: #ff8c00; font-weight: bold; } /* 블록명 */
`

export default simulationScript
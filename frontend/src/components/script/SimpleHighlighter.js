/**
 * 간단한 정규표현식 기반 구문 하이라이팅
 * CodeMirror 6용 시뮬레이션 스크립트 하이라이팅
 */

import { EditorView, Decoration, ViewPlugin } from '@codemirror/view'
import { RangeSetBuilder } from '@codemirror/state'

// 시뮬레이션 스크립트 토큰 정의
const tokenPatterns = [
  // 주석
  { regex: /\/\/.*$/gm, class: 'cm-comment' },
  
  // 문자열 (따옴표)
  { regex: /"([^"\\]|\\.)*"/g, class: 'cm-string' },
  
  // 숫자
  { regex: /\b\d+(\.\d+)?\b/g, class: 'cm-number' },
  
  // 키워드 (명령어)
  { regex: /\b(delay|wait|if|go|jump|log|create|dispose|force|execution|entity|product|type)\b/g, class: 'cm-keyword' },
  
  // 연산자와 논리 연산자
  { regex: /\b(and|or)\b/g, class: 'cm-operator' },
  { regex: /[=+\-,]/g, class: 'cm-operator' },
  
  // Boolean 값
  { regex: /\b(true|false)\b/g, class: 'cm-atom' },
  
  // 방향 키워드
  { regex: /\b(to|from)\b/g, class: 'cm-property' }
]

/**
 * 동적 토큰 패턴 생성 (신호명, 블록명)
 */
function createDynamicPatterns(signals = [], blocks = []) {
  const patterns = [...tokenPatterns]
  
  // 신호명 패턴 추가
  if (signals.length > 0) {
    const signalRegex = new RegExp(`\\b(${signals.map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'g')
    patterns.push({ regex: signalRegex, class: 'cm-signal' })
  }
  
  // 블록명 패턴 추가  
  if (blocks.length > 0) {
    const blockRegex = new RegExp(`\\b(${blocks.map(b => b.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'g')
    patterns.push({ regex: blockRegex, class: 'cm-block' })
  }
  
  return patterns
}

/**
 * 텍스트에서 토큰 찾기
 */
function findTokens(text, patterns) {
  const tokens = []
  
  for (const pattern of patterns) {
    pattern.regex.lastIndex = 0 // 정규식 초기화
    let match
    
    while ((match = pattern.regex.exec(text)) !== null) {
      tokens.push({
        from: match.index,
        to: match.index + match[0].length,
        class: pattern.class
      })
    }
  }
  
  // 위치순으로 정렬
  tokens.sort((a, b) => a.from - b.from)
  
  // 겹치는 토큰 제거 (첫 번째 매치 우선)
  const filteredTokens = []
  let lastEnd = 0
  
  for (const token of tokens) {
    if (token.from >= lastEnd) {
      filteredTokens.push(token)
      lastEnd = token.to
    }
  }
  
  return filteredTokens
}

/**
 * 하이라이팅 데코레이션 생성
 */
function createDecorations(view, signals = [], blocks = []) {
  const builder = new RangeSetBuilder()
  const text = view.state.doc.toString()
  const patterns = createDynamicPatterns(signals, blocks)
  const tokens = findTokens(text, patterns)
  
  for (const token of tokens) {
    builder.add(
      token.from,
      token.to,
      Decoration.mark({ class: token.class })
    )
  }
  
  return builder.finish()
}

/**
 * 하이라이팅 플러그인 생성
 */
export function createHighlightPlugin(signals = [], blocks = []) {
  return ViewPlugin.fromClass(
    class {
      constructor(view) {
        this.decorations = createDecorations(view, signals, blocks)
      }
      
      update(update) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = createDecorations(update.view, signals, blocks)
        }
      }
    },
    {
      decorations: v => v.decorations
    }
  )
}

/**
 * CSS 스타일 정의
 */
export const highlightTheme = EditorView.theme({
  '.cm-keyword': {
    color: '#0066cc',
    fontWeight: 'bold'
  },
  '.cm-operator': {
    color: '#d73a49',
    fontWeight: 'bold'
  },
  '.cm-string': {
    color: '#032f62'
  },
  '.cm-number': {
    color: '#005cc5'
  },
  '.cm-comment': {
    color: '#6a737d',
    fontStyle: 'italic',
    backgroundColor: 'rgba(106, 115, 125, 0.1)'
  },
  '.cm-atom': {
    color: '#005cc5',
    fontWeight: 'bold'
  },
  '.cm-property': {
    color: '#e36209'
  },
  '.cm-signal': {
    color: '#22863a',
    fontWeight: 'bold',
    backgroundColor: 'rgba(34, 134, 58, 0.1)'
  },
  '.cm-block': {
    color: '#e36209',
    fontWeight: 'bold',
    backgroundColor: 'rgba(227, 98, 9, 0.1)'
  }
})

export default createHighlightPlugin
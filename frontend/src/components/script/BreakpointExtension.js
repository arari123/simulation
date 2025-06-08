/**
 * 브레이크포인트 기능을 위한 CodeMirror 확장
 * 라인 번호 옆에 브레이크포인트 버튼을 추가하고 상태를 관리합니다.
 */

import { EditorView, gutter, GutterMarker, Decoration } from '@codemirror/view';
import { StateField, StateEffect, Facet } from '@codemirror/state';

// 브레이크포인트 토글 효과
export const toggleBreakpoint = StateEffect.define({
  map: (val, mapping) => ({ line: mapping.mapPos(val.line), on: val.on })
});

// 브레이크포인트 상태 필드
export const breakpointState = StateField.define({
  create() {
    return new Set();
  },
  update(breakpoints, tr) {
    let updated = false;
    let newBreakpoints = breakpoints;
    
    for (let effect of tr.effects) {
      if (effect.is(toggleBreakpoint)) {
        if (!updated) {
          // 첫 번째 변경이 발생할 때만 새로운 Set 생성
          newBreakpoints = new Set(breakpoints);
          updated = true;
        }
        const lineNum = tr.state.doc.lineAt(effect.value.line).number;
        if (effect.value.on) {
          newBreakpoints.add(lineNum);
        } else {
          newBreakpoints.delete(lineNum);
        }
      }
    }
    
    // 문서 변경 시 라인 번호 업데이트
    if (tr.docChanged) {
      const updatedBreakpoints = new Set();
      const mapping = tr.changes;
      for (let line of newBreakpoints) {
        const pos = tr.startState.doc.line(line).from;
        const newPos = mapping.mapPos(pos, 1);
        if (newPos < tr.newDoc.length) {
          const newLine = tr.newDoc.lineAt(newPos).number;
          updatedBreakpoints.add(newLine);
        }
      }
      return updatedBreakpoints;
    }
    
    return newBreakpoints;
  }
});

// 브레이크포인트 마커 클래스
class BreakpointMarker extends GutterMarker {
  constructor(on) {
    super();
    this.on = on;
  }

  toDOM() {
    const marker = document.createElement('div');
    marker.className = 'cm-breakpoint';
    marker.textContent = '●';
    marker.style.width = '20px';
    marker.style.height = '20px';
    marker.style.cursor = 'pointer';
    marker.style.display = 'flex';
    marker.style.alignItems = 'center';
    marker.style.justifyContent = 'center';
    if (this.on) {
      marker.classList.add('cm-breakpoint-on');
      marker.style.color = '#f44336';
    } else {
      marker.style.color = '#999';
    }
    return marker;
  }
  
  eq(other) {
    return other instanceof BreakpointMarker && other.on === this.on;
  }
}

// 브레이크포인트 거터 생성
export const breakpointGutter = gutter({
  class: 'cm-breakpoint-gutter',
  lineMarker(view, line, others) {
    // 현재 뷰의 브레이크포인트 상태를 확인
    const breakpoints = view.state.field(breakpointState);
    const isOn = breakpoints.has(line.number);
    
    // 마커 생성 및 반환
    return new BreakpointMarker(isOn);
  },
  lineMarkerChange: (update) => {
    // 브레이크포인트 상태가 변경될 때마다 거터 업데이트
    return update.state.field(breakpointState) !== update.startState.field(breakpointState);
  },
  initialSpacer: () => {
    const marker = new BreakpointMarker(false);
    return marker;
  },
  domEventHandlers: {
    mousedown(view, line, event) {
      // 이벤트 전파 완전 차단
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      
      // line 매개변수가 실제로는 BlockInfo 객체입니다
      const lineInfo = line;
      const doc = view.state.doc;
      const lineNumber = doc.lineAt(lineInfo.from).number;
      
      const breakpoints = view.state.field(breakpointState);
      const isOn = breakpoints.has(lineNumber);
      
      // 상태 업데이트
      view.dispatch({
        effects: toggleBreakpoint.of({ line: lineInfo.from, on: !isOn })
      });
      
      // 외부로 브레이크포인트 변경 이벤트 전달
      const callbacks = view.state.facet(breakpointCallbackFacet);
      if (callbacks.length > 0) {
        const handler = callbacks[0];
        if (handler) {
          handler(lineNumber, !isOn);
        }
      }
      
      return true;
    },
    click(view, line, event) {
      // click 이벤트도 차단
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return true;
    }
  }
});

// 브레이크포인트 변경 콜백을 저장하는 Facet
const breakpointCallbackFacet = Facet.define();

// 브레이크포인트 테마
export const breakpointTheme = EditorView.theme({
  '.cm-breakpoint-gutter': {
    width: '20px !important',
    cursor: 'pointer',
    backgroundColor: '#f5f5f5',
    position: 'relative',
    zIndex: '10'
  },
  '.cm-gutter': {
    minWidth: '20px !important',
    position: 'relative',
    zIndex: '10'
  },
  '.cm-breakpoint': {
    color: '#999',
    fontSize: '16px',
    textAlign: 'center',
    lineHeight: '20px',
    transition: 'color 0.2s',
    width: '20px',
    height: '20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  '.cm-breakpoint:hover': {
    color: '#f44336'
  },
  '.cm-breakpoint.cm-breakpoint-on': {
    color: '#f44336 !important',
    fontWeight: 'bold'
  },
  // 브레이크포인트가 있는 라인 하이라이트
  '.cm-line-breakpoint': {
    backgroundColor: 'rgba(244, 67, 54, 0.1)',
    borderLeft: '3px solid #f44336',
    paddingLeft: '2px'
  },
  // 현재 브레이크된 라인 하이라이트
  '.cm-line-breakpoint-hit': {
    backgroundColor: 'rgba(255, 193, 7, 0.3)',
    borderLeft: '3px solid #ffc107',
    paddingLeft: '2px'
  }
});

// 브레이크포인트 라인 데코레이션
export const breakpointLineDecoration = EditorView.decorations.compute(
  [breakpointState],
  (state) => {
    const breakpoints = state.field(breakpointState);
    const decorations = [];
    
    for (const lineNum of breakpoints) {
      try {
        const line = state.doc.line(lineNum);
        decorations.push(Decoration.line({
          class: 'cm-line-breakpoint'
        }).range(line.from));
      } catch (e) {
        // 라인이 범위를 벗어난 경우 무시
      }
    }
    
    return Decoration.set(decorations);
  }
);

// 브레이크포인트 설정/해제 헬퍼 함수
export function setBreakpoint(view, lineNumber, on) {
  const line = view.state.doc.line(lineNumber);
  view.dispatch({
    effects: toggleBreakpoint.of({ line: line.from, on })
  });
}

// 모든 브레이크포인트 가져오기
export function getBreakpoints(view) {
  return Array.from(view.state.field(breakpointState));
}

// 모든 브레이크포인트 클리어
export function clearAllBreakpoints(view) {
  const breakpoints = view.state.field(breakpointState);
  const effects = [];
  
  for (const lineNum of breakpoints) {
    const line = view.state.doc.line(lineNum);
    effects.push(toggleBreakpoint.of({ line: line.from, on: false }));
  }
  
  if (effects.length > 0) {
    view.dispatch({ effects });
  }
}

// 브레이크포인트 초기화 헬퍼 함수
export function initializeBreakpoints(view, breakpoints) {
  if (!breakpoints || breakpoints.length === 0) return;
  
  const effects = [];
  for (const lineNum of breakpoints) {
    try {
      const line = view.state.doc.line(lineNum);
      effects.push(toggleBreakpoint.of({ line: line.from, on: true }));
    } catch (e) {
      // 라인이 범위를 벗어난 경우 무시
    }
  }
  
  if (effects.length > 0) {
    view.dispatch({ effects });
  }
}

// 브레이크포인트 확장 번들
export function createBreakpointExtension(onBreakpointChange) {
  const extensions = [
    breakpointState,
    breakpointGutter,
    breakpointTheme,
    breakpointLineDecoration
  ];
  
  if (onBreakpointChange) {
    extensions.push(breakpointCallbackFacet.of(onBreakpointChange));
  }
  
  return extensions;
}
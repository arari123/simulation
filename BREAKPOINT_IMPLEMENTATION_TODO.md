# 브레이크포인트 기능 구현 TODO

## 개요
스크립트 디버깅을 위한 브레이크포인트 기능을 구현합니다. 이 기능은 스크립트 실행을 특정 라인에서 중단하고, 상태를 확인한 후 계속 진행할 수 있게 합니다.

## 핵심 요구사항
1. 스크립트 편집기에서 라인별 브레이크포인트 설정/해제
2. 브레이크포인트에서 실행 중단
3. 디버그 상태 표시 (UI에서 확인)
4. 스텝 실행/계속 실행 제어
5. 조건부 실행 내 브레이크포인트 처리

## 구현 전략 (모듈화 접근)
기존 엔진 코드를 최소한으로 수정하기 위해 디버그 매니저를 별도 모듈로 구현

## Phase 1: 프론트엔드 UI 구현

### 1.1 ScriptEditorV2 브레이크포인트 UI 추가
- [ ] 라인 번호 영역에 브레이크포인트 버튼 추가
- [ ] 클릭 시 빨간 점으로 브레이크포인트 표시
- [ ] 브레이크포인트 상태 관리 (Set으로 라인 번호 저장)
- [ ] CodeMirror extension으로 구현
  ```javascript
  // 새 파일: frontend/src/components/script/BreakpointExtension.js
  - createBreakpointGutter() 함수
  - breakpointTheme 정의
  - breakpoint marker widget
  ```

### 1.2 브레이크포인트 데이터 관리
- [ ] useBlocks.js에 브레이크포인트 상태 추가
  ```javascript
  const blockBreakpoints = ref(new Map()) // blockId -> Set<lineNumber>
  ```
- [ ] 브레이크포인트 저장/로드 (JSON에 포함)
- [ ] 블록별 브레이크포인트 독립 관리

### 1.3 디버그 상태 표시 UI
- [ ] ControlPanel.vue에 디버그 상태 섹션 추가
  - 현재 브레이크된 블록/라인 표시
  - "계속", "스텝 실행" 버튼
  - 디버그 모드 ON/OFF 토글
- [ ] 브레이크포인트 hit 시 하이라이트 효과

## Phase 2: 백엔드 디버그 매니저 구현

### 2.1 DebugManager 클래스 생성
- [ ] 새 파일: backend/app/core/debug_manager.py
  ```python
  class DebugManager:
      def __init__(self):
          self.breakpoints = {}  # {block_id: set(line_numbers)}
          self.is_debugging = False
          self.current_break = None  # (block_id, line_number)
          self.step_mode = False
          self.continue_event = None  # simpy event
  ```

### 2.2 스크립트 실행기 통합
- [ ] SimpleScriptExecutor 수정 (최소한의 변경)
  ```python
  def execute_script(self, script, entity, env, block):
      # 기존 코드 유지
      for line_number, command in enumerate(lines, 1):
          # 디버그 매니저 체크 추가
          if self.debug_manager:
              yield from self.debug_manager.check_breakpoint(
                  block.id, line_number, env
              )
          # 기존 명령 실행 코드
  ```

### 2.3 브레이크포인트 체크 로직
- [ ] check_breakpoint 메서드 구현
  - 브레이크포인트 존재 확인
  - 조건부 실행 context 체크
  - simpy event wait으로 중단
- [ ] resume/step 메서드 구현

## Phase 3: API 엔드포인트 추가

### 3.1 디버그 제어 API
- [ ] /simulation/debug/breakpoints - 브레이크포인트 설정/해제
  ```python
  {
      "action": "set|clear|clear_all",
      "block_id": "1",
      "line_number": 5
  }
  ```
- [ ] /simulation/debug/control - 디버그 제어
  ```python
  {
      "action": "continue|step|stop_debug"
  }
  ```
- [ ] /simulation/debug/status - 현재 디버그 상태 조회

### 3.2 시뮬레이션 상태에 디버그 정보 추가
- [ ] SimulationStepResult에 debug_info 필드 추가
  ```python
  debug_info: Optional[Dict] = {
      "is_debugging": bool,
      "is_paused": bool,
      "current_break": {"block_id": str, "line": int},
      "breakpoints": {block_id: [lines]}
  }
  ```

## Phase 4: 상태 동기화 및 통합

### 4.1 프론트엔드-백엔드 통신
- [ ] useSimulation.js에 디버그 API 호출 추가
- [ ] WebSocket 또는 polling으로 디버그 상태 실시간 업데이트
- [ ] 브레이크포인트 hit 시 자동으로 시뮬레이션 일시정지

### 4.2 조건부 실행 context 추적
- [ ] SimpleScriptExecutor에 실행 context 스택 추가
  ```python
  self.execution_context = []  # [(type, condition_met)]
  ```
- [ ] if 블록 진입/탈출 시 context 업데이트
- [ ] 조건 불만족 시 브레이크포인트 무시

## Phase 5: 테스트 및 최적화

### 5.1 테스트 케이스 작성
- [ ] 단순 브레이크포인트 테스트
- [ ] 조건부 실행 내 브레이크포인트
- [ ] 다중 블록 브레이크포인트
- [ ] 스텝 실행 테스트

### 5.2 성능 최적화
- [ ] 브레이크포인트 체크 오버헤드 최소화
- [ ] 디버그 모드 OFF 시 체크 skip
- [ ] 브레이크포인트 lookup 최적화 (Set 사용)

## Phase 6: 사용자 경험 개선

### 6.1 시각적 피드백
- [ ] 현재 실행 라인 하이라이트
- [ ] 브레이크포인트 hit 애니메이션
- [ ] 디버그 모드 시 UI 색상 변경

### 6.2 디버그 정보 패널
- [ ] 현재 변수 값 표시
- [ ] 실행 스택 표시
- [ ] 브레이크포인트 목록 관리

## 예상 구현 일정
- Phase 1-2: 3-4일 (핵심 기능)
- Phase 3-4: 2-3일 (통합)
- Phase 5-6: 2-3일 (테스트 및 개선)
- 총 예상: 7-10일

## 위험 요소 및 대응 방안

### 위험 1: 엔진 실행 흐름 중단
- **위험**: simpy 프로세스 중단 시 데드락 가능
- **대응**: Event 기반 일시정지로 안전하게 구현

### 위험 2: 성능 저하
- **위험**: 매 라인마다 브레이크포인트 체크
- **대응**: 디버그 모드 OFF 시 체크 완전 skip

### 위험 3: 상태 동기화 문제
- **위험**: 프론트엔드-백엔드 상태 불일치
- **대응**: 단방향 데이터 흐름 유지

## 구현 우선순위
1. **필수**: 기본 브레이크포인트 설정/해제 및 중단
2. **중요**: 스텝/계속 실행 제어
3. **선택**: 변수 값 표시, 실행 스택 표시

## 참고사항
- 기존 엔진 코드 최소 수정 원칙 준수
- 모든 디버그 기능은 선택적 (디버그 매니저 없이도 동작)
- 프로덕션 환경에서는 디버그 기능 비활성화 가능
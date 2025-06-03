================================================================================================
                           공정 시뮬레이션 웹 애플리케이션 프로젝트
================================================================================================

■ 실행 방법
  [frontend 서버 구동]
  - frontend 폴더에서 다음 프롬프트 명령어 입력
  - npm run dev
  [backend 서버 구동]
  - backend 폴더에서 다음 프롬프트 명령어 입력    
   # 가상환경 생성 및 활성화 (첫 실행 시)
     python3 -m venv venv
     source venv/bin/activate
     python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


■ 프로젝트 개요
  - 제조 공정을 시각적으로 모델링하고 시뮬레이션할 수 있는 웹 애플리케이션
  - 블록 기반 공정 설계, 신호 시스템, 스크립트 기반 액션 정의 지원
  - 실시간 시뮬레이션 실행 및 결과 시각화 제공
  - 엔티티 기반 블록 간 이동 추적 및 스텝 실행 시뮬레이션

■ 기술 스택
  [프론트엔드]
  - Vue.js 3 (Composition API)
  - Konva.js (2D 캔버스 렌더링 및 상호작용)
  - HTML5/CSS3/JavaScript
  - Vite (빌드 도구)

  [백엔드]
  - Python FastAPI (REST API 서버)
  - SimPy (이산 사건 시뮬레이션 라이브러리)
  - uvicorn (ASGI 서버)
  - CORS 미들웨어

■ 폴더 구조
  simulation/
  ├── frontend/                    # Vue.js 프론트엔드
  │   ├── src/
  │   │   ├── components/          # Vue 컴포넌트들
  │   │   │   ├── App.vue                    # 메인 애플리케이션 컴포넌트 (1383줄)
  │   │   │   ├── CanvasArea.vue             # Konva.js 캔버스 영역 (862줄)
  │   │   │   ├── BlockSettingsPopup.vue     # 블록 설정 팝업/사이드바 (2744줄)
  │   │   │   ├── ConnectorSettingsPopup.vue # 커넥터 설정 팝업/사이드바 (1725줄)
  │   │   │   ├── ControlPanel.vue           # 시뮬레이션 제어 패널 (399줄)
  │   │   │   └── GlobalSignalPanel.vue      # 글로벌 신호 관리 패널 (331줄)
  │   │   ├── main.js              # Vue 앱 초기화
  │   │   └── assets/              # 정적 자원
  │   ├── public/
  │   │   └── index.html           # 메인 HTML 파일
  │   ├── package.json             # 프론트엔드 의존성
  │   └── vite.config.js           # Vite 빌드 설정
  ├── backend/                     # Python FastAPI 백엔드
  │   ├── app/
  │   │   ├── main.py              # FastAPI 서버 메인 파일 (1234줄)
  │   │   ├── models.py            # 데이터 모델 정의
  │   │   └── simulation.py        # 시뮬레이션 헬퍼 함수
  │   └── requirements.txt         # 백엔드 의존성
  └── simulation-config-*.json     # 시뮬레이션 설정 파일들

■ 핵심 기능 및 컴포넌트 설명

  [1] App.vue - 메인 애플리케이션 컴포넌트 (1383줄)
      - 전체 애플리케이션 상태 관리 (blocks, connections, signals 등)
      - 레이아웃 관리 (메인 캔버스 + 사이드바)
      - 블록/커넥터 클릭 이벤트 처리
      - 시뮬레이션 데이터 로드/저장 기능
      - 초기 시나리오 설정 (투입 → 공정1 → 배출)
      - 조건부 실행 스크립트 파싱 및 라우팅 연결

  [2] CanvasArea.vue - 캔버스 렌더링 및 상호작용 (862줄)
      - Konva.js를 사용한 2D 캔버스 렌더링
      - 블록, 커넥터, 연결선 시각화
      - 마우스 드래그로 블록 이동 (cancelBubble 처리)
      - 캔버스 전체 드래그 기능 (stage draggable)
      - 줌인/줌아웃 기능
      - 블록/커넥터 클릭 이벤트 emit
      - 연결선 자동 생성 (route_to_connector 액션 기반)
      - 동적 캔버스 크기 조정

  [3] BlockSettingsPopup.vue - 블록 설정 관리 (2744줄)
      - 사이드바/팝업 모드 지원 (isSidebar prop으로 전환)
      - 블록 이름, 최대 투입 수량 설정
      - 블록 액션 목록 관리 (추가/수정/삭제/순서 변경)
      - 액션 타입: delay, signal_update, signal_check, signal_wait, action_jump, route_to_connector, conditional_branch
      - 조건부 실행 GUI 편집기
      - 스크립트 편집기 (고급 사용자용, 구문 강조 지원)
      - 블록 복사/삭제 기능
      - actions-list-container 구조로 전체 높이 활용

  [4] ConnectorSettingsPopup.vue - 커넥터(연결점) 설정 관리 (1725줄)
      - BlockSettingsPopup과 동일한 구조 및 기능
      - 커넥터별 액션 정의
      - 다음 공정 진행 설정 (route_to_connector)
      - 스크립트 편집기 지원 (조건부 실행 스크립트 포함)
      - conditional_branch 타입 액션 지원

  [5] ControlPanel.vue - 시뮬레이션 제어 (399줄)
      - 시뮬레이션 시작/중지/재설정
      - 스텝 실행 기능 (엔티티 이동 기반)
      - 시뮬레이션 속도 조절
      - 결과 표시 및 로그 출력

  [6] GlobalSignalPanel.vue - 글로벌 신호 관리 (331줄)
      - 시뮬레이션 전역 신호 생성/수정/삭제
      - 신호 타입: boolean, string, number
      - 신호 초기값 설정

■ 백엔드 시뮬레이션 엔진 (main.py - 1234줄)

  [핵심 기능]
  - SimPy 기반 이산 사건 시뮬레이션
  - 엔티티 기반 블록 간 이동 추적
  - 신호 시스템 (boolean 이벤트 기반)
  - 조건부 실행 스크립트 처리
  - 스텝 실행 (블록 간 이동 감지 기반)

  [API 엔드포인트]
  - POST /simulation/run         # 전체 시뮬레이션 실행
  - POST /simulation/step        # 스텝별 시뮬레이션 실행
  - POST /simulation/reset       # 시뮬레이션 상태 초기화

  [엔티티 관리]
  - Entity 클래스: id, name, current_block_id, current_block_name
  - active_entities_registry: 활성 엔티티 추적
  - 엔티티 생성/이동/배출 감지

  [스텝 실행 로직]
  - 엔티티 블록 간 이동 감지 기반 스텝 종료
  - check_entity_movement(): 이동 감지 함수
  - get_latest_movement_description(): 이동 설명 추출

■ 주요 데이터 구조

  [블록 (Block)]
  {
    id: number,
    name: string,
    x: number, y: number,
    width: number, height: number,
    maxCapacity: number,
    actions: Array<Action>,
    connectionPoints: Array<ConnectionPoint>
  }

  [연결점 (ConnectionPoint)]
  {
    id: string,
    name: string,
    x: number, y: number,    # 블록 내 상대 좌표
    actions: Array<Action>
  }

  [액션 (Action)]
  {
    id: string,
    name: string,
    type: 'delay' | 'signal_update' | 'signal_check' | 'signal_wait' | 'action_jump' | 'route_to_connector' | 'conditional_branch',
    parameters: Object
  }

  [신호 (Signal)]
  {
    name: string,
    type: 'boolean' | 'string' | 'number',
    initialValue: any
  }

  [엔티티 상태 (EntityState)]
  {
    id: string,
    current_block_id: string,
    current_block_name: string
  }

■ 액션 타입별 파라미터

  [delay] - 지연 시간
  parameters: { duration: number }

  [signal_update] - 신호 값 변경
  parameters: { signal_name: string, value: any }

  [signal_check] - 신호 값 체크
  parameters: { signal_name: string, expected_value: any }

  [signal_wait] - 신호 값 대기
  parameters: { signal_name: string, expected_value: any }

  [action_jump] - 다른 액션으로 이동
  parameters: { target_action_name: string }

  [route_to_connector] - 다른 블록/커넥터로 이동
  parameters: { 
    target_block_id?: number, 
    target_connector_id?: string, 
    connector_id?: string,    # 현재 블록 내 커넥터
    delay: number 
  }

  [conditional_branch] - 조건부 실행
  parameters: { script: string }

■ 스크립트 문법 (조건부 실행 및 스크립트 편집기)

  [기본 명령어]
  - delay 5                    # 5초 딜레이
  - 신호명 = true              # 신호 값 변경
  - if 신호명 = true           # 신호 값 체크 (하위 액션은 탭으로 들여쓰기)
  - wait 신호명 = true         # 신호가 true가 될 때까지 대기
  - go to self.커넥터명        # 현재 블록의 커넥터로 이동
  - go to 블록명.커넥터명      # 다른 블록의 커넥터로 이동
  - go to 블록명.커넥터명,3    # 3초 딜레이 후 이동
  - jump to 1                  # 1번째 라인으로 이동 (자동 0.1초 딜레이)
  - // 주석                    # 주석 처리

  [조건부 실행 예시]
  if 공정1 load enable = true
      공정1 load enable = false
      go to 공정1.LOAD,3
  if 공정2 load enable = true
      공정2 load enable = false
      go to 공정2.LOAD,3
  if 공정1 load enable = false
      delay 0.1
      jump to 1

■ 최근 해결된 주요 이슈들

  [시뮬레이션 엔진 개선]
  - jump to 명령어 백엔드 완전 지원 (자동 딜레이 포함)
  - 엔티티 블록 이동 기반 스텝 실행 구현
  - 조건부 실행 무한 루프 방지
  - 신호 기반 엔티티 투입 제어

  [UI/UX 개선]
  - 블록/커넥터 설정을 팝업에서 사이드바 형태로 변경
  - 사이드바 토글 기능 추가
  - 행동 목록 스크롤 영역 확대 (actions-list-container)
  - 스크립트 편집기 z-index 문제 해결 (999999로 설정)
  - 커넥터 설정창과 블록 설정창 UI 통일

  [캔버스 렌더링 문제]
  - Konva 캔버스 높이 0 문제 해결
  - CSS 레이아웃 수정 (height: 100vh, 100% 설정)
  - 동적 캔버스 크기 조정 기능
  - window resize 이벤트 처리
  - 캔버스 전체 드래그 기능 추가 (stage draggable)
  - 블록 드래그와 스테이지 드래그 충돌 방지 (cancelBubble)

  [조건부 실행 연결선 표시]
  - updateConnectionsFromRouteActions 함수 개선
  - extractRoutingFromScript 함수 추가
  - 조건부 실행 내 'go to' 명령어 파싱
  - 연결선 자동 생성 로직 강화

  [스크립트 편집기]
  - 실시간 구문 강조 및 유효성 검사
  - 행 번호 표시 및 스크롤 동기화
  - TAB 키 입력 지원
  - 사용 가능한 신호/블록 목록 표시
  - conditional_branch 타입 스크립트 변환 지원

■ 백엔드 핵심 함수

  [main.py]
  - execute_script_line(): 스크립트 라인별 실행
  - block_process(): 블록별 시뮬레이션 프로세스
  - check_entity_movement(): 엔티티 이동 감지
  - get_active_entity_states(): 활성 엔티티 상태 반환
  - run_simulation_endpoint(): 전체 시뮬레이션 실행
  - step_simulation_endpoint(): 스텝별 시뮬레이션 실행

  [Entity 클래스]
  - set_location(): 엔티티 위치 설정
  - 해시/동등성 지원 (Set 컬렉션용)

■ 개발/디버깅 팁

  [프론트엔드 실행]
  cd frontend
  npm install
  npm run dev
  # 개발 서버: http://localhost:5173

  [백엔드 실행]
  cd backend
  pip install -r requirements.txt
  cd app
  python -m uvicorn main:app --reload --port 8000
  # API 서버: http://localhost:8000

  [주요 디버깅 포인트]
  - App.vue의 onMounted에서 초기화 상태 로그 확인
  - CanvasArea.vue의 drawCanvasContent에서 렌더링 상태 확인
  - 블록/커넥터 클릭 이벤트가 올바르게 emit되는지 확인
  - 스크립트 파싱 오류는 콘솔에서 상세 메시지 확인
  - 백엔드 로그에서 시뮬레이션 진행 상황 모니터링

  [컴포넌트 props 체크]
  - BlockSettingsPopup: blockData, allSignals, allBlocks, isSidebar
  - ConnectorSettingsPopup: connectorInfo, allSignals, allBlocks, isSidebar
  - CanvasArea: blocks, connections, currentSettings

■ 향후 개발 방향

  [기능 확장]
  - 더 복잡한 공정 플로우 지원
  - 시뮬레이션 결과 차트/그래프 표시
  - 시뮬레이션 설정 템플릿 시스템
  - 실시간 공정 모니터링 대시보드
  - 시뮬레이션 히스토리 및 되돌리기 기능

  [성능 최적화]
  - 대용량 블록 처리 최적화
  - 캔버스 렌더링 성능 개선
  - 메모리 사용량 최적화
  - 시뮬레이션 스텝 실행 속도 향상

■ 문제 해결 체크리스트

  [캔버스가 보이지 않는 경우]
  1. CSS height 설정 확인 (App.vue, CanvasArea.vue)
  2. Konva stage/layer 초기화 상태 확인
  3. 브라우저 콘솔에서 JavaScript 오류 확인
  4. 캔버스 컨테이너 DOM 요소 존재 확인

  [스크립트 편집기가 표시되지 않는 경우]
  1. showScriptEditor ref 값 확인
  2. z-index 설정 확인 (999999)
  3. 부모 컨테이너의 overflow 설정 확인

  [연결선이 표시되지 않는 경우]
  1. route_to_connector 액션 파라미터 확인
  2. updateConnectionsFromRouteActions 함수 실행 확인
  3. 대상 블록/커넥터 존재 여부 확인

  [시뮬레이션이 진행되지 않는 경우]
  1. 백엔드 서버 실행 상태 확인
  2. 초기 신호 설정 확인
  3. 조건부 실행 스크립트 구문 오류 확인
  4. jump to 명령어 무한 루프 방지 확인

■ 주요 파일별 핵심 함수

  [App.vue]
  - setupInitialScenario(): 초기 시나리오 설정 (투입→공정1→배출)
  - handleBlockClicked(): 블록 클릭 처리
  - handleConnectorClicked(): 커넥터 클릭 처리
  - updateConnectionsFromRouteActions(): 연결선 업데이트
  - extractRoutingFromScript(): 조건부 실행 스크립트에서 라우팅 추출
  - parseConditionalBranch(): 조건부 분기 스크립트 파싱

  [CanvasArea.vue]
  - initKonva(): Konva 캔버스 초기화
  - drawCanvasContent(): 전체 캔버스 내용 그리기
  - drawBlock(): 개별 블록 그리기
  - drawConnections(): 연결선 그리기
  - resizeCanvas(): 캔버스 크기 동적 조정

  [BlockSettingsPopup.vue]
  - parseAdvancedScript(): 고급 스크립트 파싱
  - parseConditionalBranch(): 조건부 분기 파싱
  - convertActionToScript(): 액션을 스크립트로 변환
  - updateConditionalScript(): GUI에서 스크립트로 변환
  - openScriptEditor(): 스크립트 편집기 열기
  - loadCurrentActionsAsScript(): 현재 액션을 스크립트로 로드

  [ConnectorSettingsPopup.vue]
  - BlockSettingsPopup과 동일한 함수들 (완전히 통일된 구조)

■ 시뮬레이션 설정 파일 구조

  [simulation-config-*.json]
  - settings: 박스 크기, 폰트 크기
  - blocks: 블록 정의 (id, name, x, y, actions, connectionPoints)
  - connections: 블록 간 연결 (from_block_id, to_block_id, connector_id)
  - signals: 글로벌 신호 초기값

■ 최신 업데이트 내용 (2025-05-31)

  [시뮬레이션 엔진 개선]
  - jump to 명령어 백엔드 완전 지원 (자동 딜레이 포함)
  - 엔티티 블록 이동 기반 스텝 실행 구현
  - 조건부 실행 무한 루프 방지 메커니즘
  - 시뮬레이션 상태 완전 초기화 기능

  [UI 기능 완성]
  - 커넥터 설정창과 블록 설정창 완전 통일
  - 캔버스 드래그 기능 안정화
  - 스크립트 편집기 기능 완성



================================================================================================
                                   프로젝트 개발 상태: 완성
================================================================================================

현재 이 프로젝트는 기본적인 공정 시뮬레이션 기능이 모두 구현되어 완성된 상태입니다.
- 블록 기반 공정 설계 ✅
- 조건부 실행 스크립트 ✅  
- 엔티티 이동 추적 ✅
- 스텝별 시뮬레이션 ✅
- 신호 기반 제어 ✅
- 실시간 시각화 ✅ 
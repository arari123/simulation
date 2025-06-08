# 스텝 실행 간격 조정 모드 구현 TODO

## 1. 개요

시뮬레이션 엔진의 실행 모드를 다양화하여 사용자가 시뮬레이션 목적에 맞는 최적의 실행 방식을 선택할 수 있도록 합니다.

### 주요 목표
- 기존 엔진 코드를 수정하지 않고 모듈화된 접근 방식 사용
- 다양한 실행 모드 제공으로 시뮬레이션 유연성 증가
- 고속 실행 모드로 대규모 시뮬레이션 성능 향상

## 2. 실행 모드 정의

### 2.1 기본 모드 (Default Mode)
- **현재 동작 방식 유지**
- 매 스텝마다 프론트엔드 업데이트
- 브레이크포인트 지원
- 실시간 시각화

### 2.2 시간 스텝 모드 (Time Step Mode)
- **사용자 지정 시간을 1스텝으로 정의**
- 사용자가 임의의 시간(초) 입력 가능 (예: 2.5초, 7초, 15초 등)
- 스텝 실행 버튼 클릭 시 입력된 시간만큼 시뮬레이션 진행
- 예: 5초로 설정 시, 스텝 실행 버튼 한 번 = 5초 시뮬레이션 진행
- 브레이크포인트 지원 (시간 내에서도 브레이크포인트 동작)
- 현재 모드와 동일하게 스텝 단위 실행, 단지 1스텝의 기준이 시간으로 변경

### 2.3 고속 진행 모드 (High-Speed Mode)
- **백엔드 전용 실행**
- 프론트엔드 업데이트 없음 (최종 결과만)
- 브레이크포인트 무시
- 종료 조건:
  - 지정된 배출 수량 도달
  - 지정된 시뮬레이션 시간 경과
  - 데드락 감지

## 3. 기술 아키텍처

### 3.1 모듈 구조
```python
# 베이스 인터페이스
class StepExecutor(ABC):
    @abstractmethod
    async def execute_step(self, engine, *args, **kwargs):
        pass
    
    @abstractmethod
    def get_mode_config(self):
        pass

# 기본 모드
class DefaultStepExecutor(StepExecutor):
    async def execute_step(self, engine):
        return await engine._default_step()

# 시간 스텝 모드
class TimeStepExecutor(StepExecutor):
    def __init__(self, step_duration: float):
        self.step_duration = step_duration  # 1스텝 = 사용자 지정 시간
    
    async def execute_step(self, engine):
        # 지정된 시간만큼 시뮬레이션 진행
        start_time = engine.current_time
        target_time = start_time + self.step_duration
        
        # 백엔드에서 지정 시간만큼 진행
        while engine.current_time < target_time:
            # SimPy 이벤트 실행
            await engine.env.step()
            
            # 브레이크포인트 체크
            if engine.is_paused_at_breakpoint:
                break
        
        # 프론트엔드로 최종 상태 전송

# 고속 모드
class HighSpeedExecutor(StepExecutor):
    def __init__(self, config: dict):
        self.target_count = config.get('target_count')
        self.target_time = config.get('target_time')
        self.update_interval = config.get('update_interval', 100)  # 100 스텝마다 진행상황 업데이트
```

### 3.2 엔진 통합
```python
class SimpleSimulationEngine:
    def __init__(self):
        self.step_executor = DefaultStepExecutor()
        self.execution_mode = "default"
    
    def set_execution_mode(self, mode: str, config: dict = None):
        if mode == "default":
            self.step_executor = DefaultStepExecutor()
        elif mode == "time_step":
            step_duration = config.get('step_duration', 1.0)  # 1스텝당 시간
            self.step_executor = TimeStepExecutor(step_duration)
        elif mode == "high_speed":
            self.step_executor = HighSpeedExecutor(config)
        
        self.execution_mode = mode
```

## 4. 구현 작업 목록

### Phase 1: 모드 선택 기반 구조 (2시간)

#### 1.1 백엔드 최소 수정
- [ ] `models.py`에 ExecutionModeRequest 모델 추가
- [ ] `routes/simulation.py`에 모드 설정/조회 API 추가
  - [ ] POST `/simulation/execution-mode`
  - [ ] GET `/simulation/execution-mode`
- [ ] 현재는 default 모드만 허용, 다른 모드는 501 에러 반환

#### 1.2 프론트엔드 UI 추가
- [ ] `SimulationApi.js`에 모드 관련 API 함수 추가
- [ ] `ControlPanel.vue`에 모드 선택 드롭다운 추가
- [ ] 실행 중에는 모드 변경 비활성화
- [ ] 미구현 모드는 disabled 표시

#### 1.3 기본 모드 동작 테스트
- [ ] 모든 기존 기능 정상 동작 확인
- [ ] 브레이크포인트, 신호, 변수, 스크립트 등
- [ ] 페이지 새로고침 후 모드 유지 확인

### Phase 2: 시간 스텝 모드 구현 (Phase 1 완료 후)

#### 2.1 백엔드 엔진 확장
- [ ] `simple_simulation_engine.py`에 시간 기반 스텝 로직 추가
- [ ] 1스텝 = 사용자 지정 시간 처리
- [ ] 시간 단위 스텝 실행 루프 구현
- [ ] 브레이크포인트 통합

#### 2.2 프론트엔드 UI 활성화
- [ ] 시간 스텝 모드 선택 시 설정 UI 표시
- [ ] "1스텝 = [ ] 초" 입력 필드
- [ ] 설정 저장 버튼
- [ ] 현재 시뮬레이션 시간 표시

#### 2.3 테스트
- [ ] 다양한 시간 설정 테스트 (0.5초, 2.3초, 100초 등)
- [ ] 브레이크포인트 동작 확인
- [ ] 시간 정확도 테스트 (±5% 이내)
- [ ] 기본 모드 ↔ 시간 스텝 모드 전환 테스트

### Phase 3: 고속 진행 모드 (Phase 2 완료 후)

#### 3.1 HighSpeedExecutor 구현
- [ ] 백엔드 전용 실행 루프
- [ ] 진행 상황 추적 시스템
- [ ] 종료 조건 검사 로직
- [ ] 메모리 효율적인 상태 관리

#### 3.2 진행 상황 보고
- [ ] WebSocket을 통한 진행률 업데이트
- [ ] 중간 통계 수집 (처리량, 속도 등)
- [ ] 실행 완료 후 전체 결과 전송

#### 3.3 프론트엔드 UI
- [ ] 고속 모드 설정 다이얼로그
  - [ ] 목표 배출 수량 입력
  - [ ] 목표 시간 입력
  - [ ] 업데이트 간격 설정
- [ ] 진행률 표시 컴포넌트
- [ ] 실행 중단 버튼
- [ ] 최종 결과 표시 패널

#### 3.4 성능 최적화
- [ ] 불필요한 상태 업데이트 제거
- [ ] 메모리 사용량 모니터링
- [ ] 배치 처리 최적화

### Phase 4: 전체 통합 및 최적화 (Phase 3 완료 후)

#### 4.1 컨트롤 패널 업데이트
- [ ] "전체 실행" → "스텝 연속 실행" 버튼 이름 변경
- [ ] 실행 모드 선택 드롭다운 추가
- [ ] 모드별 아이콘 및 툴팁

#### 4.2 모드 전환 로직
- [ ] 실행 중 모드 전환 방지
- [ ] 모드 전환 시 상태 초기화
- [ ] 모드별 UI 요소 활성화/비활성화

#### 4.3 사용자 가이드
- [ ] 각 모드 설명 툴팁
- [ ] 모드 선택 가이드라인
- [ ] 성능 비교 정보

## 5. 상세 구현 사항

### 5.1 고속 모드 상태 관리
```python
class HighSpeedState:
    def __init__(self):
        self.steps_executed = 0
        self.entities_processed = 0
        self.sink_counts = {}
        self.start_time = time.time()
        self.checkpoints = []  # 주기적 스냅샷
    
    def should_update_frontend(self):
        return self.steps_executed % self.update_interval == 0
    
    def create_checkpoint(self):
        # 현재 상태 스냅샷 저장
        pass
```

### 5.2 WebSocket 메시지 형식
```json
{
  "type": "high_speed_progress",
  "data": {
    "steps_executed": 10000,
    "progress_percentage": 45.5,
    "entities_processed": 523,
    "elapsed_time": 2.3,
    "estimated_remaining": 3.2,
    "current_stats": {
      "sink_counts": {"Sink1": 234, "Sink2": 289},
      "avg_processing_time": 0.023
    }
  }
}
```

### 5.3 종료 조건 설정
```typescript
interface TimeStepConfig {
  duration: number;  // 사용자가 입력한 실행 시간 (초)
  pauseAfter: boolean;  // 시간 경과 후 일시정지 (기본값: true)
}

interface HighSpeedConfig {
  mode: 'count' | 'time' | 'both';
  targetCount?: number;
  targetTime?: number;
  sinkName?: string;  // 특정 sink의 카운트만 체크
  updateInterval?: number;
  includeStats?: boolean;
}
```

## 6. 테스트 계획

### 6.1 단위 테스트
- [ ] 각 Executor 클래스 테스트
- [ ] 모드 전환 테스트
- [ ] 종료 조건 테스트

### 6.2 통합 테스트
- [ ] 전체 시뮬레이션 플로우 테스트
- [ ] WebSocket 통신 테스트
- [ ] 에러 처리 테스트

### 6.3 성능 테스트
- [ ] 고속 모드 vs 기본 모드 속도 비교
- [ ] 메모리 사용량 측정
- [ ] 대규모 시뮬레이션 (10만+ 스텝) 테스트

## 7. 예상 문제점 및 해결 방안

### 7.1 메모리 관리
**문제**: 고속 모드에서 대량의 로그/이벤트 누적
**해결**: 
- 순환 버퍼 사용
- 주기적 가비지 컬렉션
- 중요 통계만 유지

### 7.2 데드락 감지
**문제**: 고속 모드에서 데드락 시 무한 루프
**해결**:
- 스텝당 진행 상황 모니터링
- 타임아웃 설정
- 자동 중단 메커니즘

### 7.3 상태 동기화
**문제**: 모드 전환 시 상태 불일치
**해결**:
- 명확한 상태 전환 프로토콜
- 전환 전 검증
- 롤백 메커니즘

## 8. 구현 우선순위

1. **Phase 1** (2시간)
   - 모드 선택 UI만 추가
   - 기본 모드 동작 100% 보장
   - 완전한 테스트 후 다음 단계 진행

2. **Phase 2** (Phase 1 테스트 완료 후)
   - 시간 스텝 모드 구현
   - 기본 모드는 전혀 수정하지 않음

3. **Phase 3** (Phase 2 테스트 완료 후)
   - 고속 진행 모드
   - 진행 상황 보고
   - 기본 UI

4. **Phase 4** (전체 기능 통합)
   - UI/UX 최적화
   - 고급 설정 옵션
   - 성능 튜닝

## 9. 성공 지표

- 시간 스텝 모드: 사용자 지정 시간 정확도 ±5% 이내
- 고속 모드에서 10배 이상 성능 향상
- 모든 모드에서 기존 기능 정상 작동
- 사용자 피드백 기반 만족도 향상
- 메모리 사용량 50% 이내 유지

## 10. 시간 스텝 모드 사용 예시

### 사용자 시나리오
1. 사용자가 "시간 스텝" 모드 선택
2. "1스텝 = 5초"로 설정
3. 스텝 실행 버튼 클릭 → 백엔드에서 5초간 시뮬레이션 진행 → 프론트엔드 업데이트
4. 다시 스텝 실행 버튼 클릭 → 백엔드에서 추가 5초 진행 → 프론트엔드 업데이트
5. 브레이크포인트에 걸리면 시간 내에서도 중단

### 시간 진행 예시 (1스텝 = 5초)
- 0초 (초기 상태)
- [스텝 실행] → 5초
- [스텝 실행] → 10초
- [스텝 실행] → 15초
- (브레이크포인트 발생 시 예: 12.3초에서 중단 가능)

### UI 목업
```
실행 모드: [시간 스텝 ▼]
1스텝 = [____5____] 초 [설정]

현재 시뮬레이션 시간: 45초
[스텝 실행] [스텝 연속 실행]
```

### 모드 비교
| 모드 | 1스텝 기준 | 백엔드 처리 | 프론트엔드 업데이트 | 브레이크포인트 |
|------|-----------|-------------|-------------------|---------------|
| 기본 | 엔티티 이동/생성/배출 | 이벤트 발생까지 | 스텝 완료 후 | 지원 |
| 시간 스텝 | 사용자 지정 시간 | 지정 시간만큼 | 스텝 완료 후 | 지원 |
| 고속 | N/A (연속 실행) | 목표 도달까지 | 최종 결과만 | 무시 |
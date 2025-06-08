# 실행 모드 선택 기능 구현 계획

## 목표
- 실행 모드 선택 UI 추가
- 백엔드에 모드 분기 처리 구현
- **기본 모드는 현재 동작 그대로 유지**
- 다른 모드는 미구현 상태로 두되, 추후 확장 가능한 구조로 설계

## 1단계: 프론트엔드 UI 구현

### 1.1 ControlPanel.vue 수정
```vue
<!-- 실행 모드 선택 추가 -->
<div class="execution-mode">
  <label>실행 모드:</label>
  <select v-model="executionMode" @change="onModeChange">
    <option value="default">기본 모드</option>
    <option value="time_step" disabled>시간 스텝 (준비중)</option>
    <option value="high_speed" disabled>고속 진행 (준비중)</option>
  </select>
</div>

<!-- 모드별 추가 설정 (시간 스텝 모드용, 현재는 숨김) -->
<div v-if="executionMode === 'time_step'" class="time-step-config">
  <label>1스텝 = </label>
  <input type="number" v-model="stepDuration" min="0.1" step="0.1"> 초
  <button @click="applyTimeStep">설정</button>
</div>
```

### 1.2 useSimulation.js 수정
```javascript
// 실행 모드 상태 추가
const executionMode = ref('default');
const stepDuration = ref(1.0);

// 모드 변경 API 호출
const setExecutionMode = async (mode, config = {}) => {
  try {
    await SimulationApi.setExecutionMode(mode, config);
    executionMode.value = mode;
  } catch (error) {
    console.error('Failed to set execution mode:', error);
  }
};
```

## 2단계: 백엔드 API 구현

### 2.1 routes/simulation.py 수정
```python
@router.post("/execution-mode")
async def set_execution_mode(request: ExecutionModeRequest):
    """실행 모드 설정"""
    engine_adapter.set_execution_mode(request.mode, request.config)
    return {"success": True, "mode": request.mode}

@router.get("/execution-mode")
async def get_execution_mode():
    """현재 실행 모드 조회"""
    return {
        "mode": engine_adapter.get_execution_mode(),
        "config": engine_adapter.get_mode_config()
    }
```

### 2.2 models.py 추가
```python
class ExecutionModeRequest(BaseModel):
    mode: str = Field(..., description="실행 모드: default, time_step, high_speed")
    config: dict = Field(default_factory=dict, description="모드별 설정")
```

### 2.3 simple_engine_adapter.py 수정
```python
class SimpleEngineAdapter:
    def __init__(self):
        self.engine = None
        self.execution_mode = "default"
        self.mode_config = {}
    
    def set_execution_mode(self, mode: str, config: dict = None):
        """실행 모드 설정"""
        self.execution_mode = mode
        self.mode_config = config or {}
        
        # 엔진이 있으면 모드 적용
        if self.engine:
            self.engine.set_execution_mode(mode, config)
    
    def get_execution_mode(self):
        return self.execution_mode
    
    def get_mode_config(self):
        return self.mode_config
```

### 2.4 simple_simulation_engine.py 수정
```python
class SimpleSimulationEngine:
    def __init__(self):
        # 기존 코드...
        self.execution_mode = "default"
        self.mode_config = {}
    
    def set_execution_mode(self, mode: str, config: dict = None):
        """실행 모드 설정"""
        self.execution_mode = mode
        self.mode_config = config or {}
        
        # 향후 모드별 executor 설정 예정
        # if mode == "time_step":
        #     self.step_executor = TimeStepExecutor(config)
        # elif mode == "high_speed":
        #     self.step_executor = HighSpeedExecutor(config)
    
    async def step_simulation(self):
        """스텝 실행 - 현재는 기본 모드만 동작"""
        if self.execution_mode == "default":
            # 기존 코드 그대로 실행
            return await self._default_step_simulation()
        else:
            # 다른 모드는 아직 미구현
            raise NotImplementedError(f"Mode '{self.execution_mode}' is not implemented yet")
    
    async def _default_step_simulation(self):
        """기존 스텝 실행 로직 (변경 없음)"""
        # 현재 step_simulation 메서드의 내용을 그대로 이동
        # ... (기존 코드)
```

## 3단계: 테스트 계획

### 3.1 기본 모드 동작 테스트
1. 시뮬레이션 시작
2. 모드 선택이 "기본 모드"인지 확인
3. 스텝 실행이 기존과 동일하게 동작하는지 확인
4. 브레이크포인트, 신호, 변수 등 모든 기능 정상 동작 확인

### 3.2 모드 전환 테스트
1. 시뮬레이션 중지 상태에서 모드 변경 시도
2. API 응답 확인
3. 모드 상태 유지 확인

### 3.3 에러 처리 테스트
1. 미구현 모드 선택 시 적절한 에러 메시지 표시
2. 시뮬레이션 실행 중 모드 변경 방지

## 구현 순서

1. **백엔드 API 엔드포인트 추가** (30분)
   - 모드 설정/조회 API
   - 모델 정의

2. **엔진 모드 분기 처리** (1시간)
   - set_execution_mode 메서드 추가
   - step_simulation 분기 처리
   - 기존 로직을 _default_step_simulation으로 이동

3. **프론트엔드 UI 추가** (1시간)
   - 모드 선택 드롭다운
   - API 연동
   - 상태 관리

4. **통합 테스트** (30분)
   - 기본 모드 동작 확인
   - 모든 기존 기능 정상 동작 확인

## 주의사항

1. **기존 코드 보존**
   - 현재 step_simulation 로직은 그대로 유지
   - 단순히 메서드명만 변경하여 _default_step_simulation으로 이동

2. **하위 호환성**
   - 모드 설정하지 않으면 자동으로 "default" 모드로 동작
   - 기존 시뮬레이션 파일도 정상 동작

3. **확장성**
   - 향후 다른 모드 추가 시 쉽게 확장 가능한 구조
   - 모드별 설정을 config 딕셔너리로 유연하게 처리

이 구현이 완료되고 기본 모드가 정상 동작하면, 그 다음에 시간 스텝 모드와 고속 진행 모드를 순차적으로 구현할 수 있습니다.
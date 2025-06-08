# Phase 1: 간소화된 모드 선택 기능 구현

## 목표
- 모드 선택 UI만 추가
- 백엔드는 최소한의 수정으로 기본 모드 동작 보장
- 기존 코드 변경 최소화

## 구현 작업 (2시간 내 완료 가능)

### 1. 백엔드 수정 (30분)

#### 1.1 models.py에 추가
```python
class ExecutionModeRequest(BaseModel):
    mode: str = "default"
    config: dict = {}
```

#### 1.2 routes/simulation.py에 추가
```python
# 전역 변수로 모드 저장
current_execution_mode = "default"

@router.post("/execution-mode")
async def set_execution_mode(request: ExecutionModeRequest):
    global current_execution_mode
    if request.mode not in ["default", "time_step", "high_speed"]:
        raise HTTPException(400, "Invalid execution mode")
    
    # 현재는 default만 허용
    if request.mode != "default":
        raise HTTPException(501, f"Mode '{request.mode}' is not implemented yet")
    
    current_execution_mode = request.mode
    return {"success": True, "mode": current_execution_mode}

@router.get("/execution-mode")
async def get_execution_mode():
    return {"mode": current_execution_mode}
```

### 2. 프론트엔드 수정 (30분)

#### 2.1 SimulationApi.js에 추가
```javascript
// 실행 모드 설정
export const setExecutionMode = async (mode, config = {}) => {
  const response = await fetch(`${API_BASE_URL}/simulation/execution-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, config })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to set execution mode');
  }
  return response.json();
};

// 실행 모드 조회
export const getExecutionMode = async () => {
  const response = await fetch(`${API_BASE_URL}/simulation/execution-mode`);
  return response.json();
};
```

#### 2.2 ControlPanel.vue에 추가
```vue
<template>
  <!-- 시뮬레이션 제어 버튼들 위에 추가 -->
  <div class="execution-mode-selector">
    <label>실행 모드:</label>
    <select v-model="executionMode" @change="changeExecutionMode" :disabled="isRunning">
      <option value="default">기본 모드 (엔티티 이벤트)</option>
      <option value="time_step" disabled>시간 스텝 모드 (준비중)</option>
      <option value="high_speed" disabled>고속 진행 모드 (준비중)</option>
    </select>
  </div>
  
  <!-- 기존 버튼들... -->
</template>

<script setup>
import { ref, onMounted } from 'vue';
import * as SimulationApi from '../services/SimulationApi';

const executionMode = ref('default');

// 컴포넌트 마운트 시 현재 모드 조회
onMounted(async () => {
  try {
    const { mode } = await SimulationApi.getExecutionMode();
    executionMode.value = mode;
  } catch (error) {
    console.error('Failed to get execution mode:', error);
  }
});

// 모드 변경
const changeExecutionMode = async () => {
  try {
    await SimulationApi.setExecutionMode(executionMode.value);
  } catch (error) {
    alert(error.message);
    // 실패 시 원래 모드로 복원
    executionMode.value = 'default';
  }
};
</script>

<style scoped>
.execution-mode-selector {
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.execution-mode-selector label {
  margin-right: 10px;
}

.execution-mode-selector select {
  padding: 5px;
  border-radius: 3px;
}
</style>
```

### 3. 테스트 체크리스트 (1시간)

#### 3.1 기본 기능 테스트
- [ ] 시뮬레이션 로드
- [ ] 모드 선택 UI 표시 확인
- [ ] 기본 모드 선택 상태 확인
- [ ] 스텝 실행 정상 동작
- [ ] 전체 실행 정상 동작
- [ ] 정지/리셋 정상 동작

#### 3.2 기존 기능 호환성 테스트
- [ ] 브레이크포인트 동작
- [ ] 신호 변경 동작
- [ ] 정수 변수 동작
- [ ] 엔티티 생성/이동/삭제
- [ ] 스크립트 실행
- [ ] 로그 표시

#### 3.3 모드 전환 테스트
- [ ] 실행 중 모드 선택 비활성화 확인
- [ ] 미구현 모드 선택 시 에러 메시지
- [ ] 페이지 새로고침 후 모드 유지

## 예상 결과

1. **UI 변경사항**
   - 컨트롤 패널 상단에 모드 선택 드롭다운 추가
   - 현재는 "기본 모드"만 선택 가능

2. **동작 변경사항**
   - 없음 (기존과 100% 동일하게 동작)

3. **향후 확장성**
   - 모드 선택 API 준비 완료
   - 다른 모드 구현 시 백엔드/프론트엔드 최소 수정으로 추가 가능

이 Phase 1을 완료하면 기본 모드가 정상 동작하는 것을 확인할 수 있고, 이후 다른 모드를 안전하게 추가할 수 있습니다.
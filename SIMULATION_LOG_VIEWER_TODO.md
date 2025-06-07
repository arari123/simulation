# 시뮬레이션 로그 뷰어 구현 상세 계획

## 개요
현재 백엔드에서 스크립트 `log` 명령어는 이미 구현되어 있으며, 변수 보간 기능도 완료되어 있습니다. 
하지만 로그가 백엔드 콘솔에만 출력되고 있어, 이를 웹 UI에서 볼 수 있도록 구현해야 합니다.

## 현재 상태 분석
- ✅ `log` 명령어 파싱 완료 (`simple_script_executor.py`)
- ✅ 변수 보간 기능 완료 (`{변수}` 형식 지원)
- ✅ 로그 데이터 저장 (`simulation_logs` 리스트)
- ❌ 프론트엔드로 로그 전송 미구현
- ❌ 웹 UI 로그 뷰어 미구현

## 구현 계획

### Phase 1: 백엔드 로그 수집 및 전송 시스템

#### 1.1 Script Executor 로그 수집 개선
```python
# simple_script_executor.py
class SimpleScriptExecutor:
    def get_simulation_logs(self):
        """현재까지 수집된 시뮬레이션 로그 반환"""
        return self.simulation_logs.copy()
    
    def clear_logs(self):
        """로그 초기화 (옵션)"""
        self.simulation_logs = []
```

#### 1.2 Block 레벨 로그 수집
```python
# simple_block.py
class SimpleBlock:
    def get_script_logs(self):
        """블록의 스크립트 실행 로그 반환"""
        if self.script_executor:
            return self.script_executor.get_simulation_logs()
        return []
```

#### 1.3 Engine 레벨 로그 집계
```python
# simple_simulation_engine.py
def collect_script_logs(self):
    """모든 블록의 스크립트 로그 수집"""
    all_logs = []
    for block in self.blocks.values():
        logs = block.get_script_logs()
        all_logs.extend(logs)
    # 시간순 정렬
    all_logs.sort(key=lambda x: x['time'])
    return all_logs
```

#### 1.4 API Response 확장
```python
# models.py
class SimulationStepResult(BaseModel):
    # 기존 필드들...
    script_logs: Optional[List[Dict[str, Any]]] = None  # 스크립트 로그 추가

# simple_engine_adapter.py
def convert_simple_result_to_api_format(self, result):
    return {
        # 기존 필드들...
        'script_logs': result.get('script_logs', [])
    }
```

### Phase 2: 프론트엔드 로그 뷰어 UI

#### 2.1 로그 패널 컴포넌트 (`LogPanel.vue`)
```vue
<template>
  <div class="log-panel" :class="{ minimized: isMinimized }">
    <!-- 헤더 -->
    <div class="log-header" @click="toggleMinimize">
      <span class="title">📋 시뮬레이션 로그</span>
      <div class="controls">
        <button @click.stop="clearLogs" title="로그 지우기">🗑️</button>
        <button @click.stop="exportLogs" title="로그 내보내기">💾</button>
        <button @click.stop="toggleMinimize" title="최소화/최대화">
          {{ isMinimized ? '▲' : '▼' }}
        </button>
      </div>
    </div>
    
    <!-- 로그 필터 -->
    <div v-if="!isMinimized" class="log-filters">
      <input 
        v-model="filterText" 
        placeholder="로그 검색..."
        class="filter-input"
      >
      <select v-model="filterBlock" class="filter-select">
        <option value="">모든 블록</option>
        <option v-for="block in uniqueBlocks" :key="block">
          {{ block }}
        </option>
      </select>
    </div>
    
    <!-- 로그 내용 -->
    <div v-if="!isMinimized" class="log-content" ref="logContentRef">
      <div 
        v-for="(log, index) in filteredLogs" 
        :key="index"
        class="log-entry"
        :class="getLogClass(log)"
      >
        <span class="log-time">[{{ formatTime(log.time) }}s]</span>
        <span class="log-block">[{{ log.block }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      <div v-if="filteredLogs.length === 0" class="no-logs">
        로그가 없습니다
      </div>
    </div>
  </div>
</template>
```

#### 2.2 위치 및 스타일링
- **위치**: 캔버스 하단 또는 오른쪽 패널
- **크기**: 
  - 최소화: 헤더만 표시 (높이 40px)
  - 최대화: 200-300px 높이, 스크롤 가능
- **반응형**: 화면 크기에 따라 자동 조정

#### 2.3 주요 기능
1. **실시간 업데이트**: 새 로그 자동 추가
2. **자동 스크롤**: 새 로그 추가 시 하단으로 스크롤
3. **필터링**: 
   - 텍스트 검색
   - 블록별 필터
4. **로그 레벨**: 
   - 일반 로그
   - 경고 (특정 키워드 포함 시)
   - 오류 (에러 키워드 포함 시)
5. **내보내기**: 
   - TXT 형식
   - CSV 형식
   - JSON 형식

### Phase 3: 데이터 흐름 및 상태 관리

#### 3.1 Composable (`useSimulationLogs.js`)
```javascript
export function useSimulationLogs() {
  const logs = ref([])
  const maxLogs = 1000 // 최대 로그 수 제한
  
  function addLogs(newLogs) {
    logs.value.push(...newLogs)
    // 최대 로그 수 제한
    if (logs.value.length > maxLogs) {
      logs.value = logs.value.slice(-maxLogs)
    }
  }
  
  function clearLogs() {
    logs.value = []
  }
  
  function exportLogs(format = 'txt') {
    // 로그 내보내기 로직
  }
  
  return {
    logs,
    addLogs,
    clearLogs,
    exportLogs
  }
}
```

#### 3.2 App.vue 통합
```javascript
// 시뮬레이션 스텝 결과 처리
function updateSimulationState(result) {
  // 기존 코드...
  
  // 스크립트 로그 추가
  if (result.script_logs) {
    simulationLogs.addLogs(result.script_logs)
  }
}
```

### Phase 4: 고급 기능 (선택적)

#### 4.1 로그 영속성
- LocalStorage에 로그 저장
- 세션 간 로그 유지 옵션

#### 4.2 로그 분석
- 로그 통계 (블록별 로그 수)
- 시간대별 로그 분포
- 자주 나타나는 패턴 분석

#### 4.3 디버깅 지원
- 로그 시점의 시뮬레이션 상태 표시
- 특정 로그 클릭 시 해당 블록 하이라이트

## 구현 순서

### 1단계: 백엔드 (2시간)
1. Script Executor에 로그 접근 메서드 추가
2. Block에 로그 수집 메서드 추가
3. Engine에 로그 집계 로직 추가
4. API Response에 script_logs 필드 추가

### 2단계: 프론트엔드 기본 UI (3시간)
1. LogPanel 컴포넌트 생성
2. 기본 로그 표시 기능
3. 최소화/최대화 토글
4. App.vue 통합

### 3단계: 필터링 및 검색 (2시간)
1. 텍스트 검색 기능
2. 블록별 필터
3. 자동 스크롤

### 4단계: 내보내기 기능 (1시간)
1. TXT 내보내기
2. CSV 내보내기
3. JSON 내보내기

### 5단계: 스타일링 및 최적화 (1시간)
1. 로그 레벨별 색상
2. 성능 최적화
3. 반응형 디자인

## 기술적 고려사항

### 성능
- 대량 로그 처리를 위한 가상 스크롤 고려
- 로그 수 제한 (1000개)
- 디바운싱 적용 (검색)

### 보안
- XSS 방지 (로그 메시지 이스케이프)
- 민감정보 필터링

### 접근성
- 키보드 네비게이션
- 스크린 리더 지원
- 고대비 모드

## 예상 결과

### 사용자 경험
1. 시뮬레이션 실행 중 실시간 로그 확인
2. 문제 발생 시 로그를 통한 디버깅
3. 로그 내보내기로 기록 보관

### 기술적 이점
1. 기존 로그 시스템 재활용
2. 최소한의 백엔드 수정
3. 확장 가능한 구조

## 위험 요소 및 대응

### 위험 요소
1. 대량 로그로 인한 성능 저하
2. 메모리 사용량 증가
3. 네트워크 트래픽 증가

### 대응 방안
1. 로그 수 제한 및 페이징
2. 로그 레벨 필터링
3. 압축 전송 고려

## 테스트 계획

### 단위 테스트
1. 로그 수집 로직
2. 필터링 로직
3. 내보내기 기능

### 통합 테스트
1. 시뮬레이션 실행 중 로그 수집
2. 다중 블록 로그 처리
3. 대량 로그 성능 테스트

### 사용자 테스트
1. UI/UX 피드백
2. 성능 체감 테스트
3. 버그 리포트
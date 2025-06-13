# 프론트엔드 최적화 계획

## 개요
현재 시뮬레이션의 주요 성능 병목은 백엔드 엔진이 아닌 프론트엔드-백엔드 통신과 프론트엔드 렌더링에 있습니다.

### 현재 성능 분석
- **백엔드 엔진**: 10개 엔티티 처리에 0.13초 (충분히 빠름)
- **실제 사용자 경험**: 같은 작업에 수 초 이상 소요
- **주요 병목**: HTTP 통신 오버헤드, Canvas 렌더링

## 1. 프론트엔드-백엔드 통신 최적화

### 1.1 Batch Step 실행 구현 (단기 - 1주일)

#### 현재 문제점
- 매 스텝마다 HTTP POST 요청 발생
- 72초 시뮬레이션 = 72번의 HTTP 요청
- 각 요청마다 네트워크 지연 + JSON 직렬화/역직렬화 오버헤드

#### 구현 계획
```javascript
// frontend/src/services/SimulationApi.js
async batchStepSimulation(steps) {
  const response = await fetch(`${API_BASE}/simulation/batch-step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steps })
  })
  return response.json()
}

// frontend/src/composables/useSimulation.js
const BATCH_SIZE = {
  default: 5,      // 엔티티 이동 모드: 5스텝씩
  time_step: 10    // 시간 스텝 모드: 10초씩
}

async function runBatchSteps() {
  const batchSize = executionMode.value === 'time_step' 
    ? BATCH_SIZE.time_step 
    : BATCH_SIZE.default
    
  const result = await SimulationApi.batchStepSimulation(batchSize)
  
  // 중간 상태들을 순차적으로 렌더링
  for (const stepResult of result.steps) {
    updateSimulationState(stepResult)
    await nextFrame() // requestAnimationFrame 대기
  }
}
```

#### 기대 효과
- HTTP 요청 감소: 72번 → 8번 (90% 감소)
- 예상 성능 향상: 3-5배

### 1.2 WebSocket 실시간 통신 (중기 - 2-3주)

#### 구현 계획

##### 백엔드 WebSocket 서버
```python
# backend/app/websocket.py
from fastapi import WebSocket
from typing import Dict, Set
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.simulation_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_state(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

@app.websocket("/ws/simulation")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "start_simulation":
                # 시뮬레이션을 백그라운드 태스크로 실행
                task = asyncio.create_task(
                    run_simulation_stream(websocket, data["config"])
                )
                manager.simulation_tasks[websocket] = task
                
            elif data["type"] == "stop_simulation":
                if websocket in manager.simulation_tasks:
                    manager.simulation_tasks[websocket].cancel()
                    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
```

##### 프론트엔드 WebSocket 클라이언트
```javascript
// frontend/src/services/SimulationWebSocket.js
class SimulationWebSocket {
  constructor() {
    this.ws = null
    this.listeners = new Map()
  }
  
  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws/simulation')
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.emit('state_update', data)
    }
  }
  
  startSimulation(config) {
    this.ws.send(JSON.stringify({
      type: 'start_simulation',
      config
    }))
  }
  
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }
  
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => cb(data))
    }
  }
}
```

#### 기대 효과
- 실시간 양방향 통신
- HTTP 오버헤드 완전 제거
- 스트리밍 방식으로 지연 없는 업데이트

### 1.3 데이터 압축 및 차분 전송 (선택사항)

#### 구현 계획
- 전체 상태 대신 변경된 부분만 전송
- MessagePack 등 바이너리 직렬화 사용

```python
# backend/app/models.py
class StateDelta(BaseModel):
    """상태 변경 사항만 포함"""
    time: float
    entities_moved: List[EntityMovement]
    signals_changed: Dict[str, Any]
    blocks_updated: List[BlockUpdate]
```

## 2. 프론트엔드 렌더링 최적화

### 2.1 Canvas 부분 업데이트 (단기 - 1주일)

#### 현재 문제점
- 매 프레임마다 전체 Canvas 다시 그리기
- 변경되지 않은 블록도 매번 렌더링

#### 구현 계획

##### 더티 플래그 시스템
```javascript
// frontend/src/composables/useCanvas.js
const dirtyRegions = ref(new Set())

function markDirty(blockId) {
  dirtyRegions.value.add(blockId)
}

function renderCanvas() {
  if (dirtyRegions.value.size === 0) return
  
  const ctx = canvas.value.getContext('2d')
  
  // 변경된 영역만 지우고 다시 그리기
  dirtyRegions.value.forEach(blockId => {
    const block = blocks.value.find(b => b.id === blockId)
    if (block) {
      // 해당 블록 영역만 clear
      ctx.clearRect(block.x - 10, block.y - 10, 
                    block.width + 20, block.height + 20)
      
      // 해당 블록만 다시 그리기
      drawBlock(ctx, block)
    }
  })
  
  dirtyRegions.value.clear()
}
```

##### 레이어 분리
```javascript
// 정적 레이어 (블록, 연결선)
const staticCanvas = ref(null)
// 동적 레이어 (엔티티, 애니메이션)
const dynamicCanvas = ref(null)

function initializeLayers() {
  // 정적 요소는 한 번만 그리기
  drawStaticElements(staticCanvas.value.getContext('2d'))
  
  // 동적 요소만 업데이트
  requestAnimationFrame(updateDynamicLayer)
}
```

### 2.2 Virtual DOM 방식 도입 (중기 - 2주)

#### 구현 계획
```javascript
// frontend/src/composables/useVirtualCanvas.js
class VirtualCanvas {
  constructor() {
    this.virtualDOM = {
      blocks: new Map(),
      entities: new Map(),
      connections: new Map()
    }
    this.previousDOM = null
  }
  
  update(newState) {
    const diff = this.computeDiff(this.virtualDOM, newState)
    this.applyDiff(diff)
    this.previousDOM = this.virtualDOM
    this.virtualDOM = newState
  }
  
  computeDiff(oldDOM, newDOM) {
    const diff = {
      added: [],
      removed: [],
      updated: []
    }
    
    // 효율적인 차분 계산
    newDOM.entities.forEach((entity, id) => {
      const oldEntity = oldDOM.entities.get(id)
      if (!oldEntity) {
        diff.added.push({ type: 'entity', data: entity })
      } else if (!this.isEqual(oldEntity, entity)) {
        diff.updated.push({ type: 'entity', data: entity })
      }
    })
    
    return diff
  }
  
  applyDiff(diff) {
    const ctx = canvas.value.getContext('2d')
    
    diff.removed.forEach(item => this.removeFromCanvas(ctx, item))
    diff.updated.forEach(item => this.updateOnCanvas(ctx, item))
    diff.added.forEach(item => this.addToCanvas(ctx, item))
  }
}
```

### 2.3 RequestAnimationFrame 최적화 (단기 - 3일)

#### 현재 문제점
- 불규칙한 프레임 업데이트
- 불필요한 렌더링 호출

#### 구현 계획
```javascript
// frontend/src/composables/useAnimationFrame.js
class AnimationFrameScheduler {
  constructor() {
    this.tasks = new Map()
    this.frameId = null
    this.lastTime = 0
    this.targetFPS = 60
    this.frameInterval = 1000 / this.targetFPS
  }
  
  schedule(id, task, priority = 0) {
    this.tasks.set(id, { task, priority })
    if (!this.frameId) {
      this.start()
    }
  }
  
  start() {
    const animate = (currentTime) => {
      const deltaTime = currentTime - this.lastTime
      
      if (deltaTime >= this.frameInterval) {
        // 우선순위에 따라 태스크 실행
        const sortedTasks = Array.from(this.tasks.values())
          .sort((a, b) => b.priority - a.priority)
        
        sortedTasks.forEach(({ task }) => task(deltaTime))
        
        this.lastTime = currentTime - (deltaTime % this.frameInterval)
      }
      
      if (this.tasks.size > 0) {
        this.frameId = requestAnimationFrame(animate)
      }
    }
    
    this.frameId = requestAnimationFrame(animate)
  }
}
```

### 2.4 엔티티 풀링 (Entity Pooling) (선택사항)

#### 구현 계획
```javascript
// frontend/src/utils/EntityPool.js
class EntityPool {
  constructor(maxSize = 100) {
    this.pool = []
    this.active = new Map()
    this.maxSize = maxSize
    
    // 미리 엔티티 객체 생성
    for (let i = 0; i < maxSize; i++) {
      this.pool.push(this.createEntity())
    }
  }
  
  acquire(id) {
    if (this.pool.length > 0) {
      const entity = this.pool.pop()
      entity.id = id
      entity.active = true
      this.active.set(id, entity)
      return entity
    }
    return null
  }
  
  release(id) {
    const entity = this.active.get(id)
    if (entity) {
      entity.active = false
      this.active.delete(id)
      this.pool.push(entity)
    }
  }
}
```

## 3. 측정 및 모니터링

### 3.1 Performance API 활용
```javascript
// frontend/src/utils/PerformanceMonitor.js
class PerformanceMonitor {
  constructor() {
    this.metrics = {
      fps: 0,
      renderTime: 0,
      networkTime: 0
    }
  }
  
  measureRender(callback) {
    const start = performance.now()
    callback()
    this.metrics.renderTime = performance.now() - start
  }
  
  async measureNetwork(asyncCallback) {
    const start = performance.now()
    const result = await asyncCallback()
    this.metrics.networkTime = performance.now() - start
    return result
  }
  
  getFPS() {
    // Chrome DevTools Performance API 활용
    if (performance.memory) {
      return {
        fps: this.metrics.fps,
        memory: performance.memory.usedJSHeapSize / 1048576 // MB
      }
    }
  }
}
```

### 3.2 개발자 도구 통합
```vue
<!-- frontend/src/components/PerformancePanel.vue -->
<template>
  <div v-if="showDevTools" class="performance-panel">
    <h3>Performance Metrics</h3>
    <div>FPS: {{ metrics.fps }}</div>
    <div>Render Time: {{ metrics.renderTime }}ms</div>
    <div>Network Time: {{ metrics.networkTime }}ms</div>
    <div>Memory: {{ metrics.memory }}MB</div>
    
    <canvas ref="fpsChart" width="200" height="50"></canvas>
  </div>
</template>
```

## 4. 구현 우선순위 및 일정

### Phase 1 (1-2주)
1. **Batch Step 실행** - 가장 빠른 성능 개선
2. **Canvas 부분 업데이트** - 렌더링 최적화
3. **RequestAnimationFrame 최적화** - 부드러운 애니메이션

### Phase 2 (3-4주)
1. **WebSocket 실시간 통신** - 근본적인 통신 개선
2. **Virtual DOM 방식** - 효율적인 렌더링

### Phase 3 (선택사항)
1. **데이터 압축 및 차분 전송**
2. **엔티티 풀링**
3. **Web Worker 활용**

## 5. 기대 효과

### 정량적 목표
- **통신 지연**: 100ms → 10ms (90% 감소)
- **렌더링 시간**: 16ms → 5ms (60% 감소)
- **전체 성능**: 5-10배 향상

### 정성적 개선
- 부드러운 애니메이션
- 즉각적인 반응성
- 대규모 시뮬레이션 가능

## 6. 위험 관리

### 백엔드 엔진 최적화의 위험성
- **현재 상태**: 이미 충분히 빠름 (0.13초/10엔티티)
- **위험 요소**: 
  - 복잡한 로직 변경으로 인한 버그 발생 가능
  - 엣지 케이스 처리 누락 위험
  - 기존 동작 변경 가능성
- **권장사항**: 백엔드 엔진은 현재 상태 유지

### 프론트엔드 최적화의 안전성
- **낮은 위험도**: UI/UX 레이어만 변경
- **점진적 적용**: 기능별로 독립적 구현 가능
- **롤백 용이**: 문제 발생 시 즉시 복구 가능

## 7. 테스트 계획

### 성능 테스트
```javascript
// frontend/tests/performance.test.js
describe('Performance Tests', () => {
  it('should handle 100 entities without frame drops', async () => {
    const monitor = new PerformanceMonitor()
    
    // 100개 엔티티 시뮬레이션
    await runSimulation({ entityCount: 100 })
    
    expect(monitor.metrics.fps).toBeGreaterThan(30)
    expect(monitor.metrics.renderTime).toBeLessThan(16)
  })
})
```

### 부하 테스트
- 동시 다발적 엔티티 이동
- 대량 데이터 전송
- 장시간 실행 안정성

## 결론

백엔드 엔진은 이미 최적화되어 있으므로, **프론트엔드 통신 및 렌더링 최적화**에 집중하는 것이 가장 효과적입니다. Batch 실행과 Canvas 부분 업데이트만으로도 상당한 성능 향상을 얻을 수 있을 것으로 예상됩니다.
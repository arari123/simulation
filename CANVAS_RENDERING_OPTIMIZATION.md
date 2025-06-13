# Canvas 렌더링 최적화 실행 계획

## 개요
현재 시뮬레이션은 매 프레임마다 전체 Canvas를 다시 그리고 있어 성능 저하가 발생합니다. 이를 부분 업데이트와 레이어 분리로 최적화합니다.

## 현황 분석

### 현재 구조
```javascript
// frontend/src/components/CanvasArea.vue
function drawCanvas() {
  const ctx = canvas.value.getContext('2d')
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height) // 전체 지우기
  
  // 모든 요소 다시 그리기
  connections.forEach(conn => drawConnection(ctx, conn))
  blocks.forEach(block => drawBlock(ctx, block))
  entities.forEach(entity => drawEntity(ctx, entity))
}
```

### 문제점
1. 매 프레임 전체 Canvas clear
2. 변경되지 않은 요소도 다시 렌더링
3. 레이어 구분 없이 모든 요소가 한 Canvas에
4. 불필요한 DOM 접근 반복

## 구현 계획

### Phase 1: 더티 플래그 시스템 (3일)

#### 1.1 더티 플래그 관리자 생성
```javascript
// frontend/src/composables/useDirtyFlag.js
import { ref, reactive } from 'vue'

export function useDirtyFlag() {
  const dirtyBlocks = ref(new Set())
  const dirtyEntities = ref(new Set())
  const dirtyConnections = ref(new Set())
  const dirtyRegions = reactive(new Map()) // blockId -> {x, y, width, height}
  
  function markBlockDirty(blockId) {
    dirtyBlocks.value.add(blockId)
    const block = blocks.value.find(b => b.id === blockId)
    if (block) {
      // 영향받는 영역 계산 (여백 포함)
      dirtyRegions.set(blockId, {
        x: block.x - 20,
        y: block.y - 20,
        width: block.width + 40,
        height: block.height + 40
      })
    }
  }
  
  function markEntityDirty(entityId) {
    dirtyEntities.value.add(entityId)
  }
  
  function isDirty(type, id) {
    switch(type) {
      case 'block': return dirtyBlocks.value.has(id)
      case 'entity': return dirtyEntities.value.has(id)
      case 'connection': return dirtyConnections.value.has(id)
      default: return false
    }
  }
  
  function clearDirtyFlags() {
    dirtyBlocks.value.clear()
    dirtyEntities.value.clear()
    dirtyConnections.value.clear()
    dirtyRegions.clear()
  }
  
  function getDirtyRegions() {
    // 겹치는 영역 병합
    const merged = []
    const regions = Array.from(dirtyRegions.values())
    
    regions.forEach(region => {
      const overlapping = merged.find(r => 
        !(region.x + region.width < r.x || 
          r.x + r.width < region.x ||
          region.y + region.height < r.y ||
          r.y + r.height < region.y)
      )
      
      if (overlapping) {
        // 병합
        overlapping.x = Math.min(overlapping.x, region.x)
        overlapping.y = Math.min(overlapping.y, region.y)
        overlapping.width = Math.max(
          overlapping.x + overlapping.width,
          region.x + region.width
        ) - overlapping.x
        overlapping.height = Math.max(
          overlapping.y + overlapping.height,
          region.y + region.height
        ) - overlapping.y
      } else {
        merged.push({...region})
      }
    })
    
    return merged
  }
  
  return {
    markBlockDirty,
    markEntityDirty,
    isDirty,
    clearDirtyFlags,
    getDirtyRegions
  }
}
```

#### 1.2 CanvasArea.vue 수정
```javascript
// frontend/src/components/CanvasArea.vue
import { useDirtyFlag } from '@/composables/useDirtyFlag'

const { 
  markBlockDirty, 
  markEntityDirty, 
  getDirtyRegions, 
  clearDirtyFlags 
} = useDirtyFlag()

// 상태 변경 감지
watch(() => simulationResult.value, (newResult) => {
  if (!newResult) return
  
  // 변경된 블록 찾기
  newResult.blocks.forEach(blockState => {
    const oldBlock = blocks.value.find(b => b.id === blockState.id)
    if (oldBlock && hasBlockChanged(oldBlock, blockState)) {
      markBlockDirty(blockState.id)
    }
  })
  
  // 변경된 엔티티 찾기
  const newEntityIds = new Set(newResult.entities.map(e => e.id))
  const oldEntityIds = new Set(entities.value.map(e => e.id))
  
  // 추가/제거된 엔티티
  newEntityIds.forEach(id => {
    if (!oldEntityIds.has(id)) markEntityDirty(id)
  })
  oldEntityIds.forEach(id => {
    if (!newEntityIds.has(id)) markEntityDirty(id)
  })
  
  // 이동한 엔티티
  newResult.entities.forEach(entity => {
    const oldEntity = entities.value.find(e => e.id === entity.id)
    if (oldEntity && (
      oldEntity.blockId !== entity.blockId ||
      oldEntity.state !== entity.state
    )) {
      markEntityDirty(entity.id)
      markBlockDirty(oldEntity.blockId)
      markBlockDirty(entity.blockId)
    }
  })
})

// 최적화된 렌더링
function renderCanvas() {
  const ctx = canvas.value.getContext('2d')
  const regions = getDirtyRegions()
  
  if (regions.length === 0) return // 변경사항 없음
  
  // 더티 영역만 다시 그리기
  regions.forEach(region => {
    // 해당 영역 클리어
    ctx.save()
    ctx.beginPath()
    ctx.rect(region.x, region.y, region.width, region.height)
    ctx.clip()
    ctx.clearRect(region.x, region.y, region.width, region.height)
    
    // 해당 영역과 겹치는 요소만 다시 그리기
    connections.value.forEach(conn => {
      if (isConnectionInRegion(conn, region)) {
        drawConnection(ctx, conn)
      }
    })
    
    blocks.value.forEach(block => {
      if (isBlockInRegion(block, region)) {
        drawBlock(ctx, block)
      }
    })
    
    entities.value.forEach(entity => {
      if (isEntityInRegion(entity, region)) {
        drawEntity(ctx, entity)
      }
    })
    
    ctx.restore()
  })
  
  clearDirtyFlags()
}
```

### Phase 2: 레이어 분리 (4일)

#### 2.1 멀티 레이어 Canvas 구조
```vue
<!-- frontend/src/components/CanvasArea.vue -->
<template>
  <div class="canvas-container">
    <!-- 배경 레이어: 그리드, 배경 이미지 -->
    <canvas 
      ref="backgroundCanvas"
      class="canvas-layer"
      :width="canvasWidth"
      :height="canvasHeight"
    />
    
    <!-- 정적 레이어: 블록, 연결선 -->
    <canvas 
      ref="staticCanvas"
      class="canvas-layer"
      :width="canvasWidth"
      :height="canvasHeight"
    />
    
    <!-- 동적 레이어: 엔티티, 애니메이션 -->
    <canvas 
      ref="dynamicCanvas"
      class="canvas-layer"
      :width="canvasWidth"
      :height="canvasHeight"
    />
    
    <!-- UI 레이어: 선택 영역, 툴팁 -->
    <canvas 
      ref="uiCanvas"
      class="canvas-layer"
      :width="canvasWidth"
      :height="canvasHeight"
    />
  </div>
</template>

<style scoped>
.canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.canvas-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.canvas-layer:last-child {
  pointer-events: auto; /* UI 레이어만 마우스 이벤트 받음 */
}
</style>
```

#### 2.2 레이어별 렌더링 관리
```javascript
// frontend/src/composables/useLayeredCanvas.js
import { ref, onMounted, onUnmounted } from 'vue'

export function useLayeredCanvas() {
  const layers = {
    background: { canvas: ref(null), ctx: null, needsRedraw: true },
    static: { canvas: ref(null), ctx: null, needsRedraw: true },
    dynamic: { canvas: ref(null), ctx: null, needsRedraw: true },
    ui: { canvas: ref(null), ctx: null, needsRedraw: true }
  }
  
  let animationFrameId = null
  const renderQueue = new Set()
  
  function initializeLayers() {
    Object.keys(layers).forEach(key => {
      if (layers[key].canvas.value) {
        layers[key].ctx = layers[key].canvas.value.getContext('2d')
        layers[key].ctx.imageSmoothingEnabled = true
      }
    })
    
    // 배경 레이어는 한 번만 그리기
    drawBackgroundLayer()
  }
  
  function drawBackgroundLayer() {
    const { ctx } = layers.background
    if (!ctx) return
    
    // 그리드 그리기
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 1
    
    for (let x = 0; x < canvasWidth.value; x += 50) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, canvasHeight.value)
      ctx.stroke()
    }
    
    for (let y = 0; y < canvasHeight.value; y += 50) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(canvasWidth.value, y)
      ctx.stroke()
    }
    
    layers.background.needsRedraw = false
  }
  
  function drawStaticLayer() {
    const { ctx } = layers.static
    if (!ctx || !layers.static.needsRedraw) return
    
    ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
    
    // 연결선 그리기
    connections.value.forEach(conn => drawConnection(ctx, conn))
    
    // 블록 그리기
    blocks.value.forEach(block => drawBlock(ctx, block))
    
    layers.static.needsRedraw = false
  }
  
  function drawDynamicLayer() {
    const { ctx } = layers.dynamic
    if (!ctx) return
    
    ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
    
    // 엔티티 그리기
    entities.value.forEach(entity => {
      drawEntity(ctx, entity)
    })
    
    // 애니메이션 효과
    animations.value.forEach(anim => {
      drawAnimation(ctx, anim)
    })
  }
  
  function drawUILayer() {
    const { ctx } = layers.ui
    if (!ctx || !layers.ui.needsRedraw) return
    
    ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
    
    // 선택 영역
    if (selection.value) {
      drawSelection(ctx, selection.value)
    }
    
    // 툴팁
    if (tooltip.value) {
      drawTooltip(ctx, tooltip.value)
    }
    
    layers.ui.needsRedraw = false
  }
  
  function markLayerDirty(layerName) {
    if (layers[layerName]) {
      layers[layerName].needsRedraw = true
      renderQueue.add(layerName)
      scheduleRender()
    }
  }
  
  function scheduleRender() {
    if (animationFrameId) return
    
    animationFrameId = requestAnimationFrame(() => {
      renderQueue.forEach(layerName => {
        switch(layerName) {
          case 'static': drawStaticLayer(); break
          case 'dynamic': drawDynamicLayer(); break
          case 'ui': drawUILayer(); break
        }
      })
      
      renderQueue.clear()
      animationFrameId = null
    })
  }
  
  // 블록 변경 시 정적 레이어 업데이트
  watch(() => blocks.value, () => {
    markLayerDirty('static')
  }, { deep: true })
  
  // 엔티티 변경 시 동적 레이어 업데이트
  watch(() => entities.value, () => {
    markLayerDirty('dynamic')
  }, { deep: true })
  
  return {
    layers,
    initializeLayers,
    markLayerDirty
  }
}
```

### Phase 3: 오프스크린 Canvas와 캐싱 (3일)

#### 3.1 블록별 오프스크린 Canvas
```javascript
// frontend/src/utils/CanvasCache.js
class CanvasCache {
  constructor() {
    this.cache = new Map()
    this.maxCacheSize = 100
  }
  
  generateKey(type, id, state) {
    return `${type}-${id}-${JSON.stringify(state)}`
  }
  
  getOrCreate(key, width, height, drawFunction) {
    if (this.cache.has(key)) {
      return this.cache.get(key)
    }
    
    // 캐시 크기 제한
    if (this.cache.size >= this.maxCacheSize) {
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }
    
    // 오프스크린 Canvas 생성
    const offscreenCanvas = document.createElement('canvas')
    offscreenCanvas.width = width
    offscreenCanvas.height = height
    const ctx = offscreenCanvas.getContext('2d')
    
    // 그리기
    drawFunction(ctx)
    
    // 캐시 저장
    this.cache.set(key, offscreenCanvas)
    return offscreenCanvas
  }
  
  invalidate(pattern) {
    // 패턴에 맞는 캐시 삭제
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key)
      }
    }
  }
  
  clear() {
    this.cache.clear()
  }
}

// 사용 예시
const canvasCache = new CanvasCache()

function drawBlock(ctx, block) {
  const cacheKey = canvasCache.generateKey('block', block.id, {
    name: block.name,
    color: block.backgroundColor,
    status: block.status
  })
  
  const cachedCanvas = canvasCache.getOrCreate(
    cacheKey,
    block.width + 20,
    block.height + 20,
    (cacheCtx) => {
      // 실제 블록 그리기 (한 번만 실행됨)
      drawBlockContent(cacheCtx, block)
    }
  )
  
  // 캐시된 이미지 그리기
  ctx.drawImage(
    cachedCanvas,
    block.x - 10,
    block.y - 10
  )
}
```

### Phase 4: Web Worker 렌더링 (선택사항, 5일)

#### 4.1 OffscreenCanvas를 활용한 Worker 렌더링
```javascript
// frontend/src/workers/renderWorker.js
let offscreenCanvas = null
let ctx = null

self.onmessage = function(e) {
  const { type, data } = e.data
  
  switch(type) {
    case 'init':
      offscreenCanvas = data.canvas
      ctx = offscreenCanvas.getContext('2d')
      break
      
    case 'render':
      renderFrame(data)
      break
  }
}

function renderFrame(data) {
  const { blocks, entities, connections } = data
  
  // 백그라운드 워커에서 렌더링
  ctx.clearRect(0, 0, offscreenCanvas.width, offscreenCanvas.height)
  
  // 렌더링 작업
  connections.forEach(conn => drawConnection(ctx, conn))
  blocks.forEach(block => drawBlock(ctx, block))
  entities.forEach(entity => drawEntity(ctx, entity))
  
  // 완료 신호
  self.postMessage({ type: 'renderComplete' })
}
```

## 성능 측정 및 최적화

### 측정 도구
```javascript
// frontend/src/utils/RenderingProfiler.js
class RenderingProfiler {
  constructor() {
    this.frameCount = 0
    this.lastTime = performance.now()
    this.fps = 0
    this.frameTimes = []
    this.maxSamples = 60
  }
  
  startFrame() {
    this.frameStart = performance.now()
  }
  
  endFrame() {
    const frameTime = performance.now() - this.frameStart
    this.frameTimes.push(frameTime)
    
    if (this.frameTimes.length > this.maxSamples) {
      this.frameTimes.shift()
    }
    
    this.frameCount++
    
    const currentTime = performance.now()
    const deltaTime = currentTime - this.lastTime
    
    if (deltaTime >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / deltaTime)
      this.frameCount = 0
      this.lastTime = currentTime
    }
  }
  
  getStats() {
    const avgFrameTime = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length
    const maxFrameTime = Math.max(...this.frameTimes)
    
    return {
      fps: this.fps,
      avgFrameTime: avgFrameTime.toFixed(2),
      maxFrameTime: maxFrameTime.toFixed(2),
      droppedFrames: this.frameTimes.filter(t => t > 16.67).length
    }
  }
}
```

## 테스트 계획

### 단위 테스트
```javascript
// frontend/tests/unit/dirtyFlag.spec.js
describe('DirtyFlag System', () => {
  it('should mark blocks as dirty', () => {
    const { markBlockDirty, isDirty } = useDirtyFlag()
    
    markBlockDirty('block1')
    expect(isDirty('block', 'block1')).toBe(true)
    expect(isDirty('block', 'block2')).toBe(false)
  })
  
  it('should merge overlapping regions', () => {
    const { markBlockDirty, getDirtyRegions } = useDirtyFlag()
    
    // 겹치는 영역 추가
    markBlockDirty('block1') // x: 0, y: 0, w: 100, h: 100
    markBlockDirty('block2') // x: 50, y: 50, w: 100, h: 100
    
    const regions = getDirtyRegions()
    expect(regions).toHaveLength(1)
    expect(regions[0]).toEqual({
      x: 0, y: 0, width: 150, height: 150
    })
  })
})
```

### 성능 테스트
```javascript
// frontend/tests/performance/rendering.spec.js
describe('Rendering Performance', () => {
  it('should maintain 60 FPS with 100 entities', async () => {
    const profiler = new RenderingProfiler()
    
    // 100개 엔티티 생성
    for (let i = 0; i < 100; i++) {
      entities.value.push(createTestEntity(i))
    }
    
    // 60프레임 렌더링
    for (let frame = 0; frame < 60; frame++) {
      profiler.startFrame()
      renderCanvas()
      profiler.endFrame()
      await nextFrame()
    }
    
    const stats = profiler.getStats()
    expect(stats.avgFrameTime).toBeLessThan(16.67) // 60 FPS
    expect(stats.droppedFrames).toBeLessThan(5) // 5% 미만
  })
})
```

## 구현 일정

### Week 1
- [ ] 더티 플래그 시스템 구현
- [ ] 기본 부분 업데이트 적용
- [ ] 성능 측정 도구 구현

### Week 2  
- [ ] 멀티 레이어 Canvas 구조 구현
- [ ] 레이어별 렌더링 로직
- [ ] 레이어 동기화

### Week 3
- [ ] 오프스크린 Canvas 캐싱
- [ ] 성능 프로파일링 및 최적화
- [ ] 테스트 및 버그 수정

## 기대 효과

### 정량적 개선
- 렌더링 시간: 16ms → 5ms (70% 감소)
- FPS: 30-40 → 안정적인 60 FPS
- CPU 사용률: 40% → 15%

### 정성적 개선
- 부드러운 애니메이션
- 대규모 시뮬레이션 가능 (1000+ 엔티티)
- 사용자 상호작용 반응성 향상

## 위험 관리

### 호환성 이슈
- Safari의 OffscreenCanvas 미지원 → 폴리필 적용
- 구형 브라우저 → 기능 감지 후 폴백

### 복잡도 증가
- 레이어 동기화 문제 → 명확한 레이어 책임 분리
- 디버깅 어려움 → 레이어별 디버그 모드 제공
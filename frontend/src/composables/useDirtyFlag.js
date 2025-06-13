/**
 * Canvas 렌더링 최적화를 위한 더티 플래그 시스템
 * 변경된 영역만 다시 그리도록 관리합니다.
 */
import { ref, reactive } from 'vue'

export function useDirtyFlag() {
  const dirtyBlocks = ref(new Set())
  const dirtyEntities = ref(new Set())
  const dirtyConnections = ref(new Set())
  const dirtyRegions = reactive(new Map()) // blockId -> {x, y, width, height}
  
  /**
   * 블록을 더티로 표시
   */
  function markBlockDirty(blockId, block = null) {
    dirtyBlocks.value.add(blockId)
    
    if (block) {
      // 영향받는 영역 계산 (여백 포함)
      dirtyRegions.set(blockId, {
        x: block.x - 20,
        y: block.y - 20,
        width: block.width + 40,
        height: block.height + 60 // 상태 텍스트 공간 포함
      })
    }
  }
  
  /**
   * 엔티티를 더티로 표시
   */
  function markEntityDirty(entityId) {
    dirtyEntities.value.add(entityId)
  }
  
  /**
   * 연결선을 더티로 표시
   */
  function markConnectionDirty(connectionId) {
    dirtyConnections.value.add(connectionId)
  }
  
  /**
   * 특정 요소가 더티인지 확인
   */
  function isDirty(type, id) {
    switch(type) {
      case 'block': return dirtyBlocks.value.has(id)
      case 'entity': return dirtyEntities.value.has(id)
      case 'connection': return dirtyConnections.value.has(id)
      default: return false
    }
  }
  
  /**
   * 모든 더티 플래그 초기화
   */
  function clearDirtyFlags() {
    dirtyBlocks.value.clear()
    dirtyEntities.value.clear()
    dirtyConnections.value.clear()
    dirtyRegions.clear()
  }
  
  /**
   * 더티 영역들을 병합하여 최적화된 영역 목록 반환
   */
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
  
  /**
   * 변경사항이 있는지 확인
   */
  function hasDirtyRegions() {
    return dirtyBlocks.value.size > 0 || 
           dirtyEntities.value.size > 0 || 
           dirtyConnections.value.size > 0
  }
  
  /**
   * 블록 상태 변경 감지
   */
  function hasBlockChanged(oldBlock, newBlock) {
    // 주요 속성 변경 확인
    return oldBlock.status !== newBlock.status ||
           oldBlock.processedCount !== newBlock.processedCount ||
           oldBlock.entities?.length !== newBlock.entities?.length ||
           oldBlock.backgroundColor !== newBlock.backgroundColor ||
           oldBlock.textColor !== newBlock.textColor
  }
  
  /**
   * 엔티티 상태 변경 감지
   */
  function hasEntityChanged(oldEntity, newEntity) {
    return oldEntity.current_block_id !== newEntity.current_block_id ||
           oldEntity.state !== newEntity.state ||
           oldEntity.color !== newEntity.color ||
           JSON.stringify(oldEntity.custom_attributes) !== JSON.stringify(newEntity.custom_attributes)
  }
  
  return {
    markBlockDirty,
    markEntityDirty,
    markConnectionDirty,
    isDirty,
    clearDirtyFlags,
    getDirtyRegions,
    hasDirtyRegions,
    hasBlockChanged,
    hasEntityChanged,
    
    // 내부 상태 접근 (디버깅용)
    dirtyBlocks,
    dirtyEntities,
    dirtyConnections
  }
}
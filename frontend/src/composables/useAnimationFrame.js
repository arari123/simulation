/**
 * RequestAnimationFrame 최적화를 위한 스케줄러
 * 프레임 레이트를 제어하고 작업을 효율적으로 관리합니다.
 */
import { ref, computed, onUnmounted } from 'vue'

export function useAnimationFrame() {
  const tasks = ref(new Map())
  let frameId = null
  let lastTime = 0
  const targetFPS = 60
  const frameInterval = 1000 / targetFPS
  const isRunning = ref(false)
  
  /**
   * 작업 스케줄링
   * @param {string} id - 작업 ID
   * @param {Function} task - 실행할 작업
   * @param {number} priority - 우선순위 (높을수록 먼저 실행)
   */
  function schedule(id, task, priority = 0) {
    tasks.value.set(id, { task, priority })
    if (!isRunning.value) {
      start()
    }
  }
  
  /**
   * 작업 제거
   * @param {string} id - 작업 ID
   */
  function cancel(id) {
    tasks.value.delete(id)
    if (tasks.value.size === 0) {
      stop()
    }
  }
  
  /**
   * 모든 작업 제거
   */
  function cancelAll() {
    tasks.value.clear()
    stop()
  }
  
  /**
   * 애니메이션 루프 시작
   */
  function start() {
    if (isRunning.value) return
    
    isRunning.value = true
    const animate = (currentTime) => {
      const deltaTime = currentTime - lastTime
      
      if (deltaTime >= frameInterval) {
        // 우선순위에 따라 태스크 정렬
        const sortedTasks = Array.from(tasks.value.entries())
          .sort(([, a], [, b]) => b.priority - a.priority)
        
        // 태스크 실행
        sortedTasks.forEach(([id, { task }]) => {
          try {
            task(deltaTime)
          } catch (error) {
            console.error(`Error in animation task ${id}:`, error)
          }
        })
        
        lastTime = currentTime - (deltaTime % frameInterval)
      }
      
      if (tasks.value.size > 0 && isRunning.value) {
        frameId = requestAnimationFrame(animate)
      } else {
        isRunning.value = false
      }
    }
    
    frameId = requestAnimationFrame(animate)
  }
  
  /**
   * 애니메이션 루프 중지
   */
  function stop() {
    if (frameId) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
    isRunning.value = false
  }
  
  /**
   * 한 번만 실행할 작업 스케줄링
   * @param {Function} task - 실행할 작업
   * @returns {Promise} 작업 완료 프로미스
   */
  function scheduleOnce(task) {
    return new Promise((resolve) => {
      const id = `once-${Date.now()}-${Math.random()}`
      schedule(id, () => {
        task()
        cancel(id)
        resolve()
      }, 100) // 높은 우선순위
    })
  }
  
  /**
   * 다음 프레임까지 대기
   * @returns {Promise} 다음 프레임 프로미스
   */
  function nextFrame() {
    return new Promise((resolve) => {
      requestAnimationFrame(resolve)
    })
  }
  
  /**
   * 프레임 스킵을 위한 스로틀링
   * @param {Function} callback - 실행할 함수
   * @param {number} fps - 목표 FPS (기본값: 30)
   * @returns {Function} 스로틀된 함수
   */
  function throttle(callback, fps = 30) {
    let lastCall = 0
    const interval = 1000 / fps
    
    return (...args) => {
      const now = performance.now()
      if (now - lastCall >= interval) {
        lastCall = now
        callback(...args)
      }
    }
  }
  
  // 컴포넌트 언마운트 시 정리
  onUnmounted(() => {
    cancelAll()
  })
  
  return {
    schedule,
    cancel,
    cancelAll,
    scheduleOnce,
    nextFrame,
    throttle,
    isRunning,
    taskCount: computed(() => tasks.value.size)
  }
}

// 전역 스케줄러 인스턴스 (옵션)
let globalScheduler = null

export function getGlobalAnimationScheduler() {
  if (!globalScheduler) {
    globalScheduler = {
      tasks: new Map(),
      frameId: null,
      lastTime: 0,
      targetFPS: 60,
      frameInterval: 1000 / 60,
      isRunning: false,
      
      schedule(id, task, priority = 0) {
        this.tasks.set(id, { task, priority })
        if (!this.isRunning) {
          this.start()
        }
      },
      
      cancel(id) {
        this.tasks.delete(id)
        if (this.tasks.size === 0) {
          this.stop()
        }
      },
      
      start() {
        if (this.isRunning) return
        
        this.isRunning = true
        const animate = (currentTime) => {
          const deltaTime = currentTime - this.lastTime
          
          if (deltaTime >= this.frameInterval) {
            const sortedTasks = Array.from(this.tasks.entries())
              .sort(([, a], [, b]) => b.priority - a.priority)
            
            sortedTasks.forEach(([id, { task }]) => {
              try {
                task(deltaTime)
              } catch (error) {
                console.error(`Error in animation task ${id}:`, error)
              }
            })
            
            this.lastTime = currentTime - (deltaTime % this.frameInterval)
          }
          
          if (this.tasks.size > 0 && this.isRunning) {
            this.frameId = requestAnimationFrame(animate)
          } else {
            this.isRunning = false
          }
        }
        
        this.frameId = requestAnimationFrame(animate)
      },
      
      stop() {
        if (this.frameId) {
          cancelAnimationFrame(this.frameId)
          this.frameId = null
        }
        this.isRunning = false
      }
    }
  }
  
  return globalScheduler
}
/**
 * 프론트엔드 성능 모니터링 Composable
 * API 호출, 렌더링, 사용자 상호작용의 성능을 측정합니다.
 */

import { ref, reactive } from 'vue'

export function usePerformanceMonitor() {
  // 성능 데이터 저장소
  const performanceData = reactive({
    apiCalls: [],
    renderTimes: [],
    userInteractions: [],
    memoryUsage: [],
    summary: {
      totalApiCalls: 0,
      avgApiTime: 0,
      slowestApi: null,
      totalRenders: 0,
      avgRenderTime: 0,
      totalInteractions: 0,
      avgInteractionTime: 0
    }
  })

  // 모니터링 상태
  const isMonitoring = ref(false)
  const monitoringStartTime = ref(null)

  /**
   * 성능 모니터링 시작
   */
  function startMonitoring() {
    console.log('🚀 [Performance] 성능 모니터링 시작')
    isMonitoring.value = true
    monitoringStartTime.value = performance.now()
    
    // 기존 데이터 초기화
    performanceData.apiCalls.length = 0
    performanceData.renderTimes.length = 0
    performanceData.userInteractions.length = 0
    performanceData.memoryUsage.length = 0
    
    // 메모리 사용량 주기적 측정 (브라우저에서 가능한 경우)
    if (performance.memory) {
      const memoryInterval = setInterval(() => {
        if (!isMonitoring.value) {
          clearInterval(memoryInterval)
          return
        }
        
        recordMemoryUsage()
      }, 1000) // 1초마다 측정
    }
  }

  /**
   * 성능 모니터링 중단
   */
  function stopMonitoring() {
    console.log('🛑 [Performance] 성능 모니터링 중단')
    isMonitoring.value = false
    updateSummary()
    
    const monitoringDuration = performance.now() - monitoringStartTime.value
    console.log(`📊 [Performance] 모니터링 기간: ${monitoringDuration.toFixed(2)}ms`)
    
    return getSummaryReport()
  }

  /**
   * API 호출 성능 측정 (최적화된 버전)
   */
  function measureApiCall(apiName, apiFunction, ...args) {
    // 모니터링이 비활성화된 경우 직접 실행
    if (!isMonitoring.value) {
      return apiFunction(...args)
    }

    return new Promise(async (resolve, reject) => {
      const startTime = performance.now()
      const startMemory = performance.memory ? performance.memory.usedJSHeapSize : 0
      
      try {
        // 로깅 최소화
        if (console.debug) console.debug(`🌐 [Performance] API 호출: ${apiName}`)
        
        const result = await apiFunction(...args)
        
        const endTime = performance.now()
        const endMemory = performance.memory ? performance.memory.usedJSHeapSize : 0
        const duration = endTime - startTime
        const memoryDiff = endMemory - startMemory
        
        // API 호출 데이터 기록 (간소화)
        const apiCallData = {
          name: apiName,
          duration: duration,
          success: true,
          timestamp: Date.now() // ISO 문자열 대신 숫자 사용
        }
        
        performanceData.apiCalls.push(apiCallData)
        
        // 50개 이상 누적되면 오래된 것부터 제거 (메모리 절약)
        if (performanceData.apiCalls.length > 50) {
          performanceData.apiCalls.shift()
        }
        
        resolve(result)
      } catch (error) {
        const endTime = performance.now()
        const duration = endTime - startTime
        
        // 실패한 API 호출도 기록 (간소화)
        const apiCallData = {
          name: apiName,
          duration: duration,
          success: false,
          timestamp: Date.now()
        }
        
        performanceData.apiCalls.push(apiCallData)
        
        // 50개 이상 누적되면 오래된 것부터 제거
        if (performanceData.apiCalls.length > 50) {
          performanceData.apiCalls.shift()
        }
        
        console.error(`❌ [Performance] API 호출 실패: ${apiName} (${duration.toFixed(2)}ms)`, error)
        
        reject(error)
      }
    })
  }

  /**
   * 렌더링 성능 측정
   */
  function measureRender(componentName, renderFunction) {
    const startTime = performance.now()
    
    try {
      const result = renderFunction()
      
      const endTime = performance.now()
      const duration = endTime - startTime
      
      const renderData = {
        component: componentName,
        startTime: startTime,
        endTime: endTime,
        duration: duration,
        timestamp: new Date().toISOString()
      }
      
      if (isMonitoring.value) {
        performanceData.renderTimes.push(renderData)
      }
      
      if (duration > 16.67) { // 60fps 기준 (16.67ms)
        console.warn(`⚠️ [Performance] 느린 렌더링: ${componentName} (${duration.toFixed(2)}ms)`)
      }
      
      return result
    } catch (error) {
      console.error(`❌ [Performance] 렌더링 오류: ${componentName}`, error)
      throw error
    }
  }

  /**
   * 사용자 상호작용 성능 측정
   */
  function measureUserInteraction(interactionName, interactionFunction, ...args) {
    return new Promise(async (resolve, reject) => {
      const startTime = performance.now()
      
      try {
        console.log(`👆 [Performance] 사용자 상호작용 시작: ${interactionName}`)
        
        const result = await interactionFunction(...args)
        
        const endTime = performance.now()
        const duration = endTime - startTime
        
        const interactionData = {
          name: interactionName,
          startTime: startTime,
          endTime: endTime,
          duration: duration,
          timestamp: new Date().toISOString(),
          success: true
        }
        
        if (isMonitoring.value) {
          performanceData.userInteractions.push(interactionData)
        }
        
        if (duration > 100) { // 100ms 이상이면 느린 상호작용
          console.warn(`⚠️ [Performance] 느린 상호작용: ${interactionName} (${duration.toFixed(2)}ms)`)
        } else {
          console.log(`✅ [Performance] 상호작용 완료: ${interactionName} (${duration.toFixed(2)}ms)`)
        }
        
        resolve(result)
      } catch (error) {
        const endTime = performance.now()
        const duration = endTime - startTime
        
        const interactionData = {
          name: interactionName,
          startTime: startTime,
          endTime: endTime,
          duration: duration,
          timestamp: new Date().toISOString(),
          success: false,
          error: error.message
        }
        
        if (isMonitoring.value) {
          performanceData.userInteractions.push(interactionData)
        }
        
        console.error(`❌ [Performance] 상호작용 실패: ${interactionName} (${duration.toFixed(2)}ms)`, error)
        
        reject(error)
      }
    })
  }

  /**
   * 메모리 사용량 기록
   */
  function recordMemoryUsage() {
    if (!performance.memory || !isMonitoring.value) return
    
    const memoryData = {
      used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024), // MB
      total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024), // MB
      limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024), // MB
      timestamp: new Date().toISOString()
    }
    
    performanceData.memoryUsage.push(memoryData)
    
    // 메모리 사용량이 높으면 경고
    const memoryUsagePercent = (memoryData.used / memoryData.limit) * 100
    if (memoryUsagePercent > 80) {
      console.warn(`⚠️ [Performance] 높은 메모리 사용량: ${memoryData.used}MB (${memoryUsagePercent.toFixed(1)}%)`)
    }
  }

  /**
   * 성능 요약 업데이트
   */
  function updateSummary() {
    const apiCalls = performanceData.apiCalls
    const renderTimes = performanceData.renderTimes
    const userInteractions = performanceData.userInteractions
    
    // API 호출 요약
    if (apiCalls.length > 0) {
      const successfulCalls = apiCalls.filter(call => call.success)
      const totalApiTime = successfulCalls.reduce((sum, call) => sum + call.duration, 0)
      
      performanceData.summary.totalApiCalls = apiCalls.length
      performanceData.summary.avgApiTime = totalApiTime / successfulCalls.length
      performanceData.summary.slowestApi = successfulCalls.reduce((slowest, current) => 
        current.duration > (slowest?.duration || 0) ? current : slowest, null)
    }
    
    // 렌더링 요약
    if (renderTimes.length > 0) {
      const totalRenderTime = renderTimes.reduce((sum, render) => sum + render.duration, 0)
      
      performanceData.summary.totalRenders = renderTimes.length
      performanceData.summary.avgRenderTime = totalRenderTime / renderTimes.length
    }
    
    // 사용자 상호작용 요약
    if (userInteractions.length > 0) {
      const successfulInteractions = userInteractions.filter(interaction => interaction.success)
      const totalInteractionTime = successfulInteractions.reduce((sum, interaction) => sum + interaction.duration, 0)
      
      performanceData.summary.totalInteractions = userInteractions.length
      performanceData.summary.avgInteractionTime = totalInteractionTime / successfulInteractions.length
    }
  }

  /**
   * 성능 보고서 생성
   */
  function getSummaryReport() {
    updateSummary()
    
    const report = {
      monitoringDuration: performance.now() - monitoringStartTime.value,
      apiPerformance: {
        totalCalls: performanceData.summary.totalApiCalls,
        avgTime: performanceData.summary.avgApiTime,
        slowestCall: performanceData.summary.slowestApi,
        callsPerSecond: performanceData.summary.totalApiCalls / ((performance.now() - monitoringStartTime.value) / 1000)
      },
      renderPerformance: {
        totalRenders: performanceData.summary.totalRenders,
        avgTime: performanceData.summary.avgRenderTime,
        fps: 1000 / performanceData.summary.avgRenderTime // 추정 FPS
      },
      interactionPerformance: {
        totalInteractions: performanceData.summary.totalInteractions,
        avgTime: performanceData.summary.avgInteractionTime
      },
      memoryUsage: {
        samples: performanceData.memoryUsage.length,
        peak: performanceData.memoryUsage.length > 0 ? Math.max(...performanceData.memoryUsage.map(m => m.used)) : 0,
        current: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) : 0
      }
    }
    
    console.log('📊 [Performance] 성능 보고서:', report)
    
    return report
  }

  /**
   * 상세 성능 로그 출력
   */
  function printDetailedReport() {
    console.group('📊 [Performance] 상세 성능 보고서')
    
    console.group('🌐 API 호출')
    performanceData.apiCalls.forEach((call, index) => {
      const status = call.success ? '✅' : '❌'
      console.log(`${status} ${index + 1}. ${call.name}: ${call.duration.toFixed(2)}ms`)
    })
    console.groupEnd()
    
    console.group('🎨 렌더링')
    performanceData.renderTimes.forEach((render, index) => {
      const status = render.duration > 16.67 ? '⚠️' : '✅'
      console.log(`${status} ${index + 1}. ${render.component}: ${render.duration.toFixed(2)}ms`)
    })
    console.groupEnd()
    
    console.group('👆 사용자 상호작용')
    performanceData.userInteractions.forEach((interaction, index) => {
      const status = interaction.success ? (interaction.duration > 100 ? '⚠️' : '✅') : '❌'
      console.log(`${status} ${index + 1}. ${interaction.name}: ${interaction.duration.toFixed(2)}ms`)
    })
    console.groupEnd()
    
    if (performanceData.memoryUsage.length > 0) {
      console.group('💾 메모리 사용량')
      const latestMemory = performanceData.memoryUsage[performanceData.memoryUsage.length - 1]
      const peakMemory = Math.max(...performanceData.memoryUsage.map(m => m.used))
      console.log(`현재: ${latestMemory.used}MB`)
      console.log(`최대: ${peakMemory}MB`)
      console.log(`샘플 수: ${performanceData.memoryUsage.length}`)
      console.groupEnd()
    }
    
    console.groupEnd()
  }

  /**
   * 성능 데이터 내보내기 (JSON)
   */
  function exportPerformanceData() {
    const exportData = {
      timestamp: new Date().toISOString(),
      monitoringDuration: performance.now() - monitoringStartTime.value,
      browserInfo: {
        userAgent: navigator.userAgent,
        vendor: navigator.vendor,
        platform: navigator.platform
      },
      performanceData: {
        apiCalls: performanceData.apiCalls,
        renderTimes: performanceData.renderTimes,
        userInteractions: performanceData.userInteractions,
        memoryUsage: performanceData.memoryUsage,
        summary: performanceData.summary
      }
    }
    
    const dataStr = JSON.stringify(exportData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `performance-report-${new Date().toISOString().replace(/[:.]/g, '-')}.json`
    link.click()
    
    URL.revokeObjectURL(url)
    
    console.log('📁 [Performance] 성능 데이터 내보내기 완료')
  }

  return {
    // 상태
    performanceData,
    isMonitoring,
    
    // 메서드
    startMonitoring,
    stopMonitoring,
    measureApiCall,
    measureRender,
    measureUserInteraction,
    recordMemoryUsage,
    getSummaryReport,
    printDetailedReport,
    exportPerformanceData
  }
}
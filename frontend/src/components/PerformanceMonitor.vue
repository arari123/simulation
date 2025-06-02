<template>
  <div class="performance-monitor">
    <!-- 성능 모니터링 토글 버튼 -->
    <div class="monitor-controls">
      <button 
        @click="toggleMonitoring"
        :class="['monitor-btn', { active: performanceMonitor.isMonitoring.value }]"
      >
        {{ performanceMonitor.isMonitoring.value ? '⏹️ 모니터링 중단' : '▶️ 성능 모니터링 시작' }}
      </button>
      
      <button 
        v-if="!performanceMonitor.isMonitoring.value && hasData"
        @click="showDetailedReport"
        class="report-btn"
      >
        📊 상세 보고서
      </button>
      
      <button 
        v-if="!performanceMonitor.isMonitoring.value && hasData"
        @click="exportData"
        class="export-btn"
      >
        📁 데이터 내보내기
      </button>
    </div>

    <!-- 실시간 성능 표시 -->
    <div v-if="performanceMonitor.isMonitoring.value" class="real-time-stats">
      <div class="stat-item">
        <span class="label">API 호출:</span>
        <span class="value">{{ performanceData.apiCalls.length }}회</span>
      </div>
      <div class="stat-item">
        <span class="label">평균 API 시간:</span>
        <span class="value">{{ avgApiTime }}ms</span>
      </div>
      <div class="stat-item">
        <span class="label">렌더링:</span>
        <span class="value">{{ performanceData.renderTimes.length }}회</span>
      </div>
      <div class="stat-item">
        <span class="label">메모리:</span>
        <span class="value">{{ currentMemory }}MB</span>
      </div>
    </div>

    <!-- 성능 요약 (모니터링 중단 후) -->
    <div v-if="!performanceMonitor.isMonitoring.value && hasData" class="performance-summary">
      <h3>📊 성능 요약</h3>
      
      <div class="summary-grid">
        <div class="summary-card">
          <h4>🌐 API 성능</h4>
          <div class="metric">
            <span class="metric-label">총 호출:</span>
            <span class="metric-value">{{ performanceData.summary.totalApiCalls }}회</span>
          </div>
          <div class="metric">
            <span class="metric-label">평균 시간:</span>
            <span class="metric-value">{{ performanceData.summary.avgApiTime?.toFixed(2) }}ms</span>
          </div>
          <div class="metric" v-if="performanceData.summary.slowestApi">
            <span class="metric-label">가장 느린 호출:</span>
            <span class="metric-value">{{ performanceData.summary.slowestApi.name }} ({{ performanceData.summary.slowestApi.duration?.toFixed(2) }}ms)</span>
          </div>
        </div>

        <div class="summary-card">
          <h4>🎨 렌더링 성능</h4>
          <div class="metric">
            <span class="metric-label">총 렌더링:</span>
            <span class="metric-value">{{ performanceData.summary.totalRenders }}회</span>
          </div>
          <div class="metric">
            <span class="metric-label">평균 시간:</span>
            <span class="metric-value">{{ performanceData.summary.avgRenderTime?.toFixed(2) }}ms</span>
          </div>
          <div class="metric">
            <span class="metric-label">예상 FPS:</span>
            <span class="metric-value">{{ estimatedFPS }}</span>
          </div>
        </div>

        <div class="summary-card">
          <h4>👆 사용자 상호작용</h4>
          <div class="metric">
            <span class="metric-label">총 상호작용:</span>
            <span class="metric-value">{{ performanceData.summary.totalInteractions }}회</span>
          </div>
          <div class="metric">
            <span class="metric-label">평균 시간:</span>
            <span class="metric-value">{{ performanceData.summary.avgInteractionTime?.toFixed(2) }}ms</span>
          </div>
        </div>

        <div class="summary-card" v-if="hasMemoryData">
          <h4>💾 메모리 사용량</h4>
          <div class="metric">
            <span class="metric-label">현재:</span>
            <span class="metric-value">{{ currentMemory }}MB</span>
          </div>
          <div class="metric">
            <span class="metric-label">최대:</span>
            <span class="metric-value">{{ peakMemory }}MB</span>
          </div>
          <div class="metric">
            <span class="metric-label">샘플:</span>
            <span class="metric-value">{{ performanceData.memoryUsage.length }}개</span>
          </div>
        </div>
      </div>

      <!-- 성능 경고 -->
      <div v-if="performanceWarnings.length > 0" class="performance-warnings">
        <h4>⚠️ 성능 경고</h4>
        <ul>
          <li v-for="warning in performanceWarnings" :key="warning" class="warning-item">
            {{ warning }}
          </li>
        </ul>
      </div>

      <!-- 개선 제안 -->
      <div v-if="performanceRecommendations.length > 0" class="performance-recommendations">
        <h4>💡 개선 제안</h4>
        <ul>
          <li v-for="rec in performanceRecommendations" :key="rec" class="recommendation-item">
            {{ rec }}
          </li>
        </ul>
      </div>
    </div>

    <!-- 상세 보고서 모달 -->
    <div v-if="showReport" class="report-modal" @click="closeReport">
      <div class="report-content" @click.stop>
        <div class="report-header">
          <h3>📊 상세 성능 보고서</h3>
          <button @click="closeReport" class="close-btn">✕</button>
        </div>
        
        <div class="report-body">
          <div class="report-section">
            <h4>🌐 API 호출 상세</h4>
            <div class="api-calls-list">
              <div v-for="(call, index) in performanceData.apiCalls" :key="index" 
                   class="api-call-item">
                <span class="call-index">{{ index + 1 }}.</span>
                <span class="call-name">{{ call.name }}</span>
                <span class="call-duration">{{ call.duration?.toFixed(2) }}ms</span>
                <span :class="['call-status', call.success ? 'success' : 'error']">
                  {{ call.success ? '✅' : '❌' }}
                </span>
              </div>
            </div>
          </div>

          <div class="report-section">
            <h4>🎨 렌더링 상세</h4>
            <div class="render-list">
              <div v-for="(render, index) in performanceData.renderTimes" :key="index" 
                   class="render-item">
                <span class="render-index">{{ index + 1 }}.</span>
                <span class="render-component">{{ render.component }}</span>
                <span class="render-duration">{{ render.duration?.toFixed(2) }}ms</span>
                <span :class="['render-status', render.duration > 16.67 ? 'slow' : 'good']">
                  {{ render.duration > 16.67 ? '⚠️' : '✅' }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="hasMemoryData" class="report-section">
            <h4>💾 메모리 사용량 추이</h4>
            <div class="memory-chart">
              <div v-for="(memory, index) in recentMemoryData" :key="index" 
                   class="memory-point">
                <span class="memory-time">{{ formatTime(memory.timestamp) }}</span>
                <span class="memory-value">{{ memory.used }}MB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'
import { usePerformanceMonitor } from '../composables/usePerformanceMonitor.js'

export default {
  name: 'PerformanceMonitor',
  setup() {
    const performanceMonitor = usePerformanceMonitor()
    const showReport = ref(false)

    // 성능 데이터 접근
    const performanceData = performanceMonitor.performanceData

    // 계산된 속성들
    const hasData = computed(() => {
      return performanceData.apiCalls.length > 0 || 
             performanceData.renderTimes.length > 0 || 
             performanceData.userInteractions.length > 0
    })

    const avgApiTime = computed(() => {
      if (performanceData.apiCalls.length === 0) return '0.00'
      const total = performanceData.apiCalls.reduce((sum, call) => sum + (call.duration || 0), 0)
      return (total / performanceData.apiCalls.length).toFixed(2)
    })

    const currentMemory = computed(() => {
      if (performance.memory) {
        return Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)
      }
      return 'N/A'
    })

    const hasMemoryData = computed(() => {
      return performanceData.memoryUsage.length > 0
    })

    const peakMemory = computed(() => {
      if (performanceData.memoryUsage.length === 0) return 0
      return Math.max(...performanceData.memoryUsage.map(m => m.used))
    })

    const estimatedFPS = computed(() => {
      if (performanceData.summary.avgRenderTime > 0) {
        const fps = 1000 / performanceData.summary.avgRenderTime
        return fps.toFixed(1)
      }
      return 'N/A'
    })

    const recentMemoryData = computed(() => {
      return performanceData.memoryUsage.slice(-10) // 최근 10개만 표시
    })

    // 성능 경고 분석
    const performanceWarnings = computed(() => {
      const warnings = []
      
      // API 성능 경고
      if (performanceData.summary.avgApiTime > 100) {
        warnings.push(`평균 API 응답 시간이 느림 (${performanceData.summary.avgApiTime?.toFixed(0)}ms)`)
      }
      
      // 렌더링 성능 경고
      if (performanceData.summary.avgRenderTime > 16.67) {
        warnings.push(`평균 렌더링 시간이 60fps 기준 초과 (${performanceData.summary.avgRenderTime?.toFixed(2)}ms)`)
      }
      
      // 메모리 사용량 경고
      if (performance.memory) {
        const memoryUsagePercent = (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
        if (memoryUsagePercent > 80) {
          warnings.push(`높은 메모리 사용량 (${memoryUsagePercent.toFixed(1)}%)`)
        }
      }
      
      // 느린 API 호출 경고
      const slowApiCalls = performanceData.apiCalls.filter(call => call.duration > 200)
      if (slowApiCalls.length > 0) {
        warnings.push(`${slowApiCalls.length}개의 느린 API 호출 감지 (200ms 이상)`)
      }
      
      return warnings
    })

    // 성능 개선 제안
    const performanceRecommendations = computed(() => {
      const recommendations = []
      
      if (performanceData.summary.avgApiTime > 50) {
        recommendations.push('API 응답 시간 최적화: 백엔드 캐싱 또는 데이터 압축 검토')
      }
      
      if (performanceData.summary.avgRenderTime > 10) {
        recommendations.push('렌더링 최적화: 컴포넌트 메모이제이션 또는 가상 스크롤링 검토')
      }
      
      if (performanceData.apiCalls.length > 100) {
        recommendations.push('API 호출 최적화: 배치 처리 또는 실시간 업데이트 주기 조정')
      }
      
      if (performanceData.summary.avgInteractionTime > 100) {
        recommendations.push('사용자 상호작용 최적화: 비동기 처리 또는 로딩 상태 개선')
      }
      
      return recommendations
    })

    // 메서드들
    const toggleMonitoring = () => {
      if (performanceMonitor.isMonitoring.value) {
        performanceMonitor.stopMonitoring()
      } else {
        performanceMonitor.startMonitoring()
      }
    }

    const showDetailedReport = () => {
      showReport.value = true
      performanceMonitor.printDetailedReport()
    }

    const closeReport = () => {
      showReport.value = false
    }

    const exportData = () => {
      performanceMonitor.exportPerformanceData()
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString()
    }

    return {
      performanceMonitor,
      performanceData,
      showReport,
      hasData,
      avgApiTime,
      currentMemory,
      hasMemoryData,
      peakMemory,
      estimatedFPS,
      recentMemoryData,
      performanceWarnings,
      performanceRecommendations,
      toggleMonitoring,
      showDetailedReport,
      closeReport,
      exportData,
      formatTime
    }
  }
}
</script>

<style scoped>
.performance-monitor {
  position: fixed;
  top: 10px;
  right: 10px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  z-index: 1000;
  max-width: 400px;
  font-size: 12px;
}

.monitor-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.monitor-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

.monitor-btn.active {
  background: #dc3545;
}

.report-btn, .export-btn {
  background: #28a745;
  color: white;
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

.export-btn {
  background: #17a2b8;
}

.real-time-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.label {
  font-weight: 500;
}

.value {
  color: #007bff;
  font-weight: bold;
}

.performance-summary h3 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 14px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.summary-card {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.summary-card h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #495057;
}

.metric {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.metric-label {
  color: #6c757d;
  font-size: 11px;
}

.metric-value {
  font-weight: 500;
  font-size: 11px;
}

.performance-warnings, .performance-recommendations {
  margin-bottom: 10px;
}

.performance-warnings h4, .performance-recommendations h4 {
  margin: 0 0 6px 0;
  font-size: 12px;
}

.warning-item {
  color: #dc3545;
  font-size: 11px;
  margin-bottom: 2px;
}

.recommendation-item {
  color: #28a745;
  font-size: 11px;
  margin-bottom: 2px;
}

/* 모달 스타일 */
.report-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.report-content {
  background: white;
  width: 80%;
  max-width: 800px;
  max-height: 80%;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ddd;
  background: #f8f9fa;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #666;
}

.report-body {
  padding: 16px;
  overflow-y: auto;
}

.report-section {
  margin-bottom: 20px;
}

.report-section h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.api-calls-list, .render-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.api-call-item, .render-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  gap: 10px;
}

.api-call-item:last-child, .render-item:last-child {
  border-bottom: none;
}

.call-index, .render-index {
  min-width: 30px;
  color: #666;
}

.call-name, .render-component {
  flex: 1;
  font-family: monospace;
  font-size: 11px;
}

.call-duration, .render-duration {
  min-width: 60px;
  text-align: right;
  font-weight: 500;
}

.call-status.success, .render-status.good {
  color: #28a745;
}

.call-status.error, .render-status.slow {
  color: #dc3545;
}

.memory-chart {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.memory-point {
  display: flex;
  justify-content: space-between;
  padding: 6px 12px;
  border-bottom: 1px solid #eee;
}

.memory-point:last-child {
  border-bottom: none;
}

.memory-time {
  color: #666;
  font-size: 11px;
}

.memory-value {
  font-weight: 500;
}
</style>
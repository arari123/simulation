import { ref, computed } from 'vue'

export function useSimulationLogs() {
  // 로그 저장소
  const logs = ref([])
  const maxLogs = 1000 // 최대 로그 수 제한
  const isAutoScrollEnabled = ref(true) // 자동 스크롤 활성화 여부

  // 로그 추가
  function addLogs(newLogs) {
    if (!newLogs || !Array.isArray(newLogs)) return
    
    logs.value.push(...newLogs)
    
    // 최대 로그 수 제한
    if (logs.value.length > maxLogs) {
      logs.value = logs.value.slice(-maxLogs)
    }
  }

  // 로그 초기화
  function clearLogs() {
    logs.value = []
  }

  // 로그 내보내기
  function exportLogs(format = 'txt') {
    if (logs.value.length === 0) {
      alert('내보낼 로그가 없습니다.')
      return
    }

    let content = ''
    let filename = `simulation-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}`
    let mimeType = 'text/plain'

    switch (format) {
      case 'txt':
        content = logs.value
          .map(log => `[${log.time.toFixed(1)}s] [${log.block}] ${log.message}`)
          .join('\n')
        filename += '.txt'
        break
        
      case 'csv':
        content = 'Time,Block,Message\n' + 
          logs.value
            .map(log => `${log.time.toFixed(1)},"${log.block}","${log.message.replace(/"/g, '""')}"`)
            .join('\n')
        filename += '.csv'
        mimeType = 'text/csv'
        break
        
      case 'json':
        content = JSON.stringify(logs.value, null, 2)
        filename += '.json'
        mimeType = 'application/json'
        break
    }

    // 파일 다운로드
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }

  // 고유 블록 목록 (필터링용)
  const uniqueBlocks = computed(() => {
    const blocks = new Set()
    logs.value.forEach(log => blocks.add(log.block))
    return Array.from(blocks).sort()
  })

  // 자동 스크롤 토글
  function toggleAutoScroll() {
    isAutoScrollEnabled.value = !isAutoScrollEnabled.value
  }

  return {
    logs,
    addLogs,
    clearLogs,
    exportLogs,
    uniqueBlocks,
    isAutoScrollEnabled,
    toggleAutoScroll
  }
}
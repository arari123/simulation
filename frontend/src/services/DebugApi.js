/**
 * 디버그 API 서비스
 * 브레이크포인트 관리 및 디버그 제어를 위한 API 호출
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class DebugApi {
  /**
   * 브레이크포인트 설정
   */
  async setBreakpoint(blockId, lineNumber) {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/breakpoints`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'set',
        block_id: blockId,
        line_number: lineNumber
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to set breakpoint: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 브레이크포인트 해제
   */
  async clearBreakpoint(blockId, lineNumber) {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/breakpoints`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'clear',
        block_id: blockId,
        line_number: lineNumber
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to clear breakpoint: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 모든 브레이크포인트 해제
   */
  async clearAllBreakpoints(blockId = null) {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/breakpoints`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'clear_all',
        block_id: blockId
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to clear all breakpoints: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 여러 브레이크포인트 일괄 설정
   */
  async setBreakpointsBatch(breakpoints) {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/set_breakpoints_batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(breakpoints)
    })

    if (!response.ok) {
      throw new Error(`Failed to set batch breakpoints: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 디버그 모드 시작
   */
  async startDebugMode() {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'start_debug'
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to start debug mode: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 디버그 모드 중지
   */
  async stopDebugMode() {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'stop_debug'
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to stop debug mode: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 실행 계속
   */
  async continueExecution() {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'continue'
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to continue execution: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 스텝 실행
   */
  async stepExecution() {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: 'step'
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to step execution: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 디버그 상태 조회
   */
  async getDebugStatus() {
    const response = await fetch(`${API_BASE_URL}/simulation/debug/status`)

    if (!response.ok) {
      throw new Error(`Failed to get debug status: ${response.statusText}`)
    }

    return await response.json()
  }
}

export default new DebugApi()
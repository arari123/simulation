/**
 * 시뮬레이션 API 서비스
 * 백엔드와의 모든 API 통신을 담당합니다.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class SimulationApi {
  /**
   * 기본 설정 로드 (base.json)
   */
  static async loadBaseConfig() {
    try {
      const response = await fetch(`${API_BASE}/simulation/load-base-config`)
      if (!response.ok) {
        throw new Error(`Failed to load base config: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 기본 설정 로드 실패:', error)
      throw error
    }
  }

  /**
   * 시뮬레이션 단일 스텝 실행
   */
  static async stepSimulation(setupData) {
    try {
      const response = await fetch(`${API_BASE}/simulation/step`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(setupData)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`시뮬레이션 스텝 실행 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 스텝 실행 실패:', error)
      throw error
    }
  }

  /**
   * 브레이크포인트 설정/해제
   */
  static async setBreakpoint(blockId, lineNumber, enabled) {
    try {
      const response = await fetch(`${API_BASE}/simulation/debug/breakpoints`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          block_id: blockId,
          line_number: lineNumber,
          enabled: enabled
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`브레이크포인트 설정 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 브레이크포인트 설정 실패:', error)
      throw error
    }
  }

  /**
   * 디버그 상태 조회
   */
  static async getDebugStatus() {
    try {
      const response = await fetch(`${API_BASE}/simulation/debug/status`)
      
      if (!response.ok) {
        throw new Error(`디버그 상태 조회 실패: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 디버그 상태 조회 실패:', error)
      throw error
    }
  }

  /**
   * 디버그 실행 계속 (Continue)
   */
  static async debugContinue() {
    try {
      const response = await fetch(`${API_BASE}/simulation/debug/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'continue'
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`디버그 계속 실행 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 디버그 계속 실행 실패:', error)
      throw error
    }
  }

  /**
   * 디버그 한 스텝 실행 (Step)
   */
  static async debugStep() {
    try {
      const response = await fetch(`${API_BASE}/simulation/debug/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'step'
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`디버그 스텝 실행 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 디버그 스텝 실행 실패:', error)
      throw error
    }
  }

  /**
   * 모든 브레이크포인트 제거
   */
  static async clearAllBreakpoints() {
    try {
      const response = await fetch(`${API_BASE}/simulation/debug/breakpoints/manage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'clear_all'
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`브레이크포인트 모두 제거 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 브레이크포인트 모두 제거 실패:', error)
      throw error
    }
  }

  /**
   * 시뮬레이션 배치 스텝 실행
   */
  static async batchStepSimulation(setupData, stepCount = 10) {
    try {
      const response = await fetch(`${API_BASE}/simulation/batch-step`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...setupData,
          step_count: stepCount
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`배치 스텝 실행 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 배치 스텝 실행 실패:', error)
      throw error
    }
  }

  /**
   * 시뮬레이션 전체 실행
   */
  static async runFullSimulation(setupData) {
    try {
      const response = await fetch(`${API_BASE}/simulation/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(setupData)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`전체 시뮬레이션 실행 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 전체 시뮬레이션 실행 실패:', error)
      throw error
    }
  }

  /**
   * 시뮬레이션 초기화
   */
  static async resetSimulation() {
    try {
      const response = await fetch(`${API_BASE}/simulation/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`시뮬레이션 초기화 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 시뮬레이션 초기화 실패:', error)
      throw error
    }
  }

  /**
   * 설정 업데이트
   */
  static async updateSettings(settings) {
    try {
      const response = await fetch(`${API_BASE}/simulation/update-settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`설정 업데이트 실패: ${response.status} - ${errorText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 설정 업데이트 실패:', error)
      throw error
    }
  }

  /**
   * 실행 모드 설정
   */
  static async setExecutionMode(mode, config = {}) {
    try {
      const response = await fetch(`${API_BASE}/simulation/execution-mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode, config })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to set execution mode`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 실행 모드 설정 실패:', error)
      throw error
    }
  }

  /**
   * 현재 실행 모드 조회
   */
  static async getExecutionMode() {
    try {
      const response = await fetch(`${API_BASE}/simulation/execution-mode`)

      if (!response.ok) {
        throw new Error(`실행 모드 조회 실패: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 실행 모드 조회 실패:', error)
      throw error
    }
  }

  /**
   * 특정 설정 파일 로드
   */
  static async loadConfigFile(filePath) {
    try {
      const response = await fetch(`${API_BASE}/simulation/load-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_path: filePath })
      })

      if (!response.ok) {
        throw new Error(`설정 파일 로드 실패: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('[SimulationApi] 설정 파일 로드 실패:', error)
      throw error
    }
  }
}

export default SimulationApi 
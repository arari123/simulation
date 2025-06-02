/**
 * 시뮬레이션 API 서비스
 * 백엔드와의 모든 API 통신을 담당합니다.
 */

const API_BASE = 'http://localhost:8000'

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
}

export default SimulationApi 
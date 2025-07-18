<template>
  <div class="script-help-overlay" @click="$emit('close')">
    <div class="script-help-popup" @click.stop>
      <div class="script-help-header">
        <h3>📖 스크립트 사용법</h3>
        <button @click="$emit('close')" class="close-btn">×</button>
      </div>
      
      <div class="script-help-content">
        <div class="help-section">
          <h4>기본 명령어</h4>
          <ul>
            <li><code>delay 5</code> - 5초 딜레이</li>
            <li><code>delay 3-10</code> - 3~10초 랜덤 딜레이</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>신호 관련</h4>
          <ul>
            <li><code>신호명 = true</code> - 신호를 true로 설정</li>
            <li><code>신호명 = false</code> - 신호를 false로 설정</li>
            <li><code>wait 신호명 = true</code> - 신호가 true가 될 때까지 대기</li>
            <li><code>wait 신호명 = false</code> - 신호가 false가 될 때까지 대기</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>이동 명령어</h4>
          <ul>
            <li><strong>새로운 형식 (권장)</strong></li>
            <li><code>go from R to 블록명.L</code> - R 커넥터에서 다른 블록의 L 커넥터로 이동</li>
            <li><code>go from L to 블록명.R,3</code> - L 커넥터에서 3초 딜레이와 함께 이동</li>
            <li><code>go from 3 to 공정2.L,2-5</code> - 커넥터 '3'에서 2~5초 랜덤 딜레이와 함께 이동</li>
            <li><strong>기존 형식 (하위 호환)</strong></li>
            <li><code>go to self.R</code> - 현재 블록의 R 커넥터로 이동</li>
            <li><code>go to 블록명.커넥터명</code> - 다른 블록의 커넥터로 이동 (블록 중앙에서 시작)</li>
            <li><code>go to 블록명.커넥터명,3</code> - 3초 딜레이와 함께 이동</li>
            <li><strong>기타</strong></li>
            <li><code>jump to 액션번호</code> - 지정된 액션으로 점프</li>
            <li><code>jump to 레이블명</code> - 지정된 레이블로 점프</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>조건부 실행</h4>
          <ul>
            <li><code>if 신호명 = true</code> - 조건부 실행 시작</li>
            <li>조건 내부의 명령어들은 들여쓰기로 구분</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>블록 상태 설정</h4>
          <ul>
            <li><code>블록이름.status = "running"</code> - 블록 상태를 "running"으로 설정</li>
            <li><code>공정1.status = "idle"</code> - 공정1 블록의 상태를 "idle"로 설정</li>
            <li><code>투입.status = "준비중"</code> - 한글 상태도 지원</li>
            <li>상태 값은 반드시 따옴표로 감싸야 함</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>정수 변수 (한글 지원)</h4>
          <ul>
            <li><code>int 카운터 = 0</code> - 정수 변수 초기화</li>
            <li><code>int 공정1처리수 += 1</code> - 한글 변수명 지원</li>
            <li><code>int 총생산량 = 카운터</code> - 변수 복사</li>
          </ul>
        </div>
        
        <div class="help-section">
          <h4>주의사항</h4>
          <ul>
            <li>각 명령어는 한 줄에 하나씩 작성</li>
            <li>신호명은 전역 신호 패널에 정의된 이름과 정확히 일치해야 함</li>
            <li>블록명과 커넥터명은 실제 존재하는 이름을 사용</li>
            <li>주석은 // 로 시작</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Emits 정의
defineEmits(['close'])
</script>

<style scoped>
.script-help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2100;
}

.script-help-popup {
  background: white;
  border-radius: 8px;
  padding: 20px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.script-help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #dc3545;
}

.script-help-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.help-section {
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
}

.help-section h4 {
  margin: 0 0 10px 0;
  color: #495057;
}

.help-section ul {
  padding-left: 20px;
}

.help-section li {
  margin-bottom: 5px;
}

code {
  background: #e9ecef;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 90%;
}
</style> 
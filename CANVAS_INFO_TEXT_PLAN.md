# 캔버스 정보 텍스트 구현 계획

## 개요
캔버스 상단에 정보 텍스트를 표시하는 기능을 구현합니다. 사용자가 시뮬레이션에 대한 설명이나 메모를 작성할 수 있습니다.

## 요구사항
1. **위치**: 캔버스 화면 상단에 고정
2. **상태**: 최소화/확대 토글 가능
3. **최소화 상태**: 첫 번째 줄만 표시
4. **확대 상태**: 전체 텍스트 표시 (투명 배경)
5. **편집 기능**: 색상, 크기, 굵기 조정 가능
6. **저장**: JSON 파일에 텍스트 및 스타일 정보 저장

## 구현 계획

### 1. InfoTextPanel 컴포넌트 생성
```vue
<!-- components/InfoTextPanel.vue -->
<template>
  <div class="info-text-panel" :class="{ expanded: isExpanded }">
    <div class="text-content" @click="toggleExpand">
      <div v-if="!isExpanded" class="minimized-text">
        {{ firstLine }}
      </div>
      <div v-else class="expanded-text" v-html="formattedText">
      </div>
    </div>
    <button class="edit-button" @click="openEditDialog">
      <i class="edit-icon">✏️</i>
    </button>
  </div>
</template>
```

### 2. 데이터 구조
```javascript
infoText: {
  content: "시뮬레이션 제목\n상세 설명...",
  style: {
    fontSize: 16,      // px
    color: "#000000",  // hex color
    fontWeight: "normal" // "normal" | "bold"
  },
  isExpanded: false
}
```

### 3. 스타일링
```css
.info-text-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid #ddd;
  transition: all 0.3s ease;
  z-index: 100;
}

.info-text-panel.expanded {
  background: rgba(255, 255, 255, 0.3); /* 투명 배경 */
  backdrop-filter: blur(5px);
}

.minimized-text {
  padding: 8px 40px 8px 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expanded-text {
  padding: 16px 40px 16px 16px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}
```

### 4. 편집 다이얼로그
```vue
<!-- EditInfoTextDialog.vue -->
<template>
  <div class="edit-dialog" v-if="show">
    <div class="dialog-content">
      <h3>정보 텍스트 편집</h3>
      
      <div class="form-group">
        <label>텍스트 내용</label>
        <textarea v-model="localText" rows="5"></textarea>
      </div>
      
      <div class="form-group">
        <label>글자 크기</label>
        <input type="range" v-model="localStyle.fontSize" 
               min="12" max="24" step="1">
        <span>{{ localStyle.fontSize }}px</span>
      </div>
      
      <div class="form-group">
        <label>글자 색상</label>
        <input type="color" v-model="localStyle.color">
      </div>
      
      <div class="form-group">
        <label>글자 굵기</label>
        <select v-model="localStyle.fontWeight">
          <option value="normal">일반</option>
          <option value="bold">굵게</option>
        </select>
      </div>
      
      <div class="dialog-actions">
        <button @click="save">저장</button>
        <button @click="cancel">취소</button>
      </div>
    </div>
  </div>
</template>
```

### 5. App.vue 통합
```javascript
// App.vue에 추가
const infoText = ref({
  content: "시뮬레이션 정보를 입력하세요",
  style: {
    fontSize: 16,
    color: "#000000",
    fontWeight: "normal"
  },
  isExpanded: false
});

// 시뮬레이션 설정 저장 시
function getSimulationConfig() {
  return {
    blocks: blocks.value,
    connections: connections.value,
    globalSignals: globalSignals.value,
    settings: currentSettings.value,
    infoText: infoText.value // 추가
  };
}

// 시뮬레이션 설정 로드 시
function applySimulationConfig(config) {
  // ... 기존 코드
  if (config.infoText) {
    infoText.value = config.infoText;
  }
}
```

### 6. 구현 우선순위
1. **기본 컴포넌트 구조** (InfoTextPanel.vue)
2. **최소화/확대 토글 기능**
3. **편집 다이얼로그 구현**
4. **스타일 적용 기능**
5. **JSON 저장/로드 통합**

### 7. 기술적 고려사항
- **라이브러리 없이 구현**: 간단한 텍스트 편집이므로 별도 라이브러리 불필요
- **반응형 디자인**: 캔버스 너비에 맞춰 자동 조정
- **성능**: 텍스트 변경 시 디바운싱 적용
- **접근성**: 키보드 단축키 지원 (Esc로 최소화 등)

### 8. 예상 구현 시간
- 기본 구조: 1시간
- 스타일링 및 애니메이션: 1시간
- 편집 기능: 2시간
- JSON 통합: 30분
- 테스트 및 디버깅: 30분
- **총 예상 시간**: 5시간

## 추가 개선 사항 (선택적)
1. **마크다운 지원**: 간단한 마크다운 문법 지원
2. **폰트 선택**: 여러 폰트 중 선택 가능
3. **정렬 옵션**: 좌/중/우 정렬
4. **애니메이션**: 부드러운 전환 효과
5. **단축키**: Ctrl+I로 정보 텍스트 편집 등
# 블록 상태 속성 구현 TODO

## 개요
각 블록에 상태 속성(string 타입)을 추가하고, 스크립트 명령어를 통해 실시간으로 변경할 수 있는 기능을 구현합니다.

### 요구사항
- 각 블록은 하나의 상태 속성을 가질 수 있음
- 스크립트 명령어: `블록이름 status = "값"`
- 속성은 덮어쓰기 방식 (기존 값이 있으면 새 값으로 대체)
- 상태 값은 어떤 문자열이든 가능 (running, idle, maintenance 등)

## 구현 계획

### Phase 1: 백엔드 기초 구조 (1-2시간)

#### 1.1 블록 모델 확장
- [ ] `models.py`의 `ProcessBlockConfig`에 상태 필드 추가
  ```python
  class ProcessBlockConfig(BaseModel):
      # 기존 필드들...
      status: Optional[str] = None  # 블록 상태 속성
  ```

#### 1.2 블록 클래스 업데이트
- [ ] `simple_block.py`의 `IndependentBlock`에 상태 관리 추가
  ```python
  class IndependentBlock:
      def __init__(self, ...):
          # 기존 초기화...
          self.status = None  # 블록 상태
      
      def set_status(self, status: str):
          """블록 상태 설정"""
          self.status = status
          self.logger.info(f"Block {self.name} status changed to: {status}")
      
      def get_status(self) -> Optional[str]:
          """현재 블록 상태 반환"""
          return self.status
  ```

#### 1.3 시뮬레이션 결과에 상태 포함
- [ ] `simple_engine_adapter.py`에서 블록 상태 정보 전달
  ```python
  block_states = {
      block_id: {
          'warnings': warnings,
          'status': block.get_status(),  # 상태 추가
          'total_processed': block.total_processed
      }
  }
  ```

### Phase 2: 스크립트 명령어 구현 (2시간)

#### 2.1 명령어 파서 추가
- [ ] `simple_script_executor.py`에 블록 상태 명령어 파싱 추가
  ```python
  # execute_command 메서드에 추가
  elif command_lower == 'status':
      # "블록이름 status = 값" 형식 파싱
      if len(parts) >= 4 and parts[2] == '=':
          block_name = parts[0]
          status_value = ' '.join(parts[3:]).strip().strip('"\'')
          return self.execute_block_status(block_name, status_value)
  ```

#### 2.2 블록 상태 설정 메서드
- [ ] `execute_block_status` 메서드 구현
  ```python
  def execute_block_status(self, block_name: str, status_value: str):
      """블록 상태 설정 명령 실행"""
      # 블록 찾기
      if block_name in self.blocks:
          block = self.blocks[block_name]
          block.set_status(status_value)
          self.logger.info(f"Block '{block_name}' status set to: {status_value}")
          return None
      else:
          raise ValueError(f"Block '{block_name}' not found")
  ```

#### 2.3 명령어 검증
- [ ] 상태 값 검증 (빈 문자열 방지)
- [ ] 블록 이름 존재 여부 확인
- [ ] 따옴표 처리 (작은따옴표, 큰따옴표 모두 지원)

### Phase 3: 프론트엔드 표시 (1-2시간)

#### 3.1 블록 UI 업데이트
- [ ] `CanvasArea.vue`의 `addBlockContent` 함수 수정
  ```javascript
  // 블록 상태 표시 (블록 이름 아래)
  if (blockData.status) {
    const statusText = new Konva.Text({
      text: `[${blockData.status}]`,
      fontSize: props.currentSettings.fontSize * 0.7,
      fill: '#666',
      align: 'center',
      width: blockData.width || props.currentSettings.boxSize,
      x: 0,
      y: 20,  // 블록 이름 아래
      fontStyle: 'italic'
    });
    
    // 상태 배경 (가독성 향상)
    const statusBg = new Konva.Rect({
      x: 10,
      y: 18,
      width: (blockData.width || props.currentSettings.boxSize) - 20,
      height: props.currentSettings.fontSize * 0.9,
      fill: 'rgba(255, 255, 255, 0.7)',
      cornerRadius: 3
    });
    
    blockGroup.add(statusBg);
    blockGroup.add(statusText);
  }
  ```

#### 3.2 실시간 업데이트
- [ ] `App.vue`의 `updateBlockWarnings`에 상태 업데이트 추가
  ```javascript
  if (blockState.status !== undefined) {
    block.status = blockState.status;
  }
  ```

### Phase 4: 스크립트 에디터 지원 (1시간)

#### 4.1 구문 하이라이팅
- [ ] `SimulationScriptLanguage.js`에 status 키워드 추가
  ```javascript
  // 키워드에 'status' 추가
  keywords: ['delay', 'wait', 'if', 'log', 'go', 'to', 'from', 
             'jump', 'create', 'entity', 'dispose', 'force', 
             'execution', 'int', 'status']
  ```

#### 4.2 스크립트 검증
- [ ] `ScriptValidator.js`에 블록 상태 명령어 검증 추가
  ```javascript
  // validateLine 함수에 추가
  if (trimmed.includes(' status = ')) {
    const statusMatch = trimmed.match(/^(\S+)\s+status\s*=\s*["'](.+)["']$/);
    if (!statusMatch) {
      return {
        isValid: false,
        error: '올바른 형식: 블록이름 status = "값"'
      };
    }
    // 블록 이름 검증
    const blockName = statusMatch[1];
    if (!this.isValidBlockName(blockName)) {
      return {
        isValid: false,
        error: `블록 '${blockName}'을 찾을 수 없습니다`
      };
    }
  }
  ```

### Phase 5: JSON 저장/로드 (30분)

#### 5.1 설정 저장
- [ ] `getSimulationSetupData`에서 블록 상태 포함
  ```javascript
  const apiBlocks = blocks.value.map(block => ({
    // 기존 필드들...
    status: block.status || null
  }));
  ```

#### 5.2 설정 로드
- [ ] `applyImportedConfiguration`에서 상태 복원
  ```javascript
  if (config.blocks) {
    blocks.value = config.blocks.map(block => ({
      ...block,
      status: block.status || null
    }));
  }
  ```

### Phase 6: 테스트 및 검증 (30분)

#### 6.1 테스트 시나리오
- [ ] 단일 블록 상태 설정 테스트
- [ ] 여러 블록의 서로 다른 상태 설정
- [ ] 상태 덮어쓰기 테스트
- [ ] 특수 문자가 포함된 상태 값 테스트
- [ ] 저장/로드 후 상태 유지 확인

#### 6.2 테스트 JSON 작성
```json
{
  "blocks": [{
    "id": "1",
    "name": "공정1",
    "status": "running",
    "actions": [{
      "type": "script",
      "parameters": {
        "script": "공정1 status = \"idle\"\ndelay 5\n공정1 status = \"running\""
      }
    }]
  }]
}
```

## 주의사항

1. **기존 코드 보호**
   - Optional 필드로 추가하여 기존 JSON과 호환성 유지
   - 상태가 없는 블록도 정상 동작하도록 처리

2. **명령어 형식**
   - 공백 처리 주의 (블록 이름에 공백이 없다고 가정)
   - 따옴표 없이 입력한 경우 에러 메시지 제공

3. **성능 고려**
   - 블록 상태는 자주 변경될 수 있으므로 효율적인 업데이트 필요
   - 불필요한 UI 재렌더링 방지

4. **확장 가능성**
   - 향후 상태별 색상 표시 기능 추가 가능
   - 상태 히스토리 추적 기능 추가 가능
   - 상태 기반 조건문 추가 가능 (예: `if 공정1 status = "idle"`)

## 예상 구현 시간
- 총 예상 시간: 5-6시간
- 난이도: ⭐⭐ (쉬움)
- 위험도: 🟢 (낮음)

## 다음 단계
구현 완료 후 13번 항목 "블록 정보 화면 표시"와 연계하여 블록 상태를 시각적으로 더 잘 표현할 수 있습니다.
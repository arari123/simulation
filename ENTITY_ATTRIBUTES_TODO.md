# 엔티티 속성 추가 업데이트 상세 계획

## 개요
엔티티에 커스텀 속성과 상태를 추가하여 더 복잡한 시뮬레이션 시나리오를 지원합니다.
- 엔티티 색상 변경 기능 (시각적 구분)
- transit 상태 자동 추적
- 커스텀 속성 부여/제거
- 조건문에서 속성 체크

## 기술 사양

### Backend 구조 변경
```python
# Entity 모델 확장
class Entity:
    id: str
    block_id: str
    position: dict
    state: str = "normal"  # "normal" | "transit"
    custom_attributes: Set[str] = set()  # 예: {"flip", "1c"}
    color: Optional[str] = None  # "gray", "blue", "green", "red", "black", "white"
```

### 스크립트 명령어 확장
```
# 속성 추가
product type += flip(red)        # flip 속성 추가, 색상 red로 변경
product type += flip,1c(blue)    # 여러 속성 추가, 색상 blue로 변경
product type += (green)          # 속성 추가 없이 색상만 변경

# 속성 제거
product type -= flip             # flip 속성 제거
product type -= flip,1c          # 여러 속성 제거
product type -= (default)        # 색상을 기본값으로 변경

# 조건문
if product type = flip           # 단일 속성 체크
if product type = flip or 1c     # OR 조건
if product type = flip and 1c    # AND 조건

# 대기문
wait product type = transit      # transit 상태 대기
wait product type = flip         # 속성 대기
```

## 구현 작업 목록

### Phase 1: Backend 기반 구조 (우선순위: 높음)

#### 1.1 엔티티 모델 확장
- [ ] `app/simple_entity.py` 수정
  - [ ] `state` 필드 추가 (기본값: "normal")
  - [ ] `custom_attributes` Set 필드 추가
  - [ ] `color` 필드 추가 (Optional[str])
  - [ ] 직렬화/역직렬화 메서드 업데이트

#### 1.2 Transit 상태 관리
- [ ] `app/simple_block.py`의 `handle_go_to` 메서드 수정
  - [ ] 이동 시작 시 entity.state = "transit" 설정
  - [ ] 이동 완료 시 entity.state = "normal" 복원
  - [ ] 상태 변경 시 프론트엔드에 알림

#### 1.3 속성 명령어 파서 구현
- [ ] `app/simple_script_executor.py`에 새 함수 추가
  - [ ] `execute_product_type_add()` 함수
    - [ ] 명령어 파싱: "product type += attributes(color)"
    - [ ] 속성 추출 (쉼표로 분리)
    - [ ] 색상 추출 (괄호 내부)
    - [ ] 엔티티 속성 업데이트
  - [ ] `execute_product_type_remove()` 함수
    - [ ] 명령어 파싱: "product type -= attributes"
    - [ ] 지정된 속성 제거

### Phase 2: 조건문 확장 (우선순위: 높음)

#### 2.1 IF 조건문 속성 체크
- [ ] `execute_if()` 함수 확장
  - [ ] "product type = attributes" 패턴 인식
  - [ ] 단일 속성 체크 로직
  - [ ] OR 조건 처리 (속성 중 하나라도 있으면 true)
  - [ ] AND 조건 처리 (모든 속성이 있어야 true)

#### 2.2 WAIT 조건문 속성 체크
- [ ] `execute_wait()` 함수 확장
  - [ ] "product type = attributes" 패턴 인식
  - [ ] transit 상태 체크 지원
  - [ ] 커스텀 속성 체크 지원
  - [ ] OR/AND 조건 지원

### Phase 3: Frontend 시각화 (우선순위: 중간)

#### 3.1 엔티티 데이터 구조 확장
- [ ] `src/components/CanvasArea.vue` 수정
  - [ ] entities 데이터에 color 필드 추가
  - [ ] updateEntities 메서드에서 색상 정보 처리

#### 3.2 엔티티 렌더링 업데이트
- [ ] `drawEntities()` 메서드 수정
  - [ ] 색상별 배경색 매핑
    ```javascript
    const colorMap = {
      'gray': '#808080',
      'blue': '#0000FF',
      'green': '#00FF00',
      'red': '#FF0000',
      'black': '#000000',
      'white': '#FFFFFF',
      'default': '#FFA500'  // 기본 주황색
    }
    ```
  - [ ] 텍스트 색상 자동 조정 (배경색에 따라)
    ```javascript
    const textColor = ['black', 'blue'].includes(entity.color) ? 'white' : 'black'
    ```

#### 3.3 실시간 색상 동기화
- [ ] WebSocket 메시지 처리
  - [ ] 속성 변경 이벤트 수신
  - [ ] 엔티티 색상 업데이트

### Phase 4: 속성 영속성 (우선순위: 높음)

#### 4.1 블록 간 이동 시 속성 유지
- [ ] `transfer_entity()` 메서드 확인
  - [ ] 속성 정보가 유지되는지 검증
  - [ ] 필요시 deep copy 적용

#### 4.2 시뮬레이션 상태 저장/로드
- [ ] JSON 직렬화에 속성 포함
  - [ ] custom_attributes 배열로 변환
  - [ ] color 필드 포함

### Phase 5: 테스트 및 검증 (우선순위: 낮음)

#### 5.1 단위 테스트
- [ ] 속성 추가/제거 테스트
- [ ] 조건문 평가 테스트
- [ ] 상태 전환 테스트

#### 5.2 통합 테스트 시나리오
```
# 테스트 시나리오 1: 기본 속성 추가/제거
delay 1
product type += flip(red)
delay 2
if product type = flip
    product type -= flip
    product type += (default)

# 테스트 시나리오 2: 복합 조건
product type += flip,1c(blue)
if product type = flip and 1c
    go to 공정2.L,3
wait product type = transit
wait product type = normal

# 테스트 시나리오 3: 색상만 변경
product type += (green)
delay 1
product type += quality(red)
```

### Phase 6: 문서화 (우선순위: 낮음)

#### 6.1 CLAUDE.md 업데이트
- [ ] 새 스크립트 명령어 추가
- [ ] 예제 코드 포함

#### 6.2 사용자 가이드
- [ ] 속성 활용 시나리오
- [ ] 색상 활용 가이드

## 구현 순서 권장사항

1. **Week 1**: Backend 기반 구조 (Phase 1)
   - 엔티티 모델 확장
   - Transit 상태 관리
   - 기본 명령어 파서

2. **Week 2**: 조건문 지원 (Phase 2)
   - IF 조건문 확장
   - WAIT 조건문 확장

3. **Week 3**: Frontend 통합 (Phase 3)
   - 색상 렌더링
   - 실시간 동기화

4. **Week 4**: 마무리
   - 속성 영속성 검증
   - 테스트 및 문서화

## 주의사항

1. **기존 기능 보존**: 새 필드는 Optional로 추가하여 기존 시뮬레이션 호환성 유지
2. **성능 고려**: Set 자료구조로 속성 체크 O(1) 시간복잡도 유지
3. **확장성**: 향후 속성 타입 확장 가능하도록 구조 설계
4. **에러 처리**: 잘못된 속성명이나 색상명에 대한 graceful 처리

## 예상 난이도 및 위험성
- **전체 난이도**: ⭐⭐⭐⭐ (중상)
- **위험성**: 🟢 (낮음) - 기존 구조에 추가만 하므로 안전
- **예상 소요 시간**: 3-4주

## 다음 단계
1. 이 계획서 검토 및 승인
2. Phase 1부터 순차적 구현 시작
3. 각 Phase 완료 후 테스트 및 피드백
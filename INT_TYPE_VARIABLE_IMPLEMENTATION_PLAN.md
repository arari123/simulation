# Int 타입 전역 변수 구현 계획

## 개요
현재 boolean 타입만 지원하는 전역 신호 시스템을 확장하여 정수형(int) 변수를 지원하도록 구현합니다.
기존 시스템과의 호환성을 유지하면서 모듈화된 구조로 안전하게 추가합니다.

## 현재 시스템 분석
- **Frontend**: `globalSignals`에 boolean 값만 저장
- **Backend**: `SimpleSignalManager`가 Dict[str, bool] 타입으로 관리
- **스크립트**: `신호명 = true/false` 형태만 지원

## 구현 전략

### 1. 모듈화 접근법
```
┌─────────────────────┐
│  SignalManager      │ (기존 boolean 신호 관리)
└─────────────────────┘
┌─────────────────────┐
│ IntegerVariableManager │ (새로운 정수 변수 관리)
└─────────────────────┘
┌─────────────────────┐
│ UnifiedVariableAccessor │ (통합 접근 인터페이스)
└─────────────────────┘
```

### 2. 데이터 모델 확장

#### Frontend 신호 구조
```javascript
{
  id: string,
  name: string,
  type: 'boolean' | 'integer',  // 새 필드
  value: boolean | number,       // 타입 확장
  initialValue: boolean | number
}
```

#### Backend 저장 구조
- 기존: `signals: Dict[str, bool]`
- 추가: `integer_variables: Dict[str, int]`

## 스크립트 명령어 설계

### 1. 변수 선언 및 초기화
```
// 자동 선언 방식 (UI에서 생성한 변수 외에도 스크립트에서 직접 사용)
int count = 0          // 초기값 설정
int total = count      // 다른 변수값으로 초기화
```

### 2. 산술 연산
```
// 기본 산술 연산
int count += 1         // 증가
int count -= 1         // 감소
int count *= 2         // 곱하기
int count /= 2         // 나누기 (정수 나눗셈)

// 변수간 연산
int total = count + 5
int result = a - b
int result = a * b
int result = a / b     // 정수 나눗셈 (나머지 버림)
```

### 3. 비교 연산
```
// if 조건문에서 사용
if int count > 10
if int count >= 10
if int count < 10
if int count <= 10
if int count = 10
if int count != 10

// wait 조건문에서 사용
wait int count > 10
wait int total = 100

// 복합 조건
if int count > 10 and 신호A = true
wait int count = 0 or int total > 100
```

### 4. 로그 출력
```
log "현재 카운트: {count}"
log "총합: {total}, 개수: {count}"
```

## 구현 순서

### Phase 1: 기반 구축 (우선순위: 높음)
1. **타입 시스템 설계**
   - SignalType enum 정의 (BOOLEAN, INTEGER)
   - 타입별 유효성 검증 로직

2. **Backend 모듈 구현**
   - `IntegerVariableManager` 클래스 생성
   - 기본 CRUD 메서드 구현
   - 초기값 관리 시스템

3. **Frontend 데이터 모델**
   - `useSignals.js` 확장
   - 타입 필드 추가
   - 값 타입 유니온 처리

4. **UI 컴포넌트 수정**
   - 타입 선택 드롭다운
   - 조건부 입력 필드 렌더링
   - 정수값 표시 방식

### Phase 2: 스크립트 지원 (우선순위: 중간)
5. **파서 확장**
   - `int 변수명 연산자 값` 패턴 인식
   - 산술 연산자 토큰화
   - 비교 연산자 파싱

6. **실행기 구현**
   - `execute_int_operation()` 메서드
   - 산술 연산 함수들
   - 오버플로우 처리

7. **조건문 통합**
   - 정수 비교 로직
   - 기존 boolean 조건과 통합
   - 혼합 조건 처리

8. **API 계층 수정**
   - 신호 데이터 직렬화
   - 타입 정보 포함
   - 하위 호환성 유지

### Phase 3: 완성도 향상 (우선순위: 낮음)
9. **검증 강화**
   - 정수 연산 검증 규칙
   - 타입 불일치 오류 처리

10. **시각화 개선**
    - 정수값 직접 표시
    - 값 변화 애니메이션

11. **로그 통합**
    - 변수 치환 로직
    - 포맷 문자열 처리

12. **테스트 및 문서화**
    - 단위 테스트 작성
    - 통합 테스트 시나리오
    - 사용자 문서 업데이트

## 기술적 고려사항

### 1. 타입 안정성
- TypeScript/Python 타입 힌트 활용
- 런타임 타입 검증
- 명확한 오류 메시지

### 2. 성능 최적화
- 변수 접근 캐싱
- 연산 결과 메모이제이션
- 대량 변수 처리 최적화

### 3. 하위 호환성
- 기존 boolean 신호 동작 유지
- 구버전 JSON 파일 자동 마이그레이션
- API 버전 관리

### 4. 확장성
- 향후 float 타입 추가 고려
- 문자열 변수 지원 가능성
- 배열/리스트 타입 확장

## 예상 구현 난이도 및 일정

### 난이도 평가
- **전체 난이도**: ⭐⭐⭐⭐ (중상)
- **위험성**: 🟢 (낮음) - 모듈화로 기존 코드 영향 최소화

### 예상 일정
- Phase 1: 3-4일 (기반 구축)
- Phase 2: 4-5일 (스크립트 지원)
- Phase 3: 2-3일 (완성도 향상)
- **총 예상 기간**: 9-12일

## 테스트 시나리오

### 1. 기본 동작 테스트
```json
{
  "globalSignals": [
    {"name": "count", "type": "integer", "initialValue": 0},
    {"name": "threshold", "type": "integer", "initialValue": 10}
  ],
  "blocks": [{
    "script": [
      "int count += 1",
      "if int count > threshold",
      "  log \"임계값 초과: {count}\"",
      "  신호A = true"
    ]
  }]
}
```

### 2. 복합 연산 테스트
```json
{
  "script": [
    "int total = 0",
    "int batch = 5",
    "delay 1",
    "int total += batch",
    "wait int total >= 20",
    "go to 다음공정.L"
  ]
}
```

## 주의사항

1. **변수명 규칙**
   - 정수 변수와 boolean 신호 이름 중복 불가
   - 예약어 사용 금지 (int, boolean 등)

2. **연산 제한**
   - 0으로 나누기 방지
   - 정수 오버플로우 처리
   - 음수 처리 정책 결정

3. **UI/UX**
   - 타입별 시각적 구분
   - 직관적인 에러 메시지
   - 도움말 제공

## 다음 단계

1. 이 계획서 검토 및 승인
2. Phase 1부터 순차적 구현
3. 각 Phase 완료 시 중간 테스트
4. 사용자 피드백 반영
5. 최종 문서화 및 배포
# IF 조건부 AND 타입 추가 - 상세 TODO 문서

## 1. 현재 상태 분석

### 1.1 구현 완료된 부분
- **엔티티 속성 조건**:
  - `if product type = flip and 1c` ✅ 구현됨
  - `if product type = flip or 1c` ✅ 구현됨
  - `wait product type = flip and 1c` ✅ 구현됨
  - `wait product type = flip or 1c` ✅ 구현됨

### 1.2 미구현 부분
- **일반 신호 조건**:
  - `if 신호1 = true and 신호2 = false` ❌ 미구현
  - `if 신호1 = true or 신호2 = false` ❌ 미구현
  - `wait 신호1 = true and 신호2 = false` ❌ 미구현 (OR만 구현됨)

### 1.3 현재 코드 구조
```python
# simple_script_executor.py
def execute_if(self, env, condition, entity=None):
    # product type 조건: AND/OR 모두 지원 ✅
    if 'product type =' in condition:
        # AND/OR 로직 구현됨
    
    # 일반 신호 조건: 단일 조건만 지원 ❌
    elif ' = ' in condition:
        # 단일 신호만 체크

def execute_wait(self, env, condition, entity=None):
    # product type 조건: AND/OR 모두 지원 ✅
    if 'product type =' in condition:
        # AND/OR 로직 구현됨
    
    # 일반 신호 조건: OR만 지원 ❌
    elif ' or ' in condition:
        # OR 조건 처리
    elif ' = ' in condition:
        # 단일 조건 처리
```

## 2. 구현 상세 계획

### 2.1 IF 명령어 - 일반 신호 AND/OR 지원

#### 2.1.1 구현 내용
- 기존 `execute_if` 함수에 일반 신호의 AND/OR 조건 처리 추가
- 파싱 순서: AND → OR → 단일 조건
- 중첩 조건은 지원하지 않음 (괄호 없음)

#### 2.1.2 지원할 문법
```
if 신호1 = true
if 신호1 = true and 신호2 = false
if 신호1 = true and 신호2 = false and 신호3 = true
if 신호1 = true or 신호2 = false
if 신호1 = true or 신호2 = false or 신호3 = true
```

#### 2.1.3 구현 코드 구조
```python
def execute_if(self, env, condition, entity=None):
    # 1. product type 조건 체크 (기존 코드 유지)
    if 'product type =' in condition and entity:
        # 기존 코드...
    
    # 2. 일반 신호 AND 조건 체크 (새로 추가)
    elif ' and ' in condition and ' = ' in condition:
        conditions = condition.split(' and ')
        for cond in conditions:
            if not self._evaluate_single_signal_condition(cond.strip()):
                return False
        return True
    
    # 3. 일반 신호 OR 조건 체크 (새로 추가)
    elif ' or ' in condition and ' = ' in condition:
        conditions = condition.split(' or ')
        for cond in conditions:
            if self._evaluate_single_signal_condition(cond.strip()):
                return True
        return False
    
    # 4. 단일 신호 조건 체크 (기존 코드)
    elif ' = ' in condition:
        return self._evaluate_single_signal_condition(condition)
    
    return False
```

### 2.2 WAIT 명령어 - 일반 신호 AND 지원

#### 2.2.1 구현 내용
- 기존 `execute_wait` 함수에 일반 신호의 AND 조건 처리 추가
- OR 조건은 이미 구현되어 있음
- AND 조건: 모든 조건이 만족될 때까지 대기

#### 2.2.2 지원할 문법
```
wait 신호1 = true
wait 신호1 = true and 신호2 = false
wait 신호1 = true and 신호2 = false and 신호3 = true
wait 신호1 = true or 신호2 = false  (기존 지원)
```

#### 2.2.3 구현 코드 구조
```python
def execute_wait(self, env, condition, entity=None):
    # 1. product type 조건 체크 (기존 코드 유지)
    if 'product type =' in condition and entity:
        # 기존 코드...
    
    # 2. 일반 신호 AND 조건 체크 (새로 추가)
    elif ' and ' in condition and ' = ' in condition:
        conditions = condition.split(' and ')
        while True:
            all_satisfied = True
            for cond in conditions:
                if not self._evaluate_single_signal_condition(cond.strip()):
                    all_satisfied = False
                    break
            if all_satisfied:
                return
            yield env.timeout(0.01)
    
    # 3. 일반 신호 OR 조건 체크 (기존 코드)
    elif ' or ' in condition:
        # 기존 코드...
    
    # 4. 단일 신호 조건 체크 (기존 코드)
    elif ' = ' in condition:
        # 기존 코드...
```

### 2.3 공통 헬퍼 함수 추가

#### 2.3.1 단일 신호 조건 평가 함수
```python
def _evaluate_single_signal_condition(self, condition: str) -> bool:
    """단일 신호 조건 평가 헬퍼 함수"""
    if ' = ' not in condition:
        return False
    
    parts = condition.split(' = ', 1)
    signal_name = parts[0].strip()
    expected_value = parts[1].strip().lower() == 'true'
    
    if self.signal_manager:
        current_value = self.signal_manager.get_signal(signal_name, False)
        return current_value == expected_value
    
    return False
```

## 3. 테스트 시나리오

### 3.1 IF 조건문 테스트
```
# 테스트 1: AND 조건 - 모두 참
신호1 = true
신호2 = true
if 신호1 = true and 신호2 = true
    test_result = passed

# 테스트 2: AND 조건 - 하나라도 거짓
신호1 = true
신호2 = false
if 신호1 = true and 신호2 = true
    test_result = failed
    
# 테스트 3: OR 조건 - 하나라도 참
신호1 = true
신호2 = false
if 신호1 = true or 신호2 = true
    test_result = passed

# 테스트 4: 복합 조건
신호1 = true
신호2 = false
신호3 = true
if 신호1 = true and 신호3 = true
    test_result = passed
```

### 3.2 WAIT 조건문 테스트
```
# 테스트 1: AND 조건 대기
신호1 = false
신호2 = false
wait 신호1 = true and 신호2 = true
# 다른 블록에서:
delay 2
신호1 = true
delay 2
신호2 = true  # 이 시점에서 wait 해제

# 테스트 2: 혼합 조건
wait product type = flip and 신호1 = true
```

## 4. 구현 시 주의사항

### 4.1 기존 코드 보호
- 기존에 작동하는 단일 조건과 OR 조건 로직을 변경하지 않음
- 새로운 조건 체크를 기존 조건보다 먼저 배치하여 우선순위 보장
- 헬퍼 함수로 중복 코드 최소화

### 4.2 파싱 우선순위
1. product type 조건 (엔티티 속성)
2. AND 조건 (복수 조건)
3. OR 조건 (복수 조건)
4. 단일 조건

### 4.3 성능 고려사항
- wait 조건에서 0.01초마다 체크 (기존과 동일)
- 불필요한 문자열 파싱 최소화
- 조건 평가 결과 캐싱은 하지 않음 (신호가 실시간으로 변경될 수 있음)

### 4.4 에러 처리
- 잘못된 조건 문법은 False 반환
- 신호가 존재하지 않으면 False로 간주
- 로깅은 최소화하여 성능 영향 방지

## 5. 예상 코드 변경량

### 5.1 수정 파일
- `backend/app/simple_script_executor.py`
  - `execute_if` 함수: 약 20줄 추가
  - `execute_wait` 함수: 약 15줄 추가
  - `_evaluate_single_signal_condition` 헬퍼 함수: 약 15줄 추가

### 5.2 총 예상 변경량
- 추가 코드: 약 50줄
- 수정 코드: 0줄 (기존 코드 변경 없음)
- 삭제 코드: 0줄

## 6. 위험성 평가

### 6.1 위험 요소
- 기존 단일 조건 로직에 영향 없음 (조건 체크 순서로 분리)
- 기존 OR 조건 로직에 영향 없음 (독립적 구현)
- 엔티티 속성 조건과 충돌 없음 (별도 분기)

### 6.2 위험성 등급: 🟢 (낮음)
- 기존 코드를 수정하지 않고 추가만 진행
- 명확한 조건 분기로 기존 기능 보호
- 단순한 문자열 파싱과 조건 평가만 수행

## 7. 종합 테스트 환경 구성

### 7.1 테스트 시뮬레이션 환경 JSON 파일

#### 7.1.1 파일명: `test_if_wait_conditions.json`

#### 7.1.2 테스트 블록 구성
```json
{
  "blocks": [
    {
      "id": "1",
      "name": "투입",
      "type": "source",
      "x": 100,
      "y": 200,
      "actions": [
        {
          "type": "script",
          "parameters": {
            "script": "// 기존 기능 테스트\nlog \"[투입] 엔티티 생성\"\nproduct type += test(red)\ndelay 1\n\n// 새 기능 테스트용 신호 설정\n신호A = true\n신호B = false\n신호C = true\n\ngo to 기존테스트.L,1"
          }
        }
      ]
    },
    {
      "id": "2", 
      "name": "기존테스트",
      "type": "process",
      "x": 300,
      "y": 100,
      "maxCapacity": 5,
      "actions": [
        {
          "type": "script",
          "parameters": {
            "script": "log \"[기존테스트] 기존 IF 단일 조건 테스트\"\nif 신호A = true\n    log \"✅ 기존 IF 단일 조건 통과\"\n\nlog \"[기존테스트] 기존 WAIT OR 조건 테스트\"\nwait 신호B = true or 신호C = true\nlog \"✅ 기존 WAIT OR 조건 통과\"\n\nlog \"[기존테스트] 엔티티 속성 AND 조건 테스트\"\nproduct type += flip\nif product type = test and flip\n    log \"✅ 엔티티 IF AND 조건 통과\"\n\ngo to 신규테스트.L,1"
          }
        }
      ]
    },
    {
      "id": "3",
      "name": "신규테스트", 
      "type": "process",
      "x": 500,
      "y": 100,
      "maxCapacity": 5,
      "actions": [
        {
          "type": "script",
          "parameters": {
            "script": "log \"[신규테스트] 새 IF AND 조건 테스트\"\nif 신호A = true and 신호C = true\n    log \"✅ 새 IF AND 조건 통과 (A=true, C=true)\"\n\nif 신호A = true and 신호B = true\n    log \"❌ 이 메시지는 출력되면 안됨 (B=false)\"\n\nlog \"[신규테스트] 새 IF OR 조건 테스트\"\nif 신호A = true or 신호B = true\n    log \"✅ 새 IF OR 조건 통과 (A=true)\"\n\nif 신호B = true or 신호D = true\n    log \"❌ 이 메시지는 출력되면 안됨 (B,D=false)\"\n\ngo to AND대기테스트.L,1"
          }
        }
      ]
    },
    {
      "id": "4",
      "name": "AND대기테스트",
      "type": "process", 
      "x": 700,
      "y": 100,
      "maxCapacity": 5,
      "actions": [
        {
          "type": "script",
          "parameters": {
            "script": "log \"[AND대기테스트] 새 WAIT AND 조건 테스트 시작\"\n신호B = false\n신호D = false\nlog \"현재 상태: B=false, D=false\"\n\n// 다른 블록에서 신호를 변경할 예정\nwait 신호B = true and 신호D = true\nlog \"✅ 새 WAIT AND 조건 통과 (B=true, D=true)\"\n\ngo to 복합테스트.L,1"
          }
        }
      ]
    },
    {
      "id": "5",
      "name": "신호제어",
      "type": "process",
      "x": 300,
      "y": 300,
      "maxCapacity": 1,
      "actions": [
        {
          "type": "script", 
          "parameters": {
            "script": "// AND 대기 테스트를 위한 신호 제어\nlog \"[신호제어] 3초 후 신호B = true\"\ndelay 3\n신호B = true\n\nlog \"[신호제어] 2초 후 신호D = true\"\ndelay 2\n신호D = true\nlog \"[신호제어] AND 조건 충족됨\""
          }
        }
      ]
    },
    {
      "id": "6",
      "name": "복합테스트",
      "type": "process",
      "x": 900,
      "y": 100,
      "maxCapacity": 5,
      "actions": [
        {
          "type": "script",
          "parameters": {
            "script": "log \"[복합테스트] 3개 이상 AND 조건 테스트\"\nif 신호A = true and 신호C = true and 신호B = true and 신호D = true\n    log \"✅ 4개 AND 조건 통과\"\n\nlog \"[복합테스트] 3개 이상 OR 조건 테스트\"\n신호E = false\nif 신호E = true or 신호B = true or 신호F = true\n    log \"✅ 3개 OR 조건 통과 (B=true)\"\n\nlog \"[복합테스트] 혼합 조건 테스트\"\nwait product type = test and flip\nlog \"✅ 엔티티 속성 WAIT AND 통과\"\n\ngo to 배출.L,1"
          }
        }
      ]
    },
    {
      "id": "7",
      "name": "배출",
      "type": "sink",
      "x": 1100,
      "y": 200,
      "actions": []
    }
  ],
  "connections": [
    {"from_block_id": "1", "from_connector_id": "R", "to_block_id": "2", "to_connector_id": "L"},
    {"from_block_id": "2", "from_connector_id": "R", "to_block_id": "3", "to_connector_id": "L"},
    {"from_block_id": "3", "from_connector_id": "R", "to_block_id": "4", "to_connector_id": "L"},
    {"from_block_id": "4", "from_connector_id": "R", "to_block_id": "6", "to_connector_id": "L"},
    {"from_block_id": "6", "from_connector_id": "R", "to_block_id": "7", "to_connector_id": "L"},
    {"from_block_id": "1", "from_connector_id": "R", "to_block_id": "5", "to_connector_id": "L"}
  ],
  "globalSignals": [
    {"name": "신호A", "value": false},
    {"name": "신호B", "value": false},
    {"name": "신호C", "value": false},
    {"name": "신호D", "value": false},
    {"name": "신호E", "value": false},
    {"name": "신호F", "value": false}
  ]
}
```

### 7.2 로그 추가 계획

#### 7.2.1 스크립트 실행기에 로그 추가
```python
# simple_script_executor.py

def execute_if(self, env, condition, entity=None):
    # 디버그 로그 추가
    logger.debug(f"[IF 조건 평가] 조건: {condition}")
    
    # ... 기존 코드 ...
    
    # 결과 로그
    logger.debug(f"[IF 조건 결과] 조건: {condition} → {result}")
    return result

def execute_wait(self, env, condition, entity=None):
    logger.debug(f"[WAIT 시작] 조건: {condition}")
    
    # AND 조건 처리
    elif ' and ' in condition and ' = ' in condition:
        logger.debug(f"[WAIT AND 조건] 평가 중: {condition}")
        # ... 구현 ...
        logger.debug(f"[WAIT AND 조건] 충족됨: {condition}")
```

#### 7.2.2 log 명령어 구현
```python
def execute_log(self, env: simpy.Environment, message: str, block_name: str = None) -> Generator:
    """log 명령어 실행"""
    timestamp = f"{env.now:.1f}"
    log_entry = f"[{timestamp}s] {f'[{block_name}]' if block_name else ''} {message}"
    
    # 백엔드 로그
    logger.info(f"시뮬레이션 로그: {log_entry}")
    
    # 프론트엔드로 전송할 로그 저장
    if hasattr(self, 'simulation_logs'):
        self.simulation_logs.append({
            'time': env.now,
            'block': block_name,
            'message': message
        })
    
    yield env.timeout(0)
```

### 7.3 예상 테스트 결과 로그

```
[0.0s] [투입] 엔티티 생성
[1.0s] [기존테스트] 기존 IF 단일 조건 테스트
[1.0s] ✅ 기존 IF 단일 조건 통과
[1.0s] [기존테스트] 기존 WAIT OR 조건 테스트
[1.0s] ✅ 기존 WAIT OR 조건 통과
[1.0s] [기존테스트] 엔티티 속성 AND 조건 테스트
[1.0s] ✅ 엔티티 IF AND 조건 통과
[2.0s] [신규테스트] 새 IF AND 조건 테스트
[2.0s] ✅ 새 IF AND 조건 통과 (A=true, C=true)
[2.0s] [신규테스트] 새 IF OR 조건 테스트
[2.0s] ✅ 새 IF OR 조건 통과 (A=true)
[3.0s] [AND대기테스트] 새 WAIT AND 조건 테스트 시작
[3.0s] 현재 상태: B=false, D=false
[3.0s] [신호제어] 3초 후 신호B = true
[6.0s] [신호제어] 2초 후 신호D = true
[8.0s] [신호제어] AND 조건 충족됨
[8.0s] ✅ 새 WAIT AND 조건 통과 (B=true, D=true)
[9.0s] [복합테스트] 3개 이상 AND 조건 테스트
[9.0s] ✅ 4개 AND 조건 통과
[9.0s] [복합테스트] 3개 이상 OR 조건 테스트
[9.0s] ✅ 3개 OR 조건 통과 (B=true)
[9.0s] [복합테스트] 혼합 조건 테스트
[9.0s] ✅ 엔티티 속성 WAIT AND 통과
```

### 7.4 테스트 검증 체크리스트

#### 7.4.1 기존 기능 정상 동작 확인
- [ ] IF 단일 조건: `if 신호A = true`
- [ ] WAIT 단일 조건: `wait 신호 = true`
- [ ] WAIT OR 조건: `wait 신호B = true or 신호C = true`
- [ ] 엔티티 IF AND: `if product type = test and flip`
- [ ] 엔티티 IF OR: `if product type = test or flip`
- [ ] 엔티티 WAIT AND: `wait product type = test and flip`
- [ ] 엔티티 WAIT OR: `wait product type = test or flip`

#### 7.4.2 신규 기능 정상 동작 확인
- [ ] IF AND 조건 (2개): `if 신호A = true and 신호C = true`
- [ ] IF AND 조건 (3개 이상): `if A = true and B = true and C = true`
- [ ] IF OR 조건 (2개): `if 신호A = true or 신호B = true`
- [ ] IF OR 조건 (3개 이상): `if A = true or B = true or C = true`
- [ ] WAIT AND 조건: `wait 신호B = true and 신호D = true`
- [ ] WAIT AND 조건 대기 후 충족

#### 7.4.3 엣지 케이스 확인
- [ ] 존재하지 않는 신호 참조 시 False 처리
- [ ] 잘못된 문법 시 False 처리
- [ ] AND 조건에서 하나라도 False면 전체 False
- [ ] OR 조건에서 하나라도 True면 전체 True

## 8. 구현 후 문서화

### 7.1 CLAUDE.md 업데이트
```markdown
### Script Syntax - Conditional Execution

#### IF Conditions
- Single: `if 신호명 = true`
- AND: `if 신호1 = true and 신호2 = false`
- OR: `if 신호1 = true or 신호2 = false`
- Entity: `if product type = flip and 1c`

#### WAIT Conditions
- Single: `wait 신호명 = true`
- AND: `wait 신호1 = true and 신호2 = false`
- OR: `wait 신호1 = true or 신호2 = false`
- Entity: `wait product type = flip and 1c`
```

### 7.2 사용자 가이드
- AND 조건: 모든 조건이 참일 때만 실행/통과
- OR 조건: 하나라도 참이면 실행/통과
- 우선순위: AND가 OR보다 먼저 평가됨
- 중첩 조건(괄호)은 지원하지 않음
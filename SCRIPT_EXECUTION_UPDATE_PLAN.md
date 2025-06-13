# 스크립트 실행 방식 업데이트 계획서

## 1. 개요

현재 엔티티 도착/생성 시 자동으로 스크립트를 실행하는 방식에서 벗어나, 명시적인 스크립트 실행 명령어를 통해 블록의 스크립트를 실행하는 방식으로 전환합니다.

### 변경 이유
- 엔티티 움직임에 따른 자동 스크립트 실행 로직이 복잡하고 버그가 많음
- 개발 및 디버깅 시간이 오래 걸림
- 시뮬레이션 환경 작성에 제약이 있음
- 최근 업데이트 이후에도 버그로 인한 정상 작동 문제 발생

## 2. 주요 변경사항

### 2.1 제거할 기능
1. **엔티티 도착 시 스크립트 자동 실행**
   - `simple_block.py`의 엔티티 감지 및 처리 로직
   - `process_entity()` 메서드의 자동 호출
   - `entities_in_block` 모니터링 로직

2. **엔티티 처리 추적**
   - `entity.processed_by_blocks` 추적 제거
   - 엔티티별 처리 상태 관리 제거

### 2.2 유지할 기능
1. **Force Execution**
   - 첫 줄에 `force execution`이 있는 블록의 자동 실행 유지
   - 스크립트 완료 후 자동으로 다시 시작 (무한 루프)
   - 엔티티 없이 계속 실행됨

### 2.3 추가할 기능
1. **새로운 스크립트 명령어: `execute`**
   ```
   execute 블록이름              # 지정한 블록의 스크립트 실행
   ```

2. **실행 제어 메커니즘**
   - 블록 실행 상태 관리: `Idle` / `Running`
   - `Idle` 상태일 때만 execute 명령 수락
   - `Running` 상태에서는 execute 명령 무시
   - 스크립트 실행 완료 시 자동으로 `Idle` 상태로 전환
   - 다른 블록에서 다시 실행 요청 가능

## 3. 구현 상세

### 3.1 Backend 수정사항

#### `simple_block.py` 수정
```python
class IndependentBlock:
    def __init__(self, ...):
        # 기존 속성들...
        self.execution_state = "idle"  # "idle" or "running"
        self.is_executing_script = False
        
    def create_block_process(self):
        # 엔티티 도착 감지 로직 제거
        # force execution 로직만 유지
        
    def execute_script_by_command(self):
        """명령어를 통한 스크립트 실행"""
        if self.execution_state == "running":
            return False  # 실행 중이므로 무시
            
        self.execution_state = "running"
        self.is_executing_script = True
        
        # 엔티티 없이 스크립트 실행
        # self.script_executor.execute_script(entity=None)
        
        # 실행 완료 후
        self.execution_state = "idle"
        self.is_executing_script = False
        return True
```

#### `simple_script_executor.py` 수정
```python
def execute_line(self, line, ...):
    # 새로운 execute 명령어 파싱 및 실행
    if line.startswith("execute "):
        return self.execute_block_script(line[8:].strip(), ...)
```

#### `simple_simulation_engine.py` 수정
- 블록 검색 및 스크립트 실행 API 추가
- 리셋 시 모든 블록의 `execution_state`를 "idle"로 초기화
- 블록 상태 모니터링 지원

### 3.2 Frontend 수정사항

#### 스크립트 에디터 업데이트
1. **Syntax Highlighting**
   - `execute` 키워드 추가
   - 블록 이름 자동완성 지원

2. **Validation**
   - `execute` 명령어 문법 검증
   - 존재하는 블록 이름 확인

#### 시각적 피드백
- 블록 실행 상태 표시
  - Idle: 기본 상태 (실행 가능)
  - Running: 스크립트 실행 중 (주황색 테두리 등)
- 실행 상태 텍스트 또는 아이콘 표시

## 4. 마이그레이션 전략

### 4.1 기존 시뮬레이션 호환성
1. **자동 변환 도구 제공**
   - 기존 시뮬레이션 파일을 새 방식으로 변환
   - 엔티티 도착 시 실행되던 스크립트를 execute 명령어로 변경

2. **예시 변환**
   ```
   # 기존 방식 (블록 A에서 블록 B로 엔티티 이동 시 B 실행)
   # 블록 A 스크립트:
   go OUT to 블록B.IN
   
   # 새로운 방식
   # 블록 A 스크립트:
   go OUT to 블록B.IN
   execute 블록B
   ```

### 4.2 단계별 구현
1. **Phase 1**: Backend 로직 변경
   - 엔티티 기반 실행 제거
   - execute 명령어 구현
   
2. **Phase 2**: Frontend 업데이트
   - 스크립트 에디터 지원
   - 시각적 피드백
   
3. **Phase 3**: 마이그레이션 도구
   - 자동 변환 스크립트
   - 문서 및 예제 업데이트

## 5. 장단점 분석

### 장점
1. **명확한 실행 흐름**
   - 스크립트 실행 시점이 명시적으로 표현됨
   - 디버깅이 용이함

2. **단순한 구조**
   - 엔티티 추적 로직 제거로 코드 단순화
   - 버그 발생 가능성 감소

3. **유연한 제어**
   - 원하는 시점에 원하는 블록 실행 가능
   - 복잡한 시나리오 구현 가능

### 단점
1. **추가 작업 필요**
   - 사용자가 execute 명령어를 명시적으로 작성해야 함
   - 기존 시뮬레이션 수정 필요

2. **학습 곡선**
   - 새로운 패러다임에 적응 필요
   - 문서화 및 교육 필요

## 6. 예상 작업량

- **Backend 수정**: 2-3일
  - 기존 로직 제거 및 새 명령어 구현
  - 테스트 케이스 작성
  
- **Frontend 수정**: 1-2일
  - 스크립트 에디터 업데이트
  - UI 피드백 추가
  
- **마이그레이션 도구**: 1일
  - 변환 스크립트 작성
  - 문서 업데이트

**총 예상 기간**: 4-6일

## 7. 리스크 및 대응방안

### 리스크
1. **기존 사용자 혼란**
   - 대응: 상세한 마이그레이션 가이드 제공

2. **복잡한 시나리오 처리**
   - 대응: 다양한 예제 및 베스트 프랙티스 문서화

3. **성능 이슈**
   - 대응: execute 명령어 최적화 및 캐싱

## 8. 테스트 계획

1. **단위 테스트**
   - execute 명령어 파싱
   - 블록 실행 제어
   - 플래그 관리

2. **통합 테스트**
   - 전체 시뮬레이션 흐름
   - Force execution과의 상호작용
   - 에러 처리

3. **성능 테스트**
   - 대량 execute 명령어 처리
   - 메모리 사용량 확인

## 9. 구현 예시

### 새로운 시뮬레이션 작성 예시
```
# 투입 블록 (force execution)
force execution
create product
go OUT to 공정1.IN
execute 공정1

# 공정1 블록
delay 5
go OUT to 공정2.IN  
execute 공정2

# 공정2 블록
delay 3
if 품질검사 = true
    go OUT to 완료.IN
    execute 완료
if 품질검사 = false
    go OUT to 재작업.IN
    execute 재작업
```

### 블록 상태 동작 예시
```
시간 0: 투입 블록 실행 시작 (Running)
시간 1: 투입 블록이 "execute 공정1" 실행
        → 공정1이 Idle 상태이므로 실행 시작 (공정1: Running)
시간 2: 투입 블록 실행 완료 (투입: Idle)
시간 6: 공정1 블록이 "execute 공정2" 실행
        → 공정2가 Idle 상태이므로 실행 시작 (공정2: Running)
시간 7: 공정1 블록 실행 완료 (공정1: Idle)
        → 이제 다른 블록에서 공정1 실행 가능
시간 10: 공정2 블록 실행 완료 (공정2: Idle)
```

이 방식으로 블록의 동시 실행을 방지하면서도 재사용이 가능합니다.
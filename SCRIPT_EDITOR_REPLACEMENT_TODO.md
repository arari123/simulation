# 스크립트 편집기 전면 교체 프로젝트

## 📋 프로젝트 개요

### 목표
현재 스크립트 편집기의 검증 오류 문제를 근본적으로 해결하고, 명령어 자동완성 기능이 포함된 고급 스크립트 편집 환경을 구축

### 배경
- 현재 ScriptValidator.js의 복잡한 검증 로직에서 계속적인 버그 발생
- 들여쓰기, 특수문자, 복합 조건 처리에서 예상치 못한 문제들
- 여러 패치로 인한 코드 복잡도 증가로 유지보수성 저하

### 예상 기간
**3-4일 (전담 작업 기준)**

## 🔍 현재 상태 분석

### 기존 시스템의 문제점
1. **검증 로직 복잡성**
   - 수동 파싱으로 인한 오류 발생
   - 들여쓰기, 공백, 특수문자 처리 불안정
   - AND/OR 조건, 복합 명령어에서 파싱 오류

2. **사용자 경험 부족**
   - 실시간 문법 검사 부재
   - 자동완성 기능 없음
   - 구문 하이라이팅 제한적

3. **확장성 제약**
   - 새로운 명령어 추가 시마다 검증 로직 수정 필요
   - 복잡한 조건문 지원 어려움
   - 코드 편집 기능 제한적

### 기존 코드 현황
```
frontend/src/components/script/ScriptValidator.js (390라인)
frontend/src/components/shared/ScriptEditor.vue
frontend/src/utils/ScriptUtils.js
```

## 🎯 요구사항 정의

### 1. 필수 요구사항 (Phase 1)
- **기본 편집 기능**: 멀티라인 텍스트 편집, 들여쓰기 자동 처리
- **실시간 문법 검사**: 타이핑하면서 즉시 오류 표시
- **구문 하이라이팅**: 명령어, 신호명, 블록명 색상 구분
- **기존 호환성**: 현재 스크립트 구문 100% 지원

### 2. 고급 요구사항 (Phase 2)
- **자동완성**: 명령어, 블록명, 신호명 자동완성
- **스니펫**: 자주 사용하는 패턴 빠른 입력
- **에러 위치 표시**: 정확한 라인/컬럼 오류 위치
- **코드 포맷팅**: 자동 들여쓰기 정리

### 3. 최적화 요구사항 (Phase 3)
- **인텔리센스**: 컨텍스트 기반 제안
- **리팩토링 도구**: 블록명 일괄 변경 등
- **실행 미리보기**: 스크립트 실행 흐름 시각화

## 🛠 기술 스택 선택

### CodeMirror 6 채택 이유
1. **최신 기술**: 2021년 출시, 현대적 아키텍처
2. **높은 성능**: 가상 스크롤링, 효율적 렌더링
3. **확장성**: 플러그인 시스템으로 기능 추가 용이
4. **Vue 3 호환성**: 공식 Vue 바인딩 제공
5. **커뮤니티**: 활발한 개발, 풍부한 문서

### 대안 기술 비교
| 기술 | 장점 | 단점 | 점수 |
|------|------|------|------|
| **CodeMirror 6** | 최신, 성능, 확장성 | 학습곡선 | ⭐⭐⭐⭐⭐ |
| Monaco Editor | VS Code 기반, 기능 풍부 | 무거움, 복잡 | ⭐⭐⭐⭐ |
| Ace Editor | 가벼움, 안정성 | 구식, 제한적 | ⭐⭐⭐ |
| 자체 구현 | 완전 제어 | 개발 시간 과다 | ⭐⭐ |

## 📋 상세 구현 계획

### Phase 1: 기본 편집기 교체 (1-2일)

#### 1.1 환경 설정 및 의존성 추가
```bash
# CodeMirror 6 설치
npm install @codemirror/state @codemirror/view @codemirror/commands
npm install @codemirror/language @codemirror/autocomplete
npm install @codemirror/lint @codemirror/search
```

#### 1.2 새 편집기 컴포넌트 생성
**파일**: `frontend/src/components/script/ScriptEditorV2.vue`

**주요 기능**:
- CodeMirror 6 기본 설정
- 테마 적용 (다크/라이트 모드 지원)
- 기본 키바인딩 (Ctrl+Z, Ctrl+Y, Tab 등)
- 라인 번호 표시
- 코드 폴딩 지원

**구현 우선순위**:
1. ✅ 기본 에디터 마운트
2. ✅ 텍스트 입력/출력 바인딩
3. ✅ 스타일링 적용
4. ✅ 이벤트 핸들링 (onChange, onBlur)

#### 1.3 기존 컴포넌트와 연동
**수정 파일**: 
- `frontend/src/components/shared/SettingsBase.vue`
- `frontend/src/components/BlockSettingsPopup.vue`
- `frontend/src/components/ConnectorSettingsPopup.vue`

**연동 작업**:
1. ScriptEditor → ScriptEditorV2 교체
2. props 인터페이스 유지
3. emit 이벤트 호환성 확보
4. 기존 스크립트 로딩/저장 테스트

### Phase 2: 문법 검사 및 하이라이팅 (1일)

#### 2.1 커스텀 언어 정의
**파일**: `frontend/src/components/script/SimulationScriptLanguage.js`

```javascript
// 언어 정의 예시
const SimulationScriptLanguage = {
  keywords: ['delay', 'wait', 'if', 'go', 'to', 'from', 'jump', 'log', 'product', 'type'],
  operators: ['=', '+=', '-=', 'and', 'or'],
  signals: [], // 동적으로 로드
  blocks: []   // 동적으로 로드
}
```

**하이라이팅 규칙**:
- **명령어**: 파란색 (`delay`, `wait`, `if`, `go`)
- **신호명**: 초록색 (동적 목록에서)
- **블록명**: 주황색 (동적 목록에서)
- **연산자**: 빨간색 (`=`, `and`, `or`)
- **숫자**: 보라색
- **문자열**: 갈색
- **주석**: 회색

#### 2.2 실시간 문법 검사
**파일**: `frontend/src/components/script/ScriptLinter.js`

**검사 규칙**:
1. **구문 오류**: 잘못된 명령어, 누락된 매개변수
2. **참조 오류**: 존재하지 않는 신호명, 블록명
3. **로직 오류**: 무한 루프 가능성, 도달 불가능한 코드
4. **스타일 가이드**: 일관되지 않은 들여쓰기

**오류 표시 방식**:
- 🔴 **Error**: 빨간 밑줄, 실행 불가
- 🟡 **Warning**: 노란 밑줄, 실행 가능하지만 주의
- 🔵 **Info**: 파란 밑줄, 개선 제안

#### 2.3 백엔드 연동 검증
**기존 검증 로직 마이그레이션**:
1. `ScriptValidator.js` 로직을 CodeMirror linter로 이식
2. 실시간 검증과 저장 시 검증 분리
3. 성능 최적화 (디바운싱 적용)

### Phase 3: 자동완성 시스템 (1일)

#### 3.1 컨텍스트 분석기
**파일**: `frontend/src/components/script/CompletionProvider.js`

**분석 대상**:
- 현재 커서 위치의 문맥
- 이전 명령어와 매개변수
- 사용 가능한 신호/블록 목록
- 들여쓰기 레벨 (if 블록 내부 등)

#### 3.2 자동완성 제공자
**제공 항목**:
1. **명령어 완성**
   ```
   de → delay [시간]
   wa → wait [조건]
   if → if [조건]
   go → go from [커넥터] to [대상]
   ```

2. **매개변수 완성**
   ```
   wait → 신호명 목록
   go to → 블록명.커넥터명 목록
   if → 조건 템플릿
   ```

3. **스니펫 완성**
   ```
   wait-if → wait [신호] = true\nif [신호] = true\n    [액션]
   parallel → if [조건1]\n    [액션1]\nif [조건2]\n    [액션2]
   ```

#### 3.3 동적 데이터 연동
**실시간 업데이트**:
- 신호 목록 변경 시 자동완성 갱신
- 블록/커넥터 추가/삭제 시 즉시 반영
- 다른 블록 스크립트 변경 시 참조 업데이트

### Phase 4: 고급 기능 및 최적화 (추가 시간)

#### 4.1 키보드 단축키
```
Ctrl + Space: 자동완성 강제 호출
Ctrl + /: 주석 토글
Tab/Shift+Tab: 들여쓰기 조정
Ctrl + D: 현재 라인 복제
Ctrl + Shift + K: 현재 라인 삭제
```

#### 4.2 편집 도우미
- **브래킷 매칭**: 따옴표, 괄호 자동 완성
- **자동 들여쓰기**: if 문 내부 자동 들여쓰기
- **스마트 선택**: 단어, 라인, 블록 단위 선택

#### 4.3 접근성 개선
- **키보드 네비게이션**: 마우스 없이 완전 조작 가능
- **스크린 리더**: 시각 장애인을 위한 접근성
- **고대비 모드**: 색상 구분이 어려운 사용자 지원

## 🚨 리스크 관리

### 주요 리스크와 대응책

#### 1. 호환성 문제 (중위험)
**리스크**: 기존 스크립트 구문이 새 편집기에서 작동하지 않을 가능성
**대응책**: 
- 기존 스크립트 파일들로 철저한 호환성 테스트
- 기존 검증 로직을 참조 구현으로 활용
- 단계적 롤아웃으로 문제 조기 발견

#### 2. 성능 저하 (저위험)
**리스크**: 새 편집기가 기존보다 느릴 가능성
**대응책**:
- CodeMirror 6의 가상 스크롤링 활용
- 디바운싱으로 실시간 검증 최적화
- 메모리 누수 방지를 위한 적절한 cleanup

#### 3. 사용자 적응 (중위험)
**리스크**: 새로운 인터페이스에 사용자가 적응하지 못할 가능성
**대응책**:
- 기존 UI/UX 최대한 유지
- 점진적 기능 도입 (자동완성 등은 옵션으로)
- 충분한 문서화 및 도움말 제공

#### 4. 개발 지연 (고위험)
**리스크**: 예상보다 복잡하여 개발 기간 초과 가능성
**대응책**:
- 단계별 구현으로 점진적 개선
- MVP(최소 기능 제품) 우선 구현
- 롤백 계획 수립

## ✅ 테스트 계획

### 1. 단위 테스트
**대상**: 각 기능별 모듈
- 언어 정의 모듈
- 자동완성 제공자
- 문법 검사기
- 컨텍스트 분석기

### 2. 통합 테스트
**대상**: 편집기 전체 기능
- 스크립트 입력/수정/저장 플로우
- 실시간 검증 및 오류 표시
- 자동완성 동작
- 백엔드 연동

### 3. 회귀 테스트
**대상**: 기존 기능 보장
- 모든 기존 테스트 JSON 파일로 검증
- 스크립트 저장/로드 기능
- 블록/커넥터 설정 연동

### 4. 사용자 테스트
**대상**: 실제 사용 시나리오
- 복잡한 스크립트 작성
- 오류 수정 프로세스
- 자동완성 유용성
- 전반적 사용성

## 📦 배포 계획

### 1. 개발 브랜치 전략
```
main (현재 안정 버전)
├── feature/script-editor-v2 (새 편집기 개발)
│   ├── phase1-basic-editor
│   ├── phase2-syntax-highlighting
│   ├── phase3-autocomplete
│   └── phase4-advanced-features
└── hotfix/* (긴급 수정사항)
```

### 2. 단계별 배포
**Phase 1**: 개발 환경에서 기본 기능 테스트
**Phase 2**: 스테이징 환경에서 통합 테스트
**Phase 3**: 프로덕션 환경에 점진적 롤아웃
**Phase 4**: 전체 사용자에게 배포

### 3. 롤백 계획
- 기존 ScriptEditor.vue는 ScriptEditorLegacy.vue로 보존
- 환경 변수로 편집기 버전 선택 가능
- 심각한 문제 발생 시 즉시 이전 버전으로 복구

## 📊 성공 지표

### 정량적 지표
1. **오류 감소**: 스크립트 검증 오류 90% 이상 감소
2. **개발 속도**: 스크립트 작성 시간 50% 단축
3. **성능**: 편집기 반응 속도 100ms 이하 유지
4. **호환성**: 기존 스크립트 100% 호환

### 정성적 지표
1. **사용자 만족도**: 편집 경험 개선
2. **개발자 경험**: 유지보수성 향상
3. **확장성**: 새 기능 추가 용이성
4. **안정성**: 예상치 못한 오류 최소화

## 📝 구현 체크리스트

### Phase 1: 기본 편집기 (필수)
- [ ] CodeMirror 6 의존성 설치
- [ ] ScriptEditorV2.vue 컴포넌트 생성
- [ ] 기본 편집 기능 구현
- [ ] 기존 컴포넌트와 연동
- [ ] 기본 테스트 통과

### Phase 2: 문법 검사 (필수)
- [ ] SimulationScriptLanguage.js 언어 정의
- [ ] 구문 하이라이팅 구현
- [ ] ScriptLinter.js 실시간 검증
- [ ] 오류 표시 UI 구현
- [ ] 기존 검증 로직 마이그레이션

### Phase 3: 자동완성 (중요)
- [ ] CompletionProvider.js 구현
- [ ] 컨텍스트 분석기 개발
- [ ] 동적 데이터 연동
- [ ] 스니펫 시스템 구현
- [ ] 자동완성 UI 최적화

### Phase 4: 고급 기능 (선택)
- [ ] 키보드 단축키 구현
- [ ] 편집 도우미 기능
- [ ] 접근성 개선
- [ ] 성능 최적화
- [ ] 고급 테스트 추가

### 배포 및 마무리
- [ ] 전체 테스트 통과
- [ ] 문서 업데이트
- [ ] 사용자 가이드 작성
- [ ] 프로덕션 배포
- [ ] 모니터링 설정

## 🔄 마이그레이션 전략

### 기존 코드 처리
1. **보존**: `ScriptEditor.vue` → `ScriptEditorLegacy.vue`
2. **점진적 교체**: 컴포넌트별로 하나씩 새 편집기로 교체
3. **A/B 테스트**: 사용자별로 다른 버전 제공하여 비교

### 데이터 마이그레이션
1. **스크립트 호환성**: 기존 스크립트 구문 100% 지원
2. **설정 이전**: 사용자별 편집기 설정 이전
3. **캐시 정리**: 기존 캐시 데이터 정리

## 📚 참고 자료

### 기술 문서
- [CodeMirror 6 공식 문서](https://codemirror.net/docs/)
- [Vue 3 + CodeMirror 통합 가이드](https://github.com/surmon-china/vedit)
- [언어 서버 프로토콜 참고](https://microsoft.github.io/language-server-protocol/)

### 유사 프로젝트
- VS Code Monaco Editor
- GitHub Codespaces
- Repl.it 편집기
- CodePen 편집기

---

**작성일**: 2025-06-06  
**작성자**: Claude Code  
**검토 필요**: 기술적 세부사항, 일정 조정  
**우선순위**: 🔥 최고 (현재 스크립트 편집기 문제 해결 필요)
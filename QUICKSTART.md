# 🚀 Manufacturing Simulation - Quick Start Guide

> **고성능 제조 공정 시뮬레이션 - 자동화된 Git 기반 개발 환경**

## ⚡ 1분 빠른 시작

### 🔧 Git 저장소 설정 (최초 1회)
```bash
# Git 저장소 자동 초기화 및 설정
./scripts/setup-git.sh https://github.com/your-username/simulation.git

# 또는 로컬 저장소만 초기화
./scripts/setup-git.sh
```

### 🚀 개발 서버 시작
```bash
# 자동 의존성 설치 + Git 동기화 + 서버 시작
./scripts/dev-start.sh
```

**서버 접속:**
- 🌐 **웹 인터페이스**: http://localhost:5173
- 🔧 **API 서버**: http://localhost:8000
- 📚 **API 문서**: http://localhost:8000/docs

### 📝 개발 중 자동 커밋
```bash
# 변경사항 자동 분석 및 커밋/푸시
./scripts/auto-commit.sh

# 또는 직접 메시지 지정
./scripts/auto-commit.sh "feat: add new visualization feature"
```

### 🛑 서버 중지
```bash
./scripts/dev-stop.sh
```

## 🔄 자동화된 개발 워크플로우

### 일반적인 개발 세션
```bash
# 1. 아침에 프로젝트 시작
./scripts/dev-start.sh

# 2. 개발 작업...
#    - 프론트엔드: http://localhost:5173
#    - 백엔드 수정 시 자동 리로드
#    - 실시간 성능 모니터링

# 3. 변경사항 커밋 (수시로)
./scripts/auto-commit.sh

# 4. 하루 마무리
./scripts/dev-stop.sh
```

### 연속 배포 (선택적)
```bash
# 파일 변경 감지 시 자동 커밋/푸시 (30초마다 체크)
./scripts/auto-deploy.sh 30
```

## 🏗️ 프로덕션 배포

### 완전 자동화된 빌드
```bash
# 성능 테스트 + 빌드 + Docker 패키지 + Git 태깅
./scripts/build.sh
```

**결과물:**
- `deploy-YYYYMMDD-HHMMSS.tar.gz` - 배포 패키지
- `DEPLOY.md` - 배포 가이드
- Docker 파일들 포함
- Git 태그 자동 생성

## 📊 성능 특징

- **백엔드**: 22,000+ 시뮬레이션 스텝/초
- **프론트엔드**: Vue 3 + Composition API
- **실시간**: 엔티티 이동 추적 및 신호 상태 동기화
- **자동화**: 완전 자동화된 Git 워크플로우

## 🔧 주요 기능

### 시뮬레이션 특징
- ✅ 드래그 앤 드롭 블록 설계
- ✅ 실시간 엔티티 추적 (Transit 상태 포함)
- ✅ 전역 신호 관리 시스템
- ✅ 수량/시간 기반 실행 제어
- ✅ 성능 모니터링 내장

### 개발 자동화
- ✅ Git 저장소 자동 설정
- ✅ 의존성 자동 관리
- ✅ 지능형 커밋 메시지 생성
- ✅ 원격 저장소 동기화
- ✅ 성능 테스트 통합 빌드
- ✅ Docker 배포 패키지 자동 생성

## 🚨 문제 해결

### 서버 포트 충돌
```bash
# 모든 관련 프로세스 정리
./scripts/dev-stop.sh

# 강제 포트 정리
pkill -f "app.main:app"
pkill -f "vite"
```

### Git 동기화 문제
```bash
# Git 상태 재설정
git status
git pull origin main

# 또는 완전 재설정
./scripts/setup-git.sh
```

### 의존성 문제
```bash
# 백엔드 가상환경 재생성
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 프론트엔드 의존성 재설치
cd frontend
rm -rf node_modules
npm install
```

## 📁 프로젝트 구조

```
simulation/
├── scripts/                   # 🤖 자동화 스크립트
│   ├── setup-git.sh          # Git 초기 설정
│   ├── dev-start.sh          # 개발 서버 시작
│   ├── dev-stop.sh           # 서버 중지
│   ├── auto-commit.sh        # 자동 커밋
│   ├── auto-deploy.sh        # 연속 배포
│   └── build.sh              # 프로덕션 빌드
├── frontend/                  # 🌐 Vue.js 3 프론트엔드
├── backend/                   # 🔧 FastAPI 백엔드  
├── base.json                  # ⚙️ 기본 시뮬레이션 설정
├── CLAUDE.md                  # 📖 개발 가이드
└── QUICKSTART.md             # 🚀 이 파일
```

## 🎯 다음 단계

1. **개발 환경 설정**: `./scripts/dev-start.sh`
2. **기본 시뮬레이션 실행**: 웹 인터페이스에서 "전체 실행" 버튼
3. **블록 추가**: "공정 블록 추가" 버튼으로 새 블록 생성
4. **커넥터 설정**: 블록 클릭 후 연결점 설정
5. **신호 관리**: "전역 신호 패널" 에서 신호 생성 및 관리

## 📞 지원

- **문서**: `CLAUDE.md` - 상세한 아키텍처 및 개발 가이드
- **API 문서**: http://localhost:8000/docs (서버 실행 시)
- **성능 테스트**: `python backend/test_performance_and_ui.py`

---

**🎉 Happy Coding!** 

자동화된 Git 워크플로우로 더 생산적인 개발을 경험하세요! 🚀
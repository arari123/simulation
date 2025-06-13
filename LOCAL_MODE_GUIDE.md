# 로컬/웹 호스팅 모드 가이드

## 개요
시뮬레이션 프로젝트는 이제 로컬 개발 모드와 웹 호스팅(프로덕션) 모드를 구분하여 실행할 수 있습니다.

## 로컬 개발 모드

### 1. 자동 시작 방법
```bash
./start-local.sh
```
이 스크립트는 백엔드와 프론트엔드를 모두 자동으로 시작합니다.

### 2. 수동 시작 방법

**백엔드:**
```bash
cd backend
source venv/bin/activate
export ENVIRONMENT=development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**프론트엔드:**
```bash
cd frontend
npm run dev
```

### 3. 로컬 접속 URL
- 프론트엔드: http://localhost:5173
- 백엔드 API: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 웹 호스팅 모드 (프로덕션)

### 1. 배포 방법
```bash
./scripts/deploy-all.sh
```

### 2. 프로덕션 URL
- 프론트엔드: https://arari123-74173.web.app
- 백엔드 API: https://simulation-backend-573697627177.asia-northeast3.run.app

## 환경 설정 파일

### 프론트엔드
- `frontend/.env.development`: 로컬 개발 환경 설정
- `frontend/.env.production`: 프로덕션 환경 설정

### 백엔드
- `backend/.env.development`: 로컬 개발 환경 설정
- `backend/.env.production`: 프로덕션 환경 설정

## 주요 차이점

| 항목 | 로컬 모드 | 웹 호스팅 모드 |
|------|-----------|----------------|
| 환경 | development | production |
| 디버그 | 활성화 | 비활성화 |
| CORS | localhost 허용 | Firebase 도메인만 허용 |
| 포트 | 8000 (백엔드) | 8080 (Cloud Run) |
| API URL | http://localhost:8000 | https://simulation-backend-*.run.app |

## 문제 해결

### 로컬에서 CORS 오류 발생 시
백엔드 `.env.development` 파일에서 `ALLOWED_ORIGINS`에 프론트엔드 URL을 추가하세요.

### 환경 변수가 적용되지 않을 때
1. 터미널을 재시작하거나
2. `source backend/venv/bin/activate` 실행 후 다시 시도하세요.
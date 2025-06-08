# Deployment Guide

이 가이드는 시뮬레이션 플랫폼을 Firebase Hosting (프론트엔드)과 Google Cloud Run (백엔드)에 배포하는 방법을 설명합니다.

## 📋 사전 요구사항

### 필수 도구 설치
```bash
# Node.js (18 이상)
node --version

# Firebase CLI
npm install -g firebase-tools

# Google Cloud CLI
# https://cloud.google.com/sdk/docs/install 참조

# Docker
docker --version
```

### 계정 및 프로젝트 설정
1. **Google Cloud Project** 생성
   - https://console.cloud.google.com/
   - 새 프로젝트 생성 또는 기존 프로젝트 선택
   - 프로젝트 ID 기록

2. **Firebase Project** 생성
   - https://console.firebase.google.com/
   - 새 프로젝트 생성 (Google Cloud 프로젝트 연결 권장)
   - 프로젝트 ID 기록

## 🔧 환경 설정

### 1. 환경 변수 설정

#### 백엔드 환경 변수
```bash
cd backend
cp .env.example .env
```

`.env` 파일 편집:
```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
PORT=8080
LOG_LEVEL=INFO

# CORS settings (프론트엔드 URL로 변경)
ALLOWED_ORIGINS=https://your-project-id.web.app,https://your-custom-domain.com
```

#### 프론트엔드 환경 변수
```bash
cd frontend
cp .env.example .env.production
```

`.env.production` 파일 편집:
```bash
# Backend API URL (Cloud Run 배포 후 업데이트)
VITE_API_BASE_URL=https://simulation-backend-your-hash.a.run.app
VITE_ENVIRONMENT=production
```

### 2. 배포 설정 파일 수정

`deployment-config.yaml` 파일에서 프로젝트 정보 업데이트:
```yaml
google_cloud:
  project_id: "your-actual-project-id"
  
firebase:
  project_id: "your-actual-firebase-project-id"
```

## 🚀 배포 프로세스

### 1단계: 백엔드 배포 (Cloud Run)

```bash
# 환경 변수 설정
export GOOGLE_CLOUD_PROJECT_ID="your-project-id"
export GOOGLE_CLOUD_REGION="asia-northeast3"
export CLOUD_RUN_SERVICE_NAME="simulation-backend"

# 배포 실행
./scripts/deploy-backend.sh
```

배포가 완료되면 서비스 URL이 출력됩니다:
```
✅ Deployment completed successfully!
🌐 Service URL: https://simulation-backend-abc123.a.run.app
```

### 2단계: 프론트엔드 환경 변수 업데이트

백엔드 URL을 받아서 프론트엔드 환경 변수 업데이트:
```bash
cd frontend
echo "VITE_API_BASE_URL=https://simulation-backend-abc123.a.run.app" > .env.production
echo "VITE_ENVIRONMENT=production" >> .env.production
```

### 3단계: 프론트엔드 배포 (Firebase Hosting)

```bash
# 환경 변수 설정
export FIREBASE_PROJECT_ID="your-firebase-project-id"
export BACKEND_URL="https://simulation-backend-abc123.a.run.app"

# 배포 실행
./scripts/deploy-frontend.sh
```

## 🔍 배포 확인

### 백엔드 상태 확인
```bash
# Health check
curl https://your-backend-url/health

# API 문서 확인
open https://your-backend-url/docs
```

### 프론트엔드 접속 확인
```bash
# 브라우저에서 접속
open https://your-project-id.web.app
```

## 🛠️ 유지보수

### 로그 확인

#### Cloud Run 로그
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=simulation-backend" --limit 50
```

#### Firebase Hosting 로그
```bash
firebase hosting:clone
```

### 환경 변수 업데이트

#### Cloud Run 환경 변수 변경
```bash
gcloud run services update simulation-backend \
  --region=asia-northeast3 \
  --set-env-vars "NEW_VAR=value"
```

### 재배포

#### 백엔드만 재배포
```bash
./scripts/deploy-backend.sh
```

#### 프론트엔드만 재배포
```bash
./scripts/deploy-frontend.sh
```

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. CORS 오류
- 백엔드 환경 변수에서 `ALLOWED_ORIGINS`에 프론트엔드 도메인 추가
- Cloud Run 서비스 재배포

#### 2. API 연결 실패
- 프론트엔드 `VITE_API_BASE_URL` 확인
- 백엔드 헬스체크 확인: `curl https://your-backend-url/health`

#### 3. 빌드 실패
- Docker 이미지 빌드 확인
- 의존성 설치 확인

#### 4. 권한 문제
```bash
# Google Cloud 인증 확인
gcloud auth list

# Firebase 인증 확인
firebase login:list
```

### 로그 디버깅

#### 상세 Cloud Run 로그
```bash
gcloud logging read "resource.type=cloud_run_revision" \
  --filter="resource.labels.service_name=simulation-backend" \
  --format="table(timestamp,textPayload)" \
  --limit=100
```

#### 실시간 로그 모니터링
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=simulation-backend"
```

## 📊 모니터링 설정

### Cloud Monitoring 대시보드
1. Google Cloud Console > Monitoring 이동
2. Dashboards > Create Dashboard
3. Cloud Run 메트릭 추가:
   - Request count
   - Request latency
   - Error rate
   - Memory usage

### 알림 설정
```bash
# 오류율 알림 생성 예시
gcloud alpha monitoring policies create \
  --policy-from-file=monitoring-policy.yaml
```

## 🔄 CI/CD 설정 (선택사항)

### GitHub Actions 워크플로우 예시

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - id: 'auth'
        uses: 'google-github-actions/auth@v1'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      - name: Deploy to Cloud Run
        run: ./scripts/deploy-backend.sh

  deploy-frontend:
    needs: deploy-backend
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Firebase
        run: ./scripts/deploy-frontend.sh
```

## 📝 배포 체크리스트

### 배포 전 확인사항
- [ ] 환경 변수 설정 완료
- [ ] 프로젝트 ID 설정 확인
- [ ] Google Cloud 및 Firebase 인증 완료
- [ ] 로컬 테스트 완료

### 배포 후 확인사항
- [ ] 백엔드 헬스체크 통과
- [ ] 프론트엔드 접속 확인
- [ ] API 연동 테스트
- [ ] 로그 모니터링 설정
- [ ] 도메인 설정 (필요시)

## 💡 팁과 권장사항

1. **Security**: 프로덕션에서는 CORS 설정을 특정 도메인으로 제한
2. **Performance**: Cloud Run 최소 인스턴스 수 조정으로 콜드 스타트 최소화
3. **Cost**: 개발 환경에서는 최소 인스턴스를 0으로 설정
4. **Monitoring**: 정기적인 로그 확인 및 성능 모니터링
5. **Backup**: 중요한 설정 파일은 버전 관리에 포함

---

추가 질문이나 문제가 있으면 프로젝트 이슈 트래커에 문의하세요.
# GitHub Pages 배포 가이드

이 문서는 시뮬레이션 프론트엔드를 GitHub Pages에 배포하는 방법을 설명합니다.

## 배포 설정 완료 사항

### 1. Vite 설정 업데이트
- `/frontend/vite.config.js`에 GitHub Pages용 base URL 설정 추가
- 프로덕션 빌드 시 `/simulation/` 경로 사용

### 2. 환경변수 설정
- `/frontend/.env`: 개발 환경용 (localhost:8000)
- `/frontend/.env.production`: 프로덕션 환경용 (빈 API URL)

### 3. GitHub Actions 워크플로우
- `/.github/workflows/deploy.yml`: 자동 배포 워크플로우
- main 브랜치에 push 시 자동으로 GitHub Pages 배포

### 4. 패키지 스크립트
- `npm run build:gh-pages`: GitHub Pages용 빌드
- `npm run deploy`: 로컬에서 수동 배포 (gh-pages 패키지 사용)

## 배포 방법

### 자동 배포 (권장)
1. GitHub 저장소 설정에서 Pages 활성화
2. Source를 "GitHub Actions"로 설정
3. main 브랜치에 코드 push
4. GitHub Actions가 자동으로 빌드 및 배포

### 수동 배포
```bash
cd frontend
npm install
npm run deploy
```

## GitHub Pages 설정

1. GitHub 저장소 → Settings → Pages
2. Source: "Deploy from a branch" → "GitHub Actions" 선택
3. 배포 완료 후 URL: `https://{username}.github.io/simulation/`

## 중요 사항

### 백엔드 API 제한
- GitHub Pages는 정적 호스팅만 지원
- 백엔드 API가 없으므로 시뮬레이션 실행 기능은 제한됨
- 프론트엔드 UI 및 설정 기능만 확인 가능

### 개발 vs 프로덕션
- 개발: `http://localhost:5173` (백엔드 API 연동)
- 프로덕션: GitHub Pages (정적 사이트, API 없음)

### API 연동이 필요한 경우
백엔드 API와 연동하려면 다음 옵션을 고려:
1. Vercel, Netlify 등 서버리스 배포
2. Heroku, Railway 등 풀스택 배포
3. 백엔드를 별도 서버에 배포 후 CORS 설정

## 배포 URL 예시
```
https://yourusername.github.io/simulation/
```

## 문제 해결

### 빌드 실패
- `npm ci` 대신 `npm install` 사용
- Node.js 버전 호환성 확인 (18+)

### 페이지가 표시되지 않음
- base URL 설정 확인 (`/simulation/`)
- GitHub Pages 설정에서 Source가 "GitHub Actions"인지 확인

### API 요청 실패
- 정상적인 동작임 (정적 호스팅에서는 백엔드 API 사용 불가)
- 개발 환경에서 테스트 필요
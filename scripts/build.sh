#!/bin/bash

# 프로덕션 빌드 및 배포 스크립트
# 사용법: ./scripts/build.sh

set -e

# 색상 출력 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}🏗️  Manufacturing Simulation - Production Build${NC}"
echo "=================================================="

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${CYAN}📁 Project root: $PROJECT_ROOT${NC}"

# Git 상태 확인
echo -e "${BLUE}🔍 Git 상태 확인 중...${NC}"
if [ -d ".git" ]; then
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo -e "${YELLOW}⚠️  커밋되지 않은 변경사항이 있습니다.${NC}"
        read -p "빌드 전에 변경사항을 커밋하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            AUTO_CONFIRM=1 ./scripts/auto-commit.sh "build: Pre-production build commit"
        fi
    fi
    
    # 현재 브랜치와 커밋 정보
    CURRENT_BRANCH=$(git branch --show-current)
    CURRENT_COMMIT=$(git rev-parse --short HEAD)
    echo -e "${CYAN}🌿 Branch: ${CURRENT_BRANCH}${NC}"
    echo -e "${CYAN}📝 Commit: ${CURRENT_COMMIT}${NC}"
fi

# 성능 테스트 실행
echo -e "${BLUE}🧪 성능 테스트 실행 중...${NC}"
cd "$PROJECT_ROOT/backend"

# 백엔드 테스트 서버 시작
if ! curl -s http://localhost:8000/docs > /dev/null; then
    echo -e "${YELLOW}⚠️  백엔드 서버가 실행되지 않았습니다. 임시 시작...${NC}"
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt --quiet
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > build-test.log 2>&1 &
    BUILD_TEST_PID=$!
    
    # 서버 시작 대기
    for i in {1..10}; do
        if curl -s http://localhost:8000/docs > /dev/null; then
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
fi

# 성능 테스트 실행
echo -e "${CYAN}📊 성능 검증 중...${NC}"
if python3 test_performance_and_ui.py | grep -q "🎉 ALL TESTS PASSED"; then
    echo -e "${GREEN}✅ 성능 테스트 통과${NC}"
else
    echo -e "${RED}❌ 성능 테스트 실패${NC}"
    echo "빌드를 계속하시겠습니까? (y/N): "
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 임시 테스트 서버 정리
if [ ! -z "$BUILD_TEST_PID" ]; then
    kill $BUILD_TEST_PID 2>/dev/null || true
    rm -f build-test.log
fi

# 프론트엔드 빌드
echo -e "${BLUE}🌐 프론트엔드 빌드 중...${NC}"
cd "$PROJECT_ROOT/frontend"

# 의존성 설치
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 의존성 설치 중...${NC}"
    npm install
fi

# 빌드 실행
echo -e "${CYAN}🔨 Vite 빌드 실행 중...${NC}"
npm run build

if [ -d "dist" ]; then
    BUILD_SIZE=$(du -sh dist | cut -f1)
    echo -e "${GREEN}✅ 프론트엔드 빌드 완료 (크기: ${BUILD_SIZE})${NC}"
else
    echo -e "${RED}❌ 프론트엔드 빌드 실패${NC}"
    exit 1
fi

# 빌드 결과 정보
echo -e "${BLUE}📋 빌드 결과 분석 중...${NC}"
cd dist

# 주요 파일들 크기 확인
echo -e "${CYAN}📁 빌드 파일 구조:${NC}"
find . -name "*.js" -o -name "*.css" -o -name "*.html" | head -10 | while read file; do
    SIZE=$(du -sh "$file" | cut -f1)
    echo -e "  ${file}: ${SIZE}"
done

# 백엔드 배포 준비
echo -e "${BLUE}🔧 백엔드 배포 준비 중...${NC}"
cd "$PROJECT_ROOT/backend"

# requirements.txt 업데이트 확인
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    pip freeze > requirements-freeze.txt
    echo -e "${GREEN}✅ 의존성 목록이 업데이트되었습니다.${NC}"
fi

# 배포 패키지 생성
echo -e "${BLUE}📦 배포 패키지 생성 중...${NC}"
cd "$PROJECT_ROOT"

# 배포 디렉토리 생성
DEPLOY_DIR="deploy-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEPLOY_DIR"

# 필요한 파일들 복사
echo -e "${CYAN}📋 파일 복사 중...${NC}"
cp -r backend "$DEPLOY_DIR/"
cp -r frontend/dist "$DEPLOY_DIR/frontend"
cp base.json "$DEPLOY_DIR/" 2>/dev/null || true
cp CLAUDE.md "$DEPLOY_DIR/" 2>/dev/null || true

# 배포용 Docker 파일 생성
cat > "$DEPLOY_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 백엔드 의존성 설치
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# 백엔드 코드 복사
COPY backend/ ./backend/
COPY base.json .

# 프론트엔드 빌드 결과 복사
COPY frontend/ ./frontend/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# docker-compose.yml 생성
cat > "$DEPLOY_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  simulation:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./base.json:/app/base.json
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
EOF

# 배포 가이드 생성
cat > "$DEPLOY_DIR/DEPLOY.md" << EOF
# Manufacturing Simulation - 배포 가이드

## 배포 정보
- 빌드 일시: $(date '+%Y-%m-%d %H:%M:%S')
- Git Branch: ${CURRENT_BRANCH:-"N/A"}
- Git Commit: ${CURRENT_COMMIT:-"N/A"}
- 프론트엔드 크기: ${BUILD_SIZE:-"N/A"}

## Docker 배포

\`\`\`bash
# 이미지 빌드
docker-compose build

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
\`\`\`

## 직접 배포

### 백엔드 서버
\`\`\`bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

### 프론트엔드 (Static)
프론트엔드 빌드 결과는 \`frontend/\` 디렉토리에 있습니다.
웹 서버(Nginx, Apache 등)의 document root로 복사하여 사용하세요.

## 접근 URL
- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 웹 인터페이스: 프론트엔드 서버 URL

## 성능 확인
백엔드에서 다음 명령으로 성능을 확인할 수 있습니다:
\`\`\`bash
python test_performance_and_ui.py
\`\`\`
EOF

# 배포 패키지 압축
echo -e "${BLUE}🗜️  배포 패키지 압축 중...${NC}"
tar -czf "${DEPLOY_DIR}.tar.gz" "$DEPLOY_DIR"
PACKAGE_SIZE=$(du -sh "${DEPLOY_DIR}.tar.gz" | cut -f1)

echo ""
echo -e "${GREEN}🎉 빌드 및 배포 준비가 완료되었습니다!${NC}"
echo "=================================================="
echo -e "${CYAN}📦 배포 패키지:${NC} ${DEPLOY_DIR}.tar.gz (${PACKAGE_SIZE})"
echo -e "${CYAN}📁 배포 디렉토리:${NC} ${DEPLOY_DIR}/"
echo -e "${CYAN}📚 배포 가이드:${NC} ${DEPLOY_DIR}/DEPLOY.md"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo -e "1. 배포 패키지 확인: ${CYAN}tar -tzf ${DEPLOY_DIR}.tar.gz${NC}"
echo -e "2. 서버에 업로드: ${CYAN}scp ${DEPLOY_DIR}.tar.gz user@server:/path/${NC}"
echo -e "3. 서버에서 압축 해제: ${CYAN}tar -xzf ${DEPLOY_DIR}.tar.gz${NC}"
echo -e "4. Docker 배포: ${CYAN}cd ${DEPLOY_DIR} && docker-compose up -d${NC}"
echo ""

# Git 태그 생성 제안
if [ -d ".git" ]; then
    echo -e "${BLUE}🏷️  Git 태그 생성${NC}"
    read -p "이 빌드에 대한 태그를 생성하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        TAG_NAME="v$(date +%Y%m%d-%H%M%S)"
        git tag -a "$TAG_NAME" -m "Production build $(date '+%Y-%m-%d %H:%M:%S')

📦 Build Info:
- Frontend size: ${BUILD_SIZE}
- Deploy package: ${DEPLOY_DIR}.tar.gz (${PACKAGE_SIZE})
- Performance tests: Passed

🚀 Generated by automated build script"
        
        if git remote get-url origin &>/dev/null; then
            git push origin "$TAG_NAME"
            echo -e "${GREEN}✅ 태그 '${TAG_NAME}'이 생성되고 푸시되었습니다.${NC}"
        else
            echo -e "${GREEN}✅ 태그 '${TAG_NAME}'이 생성되었습니다.${NC}"
        fi
    fi
fi

echo -e "${MAGENTA}Happy deploying! 🚀${NC}"
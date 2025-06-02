#!/bin/bash

# 개발 서버 자동 시작 스크립트 (Git 통합)
# 사용법: ./scripts/dev-start.sh

set -e

# 색상 출력 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}🚀 Manufacturing Simulation - Development Server${NC}"
echo "=================================================="

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${CYAN}📁 Project root: $PROJECT_ROOT${NC}"

# Git 상태 확인 및 자동 처리
echo -e "${BLUE}🔍 Git 상태 확인 중...${NC}"

if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Git 저장소가 초기화되지 않았습니다.${NC}"
    read -p "Git을 자동으로 설정하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔧 Git 자동 설정 실행 중...${NC}"
        ./scripts/setup-git.sh
    fi
else
    echo -e "${GREEN}✅ Git 저장소가 확인되었습니다.${NC}"
    
    # 변경사항 확인
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo -e "${YELLOW}⚠️  커밋되지 않은 변경사항이 있습니다.${NC}"
        git status --short
        echo ""
        read -p "변경사항을 자동으로 커밋하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            AUTO_CONFIRM=1 ./scripts/auto-commit.sh "dev: Pre-development auto-commit"
        fi
    fi
    
    # 원격 저장소 동기화
    if git remote get-url origin &>/dev/null; then
        echo -e "${BLUE}🔄 원격 저장소 동기화 중...${NC}"
        
        # fetch로 원격 변경사항 확인
        git fetch origin
        
        CURRENT_BRANCH=$(git branch --show-current)
        LOCAL_COMMIT=$(git rev-parse HEAD)
        REMOTE_COMMIT=$(git rev-parse "origin/$CURRENT_BRANCH" 2>/dev/null || echo "")
        
        if [ ! -z "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
            echo -e "${YELLOW}⚠️  원격 저장소에 새로운 변경사항이 있습니다.${NC}"
            read -p "원격 변경사항을 pull하시겠습니까? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git pull origin "$CURRENT_BRANCH"
                echo -e "${GREEN}✅ 원격 변경사항이 적용되었습니다.${NC}"
            fi
        else
            echo -e "${GREEN}✅ 로컬과 원격이 동기화되어 있습니다.${NC}"
        fi
    fi
fi

# 기존 서버 프로세스 정리
echo -e "${BLUE}🧹 기존 서버 프로세스 정리 중...${NC}"
pkill -f "app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# 백엔드 의존성 확인
echo -e "${BLUE}📦 백엔드 의존성 확인 중...${NC}"
cd "$PROJECT_ROOT/backend"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Python 가상환경이 없습니다. 생성 중...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt --quiet

echo -e "${GREEN}✅ 백엔드 준비 완료${NC}"

# 프론트엔드 의존성 확인
echo -e "${BLUE}📦 프론트엔드 의존성 확인 중...${NC}"
cd "$PROJECT_ROOT/frontend"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  Node.js 의존성이 없습니다. 설치 중...${NC}"
    npm install
fi

echo -e "${GREEN}✅ 프론트엔드 준비 완료${NC}"

# 개발 서버 시작
echo ""
echo -e "${MAGENTA}🚀 개발 서버 시작 중...${NC}"
echo "=================================================="

# 백엔드 서버 백그라운드 시작
echo -e "${BLUE}🔧 백엔드 서버 시작 (Port: 8000)${NC}"
cd "$PROJECT_ROOT/backend"
source venv/bin/activate
nohup python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

# 백엔드 시작 대기
echo -e "${CYAN}⏳ 백엔드 서버 초기화 대기 중...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8000/docs > /dev/null; then
        echo -e "${GREEN}✅ 백엔드 서버 준비 완료${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# 프론트엔드 서버 시작
echo -e "${BLUE}🌐 프론트엔드 서버 시작 (Port: 5173)${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

# 서버 정보 출력
echo ""
echo -e "${GREEN}🎉 개발 서버가 시작되었습니다!${NC}"
echo "=================================================="
echo -e "${CYAN}🔧 백엔드 (FastAPI):${NC} http://localhost:8000"
echo -e "${CYAN}📚 API 문서:${NC} http://localhost:8000/docs"
echo -e "${CYAN}🌐 프론트엔드 (Vue.js):${NC} http://localhost:5173"
echo ""
echo -e "${YELLOW}프로세스 ID:${NC}"
echo -e "  Backend PID: ${BACKEND_PID}"
echo -e "  Frontend PID: ${FRONTEND_PID}"
echo ""
echo -e "${BLUE}서버 중지 방법:${NC}"
echo -e "  전체 중지: ${CYAN}./scripts/dev-stop.sh${NC}"
echo -e "  백엔드만: ${CYAN}pkill -f 'app.main:app'${NC}"
echo -e "  프론트엔드만: ${CYAN}pkill -f 'vite'${NC}"
echo ""
echo -e "${BLUE}로그 확인:${NC}"
echo -e "  백엔드: ${CYAN}tail -f backend/backend.log${NC}"
echo -e "  프론트엔드: ${CYAN}프론트엔드 터미널 확인${NC}"
echo ""
echo -e "${MAGENTA}Happy coding! 🚀${NC}"

# 프론트엔드 로그 실시간 표시 (Ctrl+C로 중단 가능)
echo -e "${BLUE}📺 프론트엔드 로그 (Ctrl+C로 백그라운드 실행)${NC}"
echo "=================================================="
wait $FRONTEND_PID
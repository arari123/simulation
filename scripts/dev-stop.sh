#!/bin/bash

# 개발 서버 중지 스크립트
# 사용법: ./scripts/dev-stop.sh

# 색상 출력 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 Development Server Shutdown${NC}"
echo "=================================="

# 백엔드 서버 중지
echo -e "${YELLOW}🔧 백엔드 서버 중지 중...${NC}"
BACKEND_PIDS=$(pgrep -f "app.main:app" || echo "")
if [ ! -z "$BACKEND_PIDS" ]; then
    pkill -f "app.main:app"
    echo -e "${GREEN}✅ 백엔드 서버가 중지되었습니다.${NC}"
else
    echo -e "${YELLOW}⚠️  실행 중인 백엔드 서버가 없습니다.${NC}"
fi

# 프론트엔드 서버 중지
echo -e "${YELLOW}🌐 프론트엔드 서버 중지 중...${NC}"
FRONTEND_PIDS=$(pgrep -f "vite" || echo "")
if [ ! -z "$FRONTEND_PIDS" ]; then
    pkill -f "vite"
    echo -e "${GREEN}✅ 프론트엔드 서버가 중지되었습니다.${NC}"
else
    echo -e "${YELLOW}⚠️  실행 중인 프론트엔드 서버가 없습니다.${NC}"
fi

# 포트 확인
echo -e "${BLUE}🔍 포트 사용 현황 확인...${NC}"
PORT_8000=$(lsof -ti:8000 || echo "")
PORT_5173=$(lsof -ti:5173 || echo "")

if [ ! -z "$PORT_8000" ]; then
    echo -e "${RED}⚠️  포트 8000이 여전히 사용 중입니다. PID: $PORT_8000${NC}"
    echo "강제 종료: kill -9 $PORT_8000"
fi

if [ ! -z "$PORT_5173" ]; then
    echo -e "${RED}⚠️  포트 5173이 여전히 사용 중입니다. PID: $PORT_5173${NC}"
    echo "강제 종료: kill -9 $PORT_5173"
fi

if [ -z "$PORT_8000" ] && [ -z "$PORT_5173" ]; then
    echo -e "${GREEN}✅ 모든 포트가 정리되었습니다.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 개발 서버 중지가 완료되었습니다!${NC}"
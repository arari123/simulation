#!/bin/bash

# 자동 배포 워치 스크립트
# 파일 변경 감지 시 자동으로 커밋하고 푸시하는 스크립트
# 사용법: ./scripts/auto-deploy.sh [watch-interval-seconds]

# 색상 출력 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 기본 설정
WATCH_INTERVAL=${1:-30}  # 기본 30초마다 확인
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

echo -e "${MAGENTA}🔄 Auto Deploy Watcher - Manufacturing Simulation${NC}"
echo "=================================================="
echo -e "${CYAN}📁 Project: $PROJECT_ROOT${NC}"
echo -e "${CYAN}⏰ Check interval: ${WATCH_INTERVAL} seconds${NC}"
echo -e "${CYAN}🛑 Stop: Press Ctrl+C${NC}"
echo ""

cd "$PROJECT_ROOT"

# 워치 중단을 위한 트랩 설정
trap 'echo -e "\n${YELLOW}🛑 Auto deploy watcher stopped${NC}"; exit 0' INT

# Git 저장소 확인
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Git 저장소가 없습니다. setup-git.sh를 먼저 실행하세요.${NC}"
    exit 1
fi

# 이전 커밋 해시 저장
LAST_COMMIT=$(git rev-parse HEAD 2>/dev/null)
WATCH_COUNT=0

echo -e "${GREEN}🚀 Auto deploy watcher started...${NC}"
echo ""

while true; do
    WATCH_COUNT=$((WATCH_COUNT + 1))
    CURRENT_TIME=$(date '+%H:%M:%S')
    
    # 상태 표시 (매 10번째마다)
    if [ $((WATCH_COUNT % 10)) -eq 0 ]; then
        echo -e "${BLUE}⏰ ${CURRENT_TIME} - Watching for changes... (Check #${WATCH_COUNT})${NC}"
    fi
    
    # Git 상태 확인
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo ""
        echo -e "${YELLOW}📝 ${CURRENT_TIME} - Changes detected!${NC}"
        
        # 변경된 파일 목록 표시
        echo -e "${CYAN}Changed files:${NC}"
        git status --porcelain | head -10 | while read line; do
            echo "  $line"
        done
        
        # 자동 커밋 실행
        echo -e "${BLUE}🔄 Running auto-commit...${NC}"
        if AUTO_CONFIRM=1 ./scripts/auto-commit.sh; then
            NEW_COMMIT=$(git rev-parse HEAD)
            if [ "$NEW_COMMIT" != "$LAST_COMMIT" ]; then
                echo -e "${GREEN}✅ Auto-commit successful!${NC}"
                LAST_COMMIT="$NEW_COMMIT"
                
                # 커밋 정보 표시
                echo -e "${CYAN}📝 New commit: $(git log --oneline -1)${NC}"
            fi
        else
            echo -e "${RED}❌ Auto-commit failed${NC}"
        fi
        
        echo ""
    fi
    
    # 원격 저장소 변경사항 확인 (매 5번째 체크마다)
    if [ $((WATCH_COUNT % 5)) -eq 0 ] && git remote get-url origin &>/dev/null; then
        git fetch origin --quiet
        
        CURRENT_BRANCH=$(git branch --show-current)
        LOCAL_COMMIT=$(git rev-parse HEAD)
        REMOTE_COMMIT=$(git rev-parse "origin/$CURRENT_BRANCH" 2>/dev/null || echo "")
        
        if [ ! -z "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
            echo -e "${YELLOW}📥 ${CURRENT_TIME} - Remote changes detected${NC}"
            echo -e "${BLUE}🔄 Pulling remote changes...${NC}"
            
            if git pull origin "$CURRENT_BRANCH"; then
                echo -e "${GREEN}✅ Remote changes merged successfully${NC}"
                LAST_COMMIT=$(git rev-parse HEAD)
            else
                echo -e "${RED}❌ Failed to merge remote changes${NC}"
                echo -e "${YELLOW}⚠️  Manual intervention may be required${NC}"
            fi
        fi
    fi
    
    sleep "$WATCH_INTERVAL"
done
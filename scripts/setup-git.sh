#!/bin/bash

# Git 자동 초기화 및 설정 스크립트
# 사용법: ./scripts/setup-git.sh [repository-url]

set -e  # 오류 시 스크립트 중단

# 색상 출력 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Manufacturing Simulation Git Setup${NC}"
echo "=================================================="

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}📁 Project root: $PROJECT_ROOT${NC}"

# Git 설치 확인
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git이 설치되어 있지 않습니다.${NC}"
    echo "Ubuntu/Debian: sudo apt-get install git"
    echo "CentOS/RHEL: sudo yum install git"
    exit 1
fi

echo -e "${GREEN}✅ Git이 설치되어 있습니다.${NC}"

# Git 사용자 정보 확인 및 설정
echo -e "${BLUE}🔍 Git 사용자 정보 확인 중...${NC}"

if [ -z "$(git config --global user.name)" ]; then
    echo -e "${YELLOW}⚠️  Git 사용자 이름이 설정되지 않았습니다.${NC}"
    read -p "Git 사용자 이름을 입력하세요: " git_username
    git config --global user.name "$git_username"
    echo -e "${GREEN}✅ Git 사용자 이름 설정: $git_username${NC}"
fi

if [ -z "$(git config --global user.email)" ]; then
    echo -e "${YELLOW}⚠️  Git 이메일이 설정되지 않았습니다.${NC}"
    read -p "Git 이메일을 입력하세요: " git_email
    git config --global user.email "$git_email"
    echo -e "${GREEN}✅ Git 이메일 설정: $git_email${NC}"
fi

# .gitignore 파일 생성
echo -e "${BLUE}📝 .gitignore 파일 생성 중...${NC}"
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/
backend.log
frontend.log

# Build outputs
frontend/dist/
frontend/build/

# Environment variables
.env
.env.local
.env.production

# Temporary files
*.tmp
*.temp
output*.txt

# Performance test outputs
performance_results/
test_outputs/

# Cache files
.cache/
.npm/
.yarn/
EOF

echo -e "${GREEN}✅ .gitignore 파일이 생성되었습니다.${NC}"

# Git 저장소 초기화 또는 확인
if [ ! -d ".git" ]; then
    echo -e "${BLUE}🚀 Git 저장소 초기화 중...${NC}"
    git init
    echo -e "${GREEN}✅ Git 저장소가 초기화되었습니다.${NC}"
else
    echo -e "${GREEN}✅ Git 저장소가 이미 존재합니다.${NC}"
fi

# 원격 저장소 설정
if [ ! -z "$1" ]; then
    REPO_URL="$1"
    echo -e "${BLUE}🔗 원격 저장소 설정 중: $REPO_URL${NC}"
    
    # 기존 origin 제거 (있는 경우)
    git remote remove origin 2>/dev/null || true
    
    # 새 origin 추가
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✅ 원격 저장소가 설정되었습니다.${NC}"
else
    echo -e "${YELLOW}⚠️  원격 저장소 URL이 제공되지 않았습니다.${NC}"
    echo "나중에 다음 명령으로 설정할 수 있습니다:"
    echo "git remote add origin <repository-url>"
fi

# 초기 커밋 생성
echo -e "${BLUE}📦 초기 커밋 생성 중...${NC}"

# 모든 파일 추가 (gitignore 적용)
git add .

# 커밋 생성
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  커밋할 변경사항이 없습니다.${NC}"
else
    git commit -m "Initial commit: Manufacturing Process Simulation Setup

🚀 Project Features:
- Vue.js 3 + FastAPI high-performance simulation
- 22,000+ simulation steps per second
- Real-time entity visualization with transit tracking
- Global signal management system
- Drag-and-drop process design interface

🔧 Generated with automated setup script
📅 Setup date: $(date '+%Y-%m-%d %H:%M:%S')"

    echo -e "${GREEN}✅ 초기 커밋이 생성되었습니다.${NC}"
fi

# 원격 저장소에 푸시 (설정된 경우)
if git remote get-url origin &>/dev/null; then
    echo -e "${BLUE}⬆️  원격 저장소에 푸시 중...${NC}"
    
    # 기본 브랜치 설정
    git branch -M main
    
    # 첫 번째 푸시 시도
    if git push -u origin main 2>/dev/null; then
        echo -e "${GREEN}✅ 원격 저장소에 성공적으로 푸시되었습니다.${NC}"
    else
        echo -e "${YELLOW}⚠️  원격 저장소 푸시에 실패했습니다.${NC}"
        echo "다음을 확인해주세요:"
        echo "1. 저장소 URL이 올바른지 확인"
        echo "2. 저장소에 대한 접근 권한이 있는지 확인"
        echo "3. SSH 키 또는 개인 액세스 토큰이 설정되어 있는지 확인"
        echo ""
        echo "수동으로 푸시하려면: git push -u origin main"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Git 설정이 완료되었습니다!${NC}"
echo ""
echo "다음 단계:"
echo "1. 자동 커밋/푸시: ./scripts/auto-commit.sh"
echo "2. 개발 서버 시작: ./scripts/dev-start.sh"
echo "3. 프로덕션 빌드: ./scripts/build.sh"
echo ""
echo -e "${BLUE}Git 상태 확인: git status${NC}"
echo -e "${BLUE}Git 로그 확인: git log --oneline${NC}"
#!/bin/bash
# 로컬 개발 환경 시작 스크립트

echo "🚀 로컬 개발 환경 시작..."

# 백엔드 서버 시작
echo "📦 백엔드 서버 시작 중..."
cd backend
if [ ! -d "venv" ]; then
    echo "가상 환경 생성 중..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
export ENVIRONMENT=development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 프론트엔드 서버 시작
echo "🎨 프론트엔드 서버 시작 중..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ 로컬 개발 환경이 시작되었습니다!"
echo "   - 프론트엔드: http://localhost:5173"
echo "   - 백엔드 API: http://localhost:8000"
echo "   - API 문서: http://localhost:8000/docs"

# 종료 시 모든 프로세스 정리
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

# 프로세스가 종료될 때까지 대기
wait
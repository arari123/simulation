#!/bin/bash

# 백엔드 서버 실행 스크립트
# 서버 시작 시 logs/backend_server.log 파일이 새로 생성됩니다 (최대 1000줄)
cd /home/arari123/project/simulation/backend

# 가상환경 활성화
source venv/bin/activate

# 서버 실행
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

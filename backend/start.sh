#!/bin/bash
# Startup script for Cloud Run
echo "Starting FastAPI application..."
echo "PORT: $PORT"
echo "ENVIRONMENT: $ENVIRONMENT"
echo "ALLOWED_ORIGINS: $ALLOWED_ORIGINS"

# Run the application
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
#!/bin/bash

# Complete deployment script for both frontend and backend
# This script deploys backend first, then updates frontend with the backend URL

set -e

echo "🚀 Starting complete deployment process..."

# Configuration
GOOGLE_CLOUD_PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID:-"your-project-id"}
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-"your-firebase-project-id"}
GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION:-"asia-northeast3"}
SERVICE_NAME=${CLOUD_RUN_SERVICE_NAME:-"simulation-backend"}

# Check required environment variables
if [ "$GOOGLE_CLOUD_PROJECT_ID" = "your-project-id" ]; then
    echo "❌ Please set GOOGLE_CLOUD_PROJECT_ID environment variable"
    echo "export GOOGLE_CLOUD_PROJECT_ID=\"your-actual-project-id\""
    exit 1
fi

if [ "$FIREBASE_PROJECT_ID" = "your-firebase-project-id" ]; then
    echo "❌ Please set FIREBASE_PROJECT_ID environment variable"
    echo "export FIREBASE_PROJECT_ID=\"your-actual-firebase-project-id\""
    exit 1
fi

echo "📋 Configuration:"
echo "  - Google Cloud Project: $GOOGLE_CLOUD_PROJECT_ID"
echo "  - Firebase Project: $FIREBASE_PROJECT_ID"
echo "  - Region: $GOOGLE_CLOUD_REGION"
echo "  - Service Name: $SERVICE_NAME"
echo ""

# Step 1: Deploy backend
echo "🔧 Step 1: Deploying backend to Cloud Run..."
cd "$(dirname "$0")"
./deploy-backend.sh

# Get the backend URL
echo "🔍 Getting backend service URL..."
BACKEND_URL=$(gcloud run services describe $SERVICE_NAME --region=$GOOGLE_CLOUD_REGION --format="value(status.url)")

if [ -z "$BACKEND_URL" ]; then
    echo "❌ Failed to get backend URL. Deployment may have failed."
    exit 1
fi

echo "✅ Backend deployed successfully!"
echo "🌐 Backend URL: $BACKEND_URL"

# Step 2: Update frontend environment and deploy
echo ""
echo "🎨 Step 2: Deploying frontend to Firebase Hosting..."

# Set environment variables for frontend deployment
export BACKEND_URL=$BACKEND_URL
export FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID

./deploy-frontend.sh

echo ""
echo "🎉 Complete deployment finished successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "  - Backend: $BACKEND_URL"
echo "  - Frontend: https://$FIREBASE_PROJECT_ID.web.app"
echo "  - API Docs: $BACKEND_URL/docs"
echo "  - Health Check: $BACKEND_URL/health"
echo ""
echo "🧪 Quick Test Commands:"
echo "  curl $BACKEND_URL/health"
echo "  open https://$FIREBASE_PROJECT_ID.web.app"
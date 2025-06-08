#!/bin/bash

# Firebase Hosting deployment script for Vue.js frontend
# This script builds and deploys the frontend to Firebase Hosting

set -e

# Configuration variables
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-"your-firebase-project-id"}
BACKEND_URL=${BACKEND_URL:-"https://simulation-backend-your-hash-uc.a.run.app"}

echo "🚀 Starting Firebase Hosting deployment"
echo "📍 Firebase Project: ${FIREBASE_PROJECT_ID}"
echo "🔗 Backend URL: ${BACKEND_URL}"

# Check if required tools are installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI is not installed. Installing..."
    npm install -g firebase-tools
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js first."
    exit 1
fi

# Authenticate with Firebase (if not already authenticated)
echo "🔐 Checking Firebase authentication..."
if ! firebase projects:list &> /dev/null; then
    echo "🔑 Please authenticate with Firebase:"
    firebase login
fi

# Navigate to frontend directory
cd "$(dirname "$0")/../frontend"

echo "📦 Installing dependencies..."
npm install

# Create environment configuration for production
echo "⚙️  Setting up production environment..."
cat > .env.production << EOF
VITE_API_BASE_URL=${BACKEND_URL}
VITE_ENVIRONMENT=production
EOF

echo "🏗️  Building frontend..."
npm run build

# Navigate back to project root for Firebase deployment
cd ..

echo "🔧 Setting Firebase project..."
firebase use ${FIREBASE_PROJECT_ID}

echo "🚀 Deploying to Firebase Hosting..."
firebase deploy --only hosting

# Get the hosting URL
HOSTING_URL="https://${FIREBASE_PROJECT_ID}.web.app"

echo "✅ Deployment completed successfully!"
echo "🌐 Frontend URL: ${HOSTING_URL}"
echo ""
echo "🔧 To deploy again:"
echo "./scripts/deploy-frontend.sh"
echo ""
echo "📊 To view hosting info:"
echo "firebase hosting:sites:list"
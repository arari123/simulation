#!/bin/bash
# Build and deploy script for Cloud Run with simulation config files

# Exit on error
set -e

echo "🔧 Preparing build context..."

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
echo "📁 Using build directory: $BUILD_DIR"

# Copy backend code
cp -r . "$BUILD_DIR/"

# Copy simulation config files from parent directory
echo "📋 Copying simulation configuration files..."
cp ../simulation-config.json "$BUILD_DIR/" 2>/dev/null || true
cp ../base.json "$BUILD_DIR/" 2>/dev/null || true
cp ../ex*.json "$BUILD_DIR/" 2>/dev/null || true
cp ../test*.json "$BUILD_DIR/" 2>/dev/null || true
cp ../*.json "$BUILD_DIR/" 2>/dev/null || true

# List copied files
echo "📦 Files in build context:"
ls -la "$BUILD_DIR/"*.json 2>/dev/null || echo "No JSON files found"

# Build and submit from temporary directory
echo "🏗️ Building Docker image..."
cd "$BUILD_DIR"
gcloud builds submit --tag gcr.io/my-simulation-app-462307/simulation-backend:latest .

# Clean up
echo "🧹 Cleaning up..."
rm -rf "$BUILD_DIR"

echo "✅ Build complete! Now deploy with:"
echo "gcloud run deploy simulation-backend --image gcr.io/my-simulation-app-462307/simulation-backend:latest --region asia-northeast3"
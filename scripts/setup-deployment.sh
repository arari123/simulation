#!/bin/bash

# Deployment setup script
# This script helps configure the environment for deployment

set -e

echo "🔧 Deployment Setup Script"
echo "=========================="
echo ""

# Function to read user input with default value
read_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        echo "${value:-$default}"
    else
        read -p "$prompt: " value
        echo "$value"
    fi
}

# Get project information
echo "📋 Please provide your project information:"
echo ""

GOOGLE_CLOUD_PROJECT_ID=$(read_with_default "Google Cloud Project ID" "")
FIREBASE_PROJECT_ID=$(read_with_default "Firebase Project ID" "$GOOGLE_CLOUD_PROJECT_ID")
GOOGLE_CLOUD_REGION=$(read_with_default "Google Cloud Region" "asia-northeast3")
SERVICE_NAME=$(read_with_default "Cloud Run Service Name" "simulation-backend")

echo ""
echo "🔍 Configuration Summary:"
echo "  - Google Cloud Project ID: $GOOGLE_CLOUD_PROJECT_ID"
echo "  - Firebase Project ID: $FIREBASE_PROJECT_ID"
echo "  - Region: $GOOGLE_CLOUD_REGION"
echo "  - Service Name: $SERVICE_NAME"
echo ""

read -p "Is this configuration correct? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled. Please run the script again."
    exit 1
fi

# Update configuration files
echo "🔧 Updating configuration files..."

# Update .firebaserc
cat > .firebaserc << EOF
{
  "projects": {
    "default": "$FIREBASE_PROJECT_ID"
  }
}
EOF

# Update deployment-config.yaml
cat > deployment-config.yaml << EOF
# Deployment Configuration
google_cloud:
  project_id: "$GOOGLE_CLOUD_PROJECT_ID"
  region: "$GOOGLE_CLOUD_REGION"
  zone: "${GOOGLE_CLOUD_REGION}-a"
  
cloud_run:
  service_name: "$SERVICE_NAME"
  memory: "1Gi"
  cpu: "1"
  min_instances: 0
  max_instances: 10
  timeout: 300
  concurrency: 80
  port: 8080

firebase:
  project_id: "$FIREBASE_PROJECT_ID"

environments:
  development:
    backend_url: "http://localhost:8000"
    debug: true
    log_level: "DEBUG"
    
  production:
    backend_url: "https://$SERVICE_NAME-YOUR_HASH.a.run.app"
    debug: false
    log_level: "WARNING"

build:
  node_version: "18"
  python_version: "3.11"
  docker_registry: "gcr.io"
EOF

# Create environment file for backend
echo "📝 Creating backend environment file..."
cat > backend/.env << EOF
# Backend Environment Variables
ENVIRONMENT=production
DEBUG=false
PORT=8080
LOG_LEVEL=INFO

# CORS settings (will be updated after frontend deployment)
ALLOWED_ORIGINS=https://$FIREBASE_PROJECT_ID.web.app
EOF

# Create export script for easy environment setup
echo "📝 Creating environment export script..."
cat > scripts/set-env.sh << EOF
#!/bin/bash
# Environment variables for deployment
export GOOGLE_CLOUD_PROJECT_ID="$GOOGLE_CLOUD_PROJECT_ID"
export FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID"
export GOOGLE_CLOUD_REGION="$GOOGLE_CLOUD_REGION"
export CLOUD_RUN_SERVICE_NAME="$SERVICE_NAME"

echo "Environment variables set:"
echo "  GOOGLE_CLOUD_PROJECT_ID=$GOOGLE_CLOUD_PROJECT_ID"
echo "  FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID"
echo "  GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION"
echo "  CLOUD_RUN_SERVICE_NAME=$CLOUD_RUN_SERVICE_NAME"
EOF

chmod +x scripts/set-env.sh

echo "✅ Setup completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Source the environment variables:"
echo "   source scripts/set-env.sh"
echo ""
echo "2. Authenticate with Google Cloud and Firebase:"
echo "   gcloud auth login"
echo "   firebase login"
echo ""
echo "3. Deploy the application:"
echo "   ./scripts/deploy-all.sh"
echo ""
echo "💡 Tip: You can run 'source scripts/set-env.sh' anytime to set environment variables."
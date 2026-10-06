#!/usr/bin/env bash
# ==============================================================================
# Hyrd — Cloud Run Production Deployment Script (Bash / Cloud Shell)
# ==============================================================================

set -euo pipefail

SERVICE_NAME="hyrd"
REGION="${GCP_REGION:-us-central1}"
PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No Google Cloud project selected."
    echo "Run: gcloud config set project <YOUR_PROJECT_ID>"
    exit 1
fi

echo "🚀 Deploying Hyrd to Google Cloud Run..."
echo "• Project: $PROJECT_ID"
echo "• Region:  $REGION"
echo "• Service: $SERVICE_NAME"
echo ""

# Enable required Google Cloud APIs
echo "🔧 Ensuring Cloud Run and Cloud Build APIs are enabled..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project="$PROJECT_ID"

# Build and deploy from source directly to Cloud Run
echo "📦 Building container and deploying service..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars="PORT=8080" \
    --project="$PROJECT_ID"

echo ""
echo "✅ Deployment complete!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)' --project="$PROJECT_ID")
echo "🌐 Your Hyrd application is live at: $SERVICE_URL"

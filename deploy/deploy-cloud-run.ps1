# ==============================================================================
# Hyrd — Cloud Run Production Deployment Script (PowerShell)
# ==============================================================================

param(
    [string]$ProjectId = "",
    [string]$Region = "us-central1",
    [string]$ServiceName = "hyrd"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    try {
        $ProjectId = (gcloud config get-value project 2>$null).Trim()
    } catch {
        $ProjectId = ""
    }
}

if (-not $ProjectId) {
    Write-Host "❌ Error: No Google Cloud Project ID provided." -ForegroundColor Red
    Write-Host "Usage: .\deploy\deploy-cloud-run.ps1 -ProjectId 'my-gcp-project-id'" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 Deploying Hyrd to Google Cloud Run..." -ForegroundColor Cyan
Write-Host "• Project: $ProjectId" -ForegroundColor Gray
Write-Host "• Region:  $Region" -ForegroundColor Gray
Write-Host "• Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

Write-Host "🔧 Enabling required Google Cloud APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$ProjectId

Write-Host "📦 Building and deploying directly from source..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="PORT=8080" `
    --project=$ProjectId

Write-Host ""
$ServiceUrl = (gcloud run services describe $ServiceName --region $Region --format='value(status.url)' --project=$ProjectId).Trim()
Write-Host "✅ Deployment Succeeded!" -ForegroundColor Green
Write-Host "🌐 Your Hyrd application is live at: $ServiceUrl" -ForegroundColor Cyan

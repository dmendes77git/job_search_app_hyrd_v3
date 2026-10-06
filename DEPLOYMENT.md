# 🚀 Hyrd — Production Containerization & Cloud Run Deployment Guide

> **Don't just search. Get Hyrd!**

This guide provides end-to-end instructions for containerizing **Hyrd (v3)** with Docker and deploying it to **Google Cloud Run** for a scalable, production-grade, globally accessible deployment.

---

## 🏗️ Architecture Overview

- **Base Image**: `python:3.11-slim` with minimal Debian dependencies for fast cold-starts (< 12 seconds).
- **Web Server**: Streamlit configured for headless, non-CORS execution on dynamic port `${PORT:-8080}`.
- **Security**: Runs under an unprivileged `appuser` (non-root UID) adhering to standard enterprise security compliance.
- **Health Check**: Native Streamlit endpoint `/_stcore/health` monitored by Docker and Cloud Run.
- **Pricing & Scaling**: Configured for **Scale-to-Zero** (`--min-instances 0`), meaning **$0 cost** when nobody is using the application.

---

## 🎯 Deployment Methods

Choose the method that best matches your setup:

### Method 1: Continuous Deployment from GitHub (Easiest — 3 Clicks, No Local Tools Needed)

Because your code is already pushed to GitHub at [`https://github.com/dmendes77git/agentic-ai-job-search-v3.git`](https://github.com/dmendes77git/agentic-ai-job-search-v3.git), Google Cloud Run can build and deploy it directly from GitHub!

1. Open the [Google Cloud Console Cloud Run Page](https://console.cloud.google.com/run).
2. Click **Create Service** (+ icon at the top).
3. Under **Deployment platform**, choose:
   - **"Continuously deploy from a repository"**
   - Click **Set Up with Cloud Build**.
   - Select **GitHub** as the provider and authorize your account (`dmendes77git`).
   - Select repository: `agentic-ai-job-search-v3`.
   - Branch: `^main$`.
   - Build Type: **Dockerfile** (path: `/Dockerfile`).
4. In **Service settings**:
   - **Service name**: `hyrd`
   - **Region**: `us-central1` (or your preferred region)
   - **Authentication**: Select **"Allow unauthenticated invocations"** (public web access).
5. In **Container, Networking, Security**:
   - **Container port**: `8080`
   - **Memory**: `1 GiB` (or 2 GiB for heavy resume parsing)
   - **CPU**: `1`
   - Under **Variables & Secrets**, add your environment variables:
     - `GEMINI_API_KEY`: *(Your Google AI Studio API Key)*
     - `APIFY_API_TOKEN`: *(Optional, for Apify scrapers)*
6. Click **Create**.
7. Google Cloud Build will automatically build the container and deploy your live public URL (e.g. `https://hyrd-xxxxx-uc.a.run.app`)! Every future `git push origin main` will automatically redeploy!

---

### Method 2: One-Click Deploy via Google Cloud Shell (No Local Docker Required)

If you don't have Docker or the `gcloud` CLI installed locally on Windows, you can deploy in 2 minutes using Google's free in-browser Cloud Shell:

1. Go to [https://shell.cloud.google.com/](https://shell.cloud.google.com/) and sign in.
2. Clone your repository:
   ```bash
   git clone https://github.com/dmendes77git/agentic-ai-job-search-v3.git
   cd agentic-ai-job-search-v3
   ```
3. Run the automated deployment script:
   ```bash
   chmod +x deploy/deploy-cloud-run.sh
   ./deploy/deploy-cloud-run.sh
   ```
4. When prompted, select your Google Cloud project and region (`us-central1`).
5. The script builds the container and outputs your live HTTPS URL.

---

### Method 3: Deploy from Windows Terminal (Using Google Cloud SDK)

If you have `gcloud` installed locally on Windows:

```powershell
cd C:\Users\david\.gemini\antigravity\scratch\agentic-job-search-v3

# 1. Login to Google Cloud
gcloud auth login

# 2. Set your Google Cloud Project
gcloud config set project YOUR_PROJECT_ID

# 3. Run the PowerShell deployment script
.\deploy\deploy-cloud-run.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1
```

---

### Method 4: Local Container Testing with Docker Compose

If you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your machine and want to test the container locally before deploying:

1. Create or verify your `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
2. Build and run with Docker Compose:
   ```powershell
   docker compose up --build
   ```
3. Open your browser and navigate to:
   ```text
   http://localhost:8080
   ```
4. Stop the container anytime with `Ctrl + C` or `docker compose down`.

---

## 🔐 Managing Secrets & API Keys in Production

Instead of plain-text environment variables, enterprise production best practice is to store API keys in **Google Secret Manager**:

1. Store the secret in Secret Manager:
   ```bash
   echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
   ```
2. Grant the Cloud Run service account access:
   ```bash
   gcloud secrets add-iam-policy-binding gemini-api-key \
       --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```
3. Reference the secret during deployment:
   ```bash
   gcloud run deploy hyrd \
       --source . \
       --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
   ```

---

## ⚡ Cost & Performance Tuning on Cloud Run

| Setting | Recommended Value | Reason |
| :--- | :--- | :--- |
| **Min Instances** | `0` | Scales to 0 when idle. **Cost: $0/month** when not actively searched. |
| **Max Instances** | `5` – `10` | Caps maximum concurrency to prevent unexpected traffic spikes. |
| **Memory** | `1 GiB` or `2 GiB` | Handles in-memory PDF parsing and parallel thread pools comfortably. |
| **CPU** | `1 vCPU` | Sufficient for concurrent async scraping and streaming responses. |
| **Port** | `8080` | Default Cloud Run ingress port, mapped to Streamlit. |

---

*Hyrd — Don't just search. Get Hyrd!*

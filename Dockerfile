# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# Install minimal OS dependencies for health check and document generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user for security compliance
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

# Install dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . .

# Ensure data directory exists and has proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Expose Cloud Run dynamic port (defaults to 8080)
EXPOSE 8080

# Health check using Streamlit's native health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Launch Streamlit with Cloud Run compatibility flags
ENTRYPOINT ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"]

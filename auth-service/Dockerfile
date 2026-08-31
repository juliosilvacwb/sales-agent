# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# Set working directory
WORKDIR /app

# Install system dependencies if required for builds and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first for efficient caching
COPY auth-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and auth service files
COPY src/ /app/src/
COPY auth-service/ /app/auth-service/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/keys && \
    chown -R appuser:appuser /app

USER appuser

# Expose Auth Service port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default entrypoint starts the Auth FastAPI application
ENTRYPOINT ["python", "-m", "uvicorn", "--app-dir", "auth-service", "app:app", "--host", "0.0.0.0", "--port", "8001"]

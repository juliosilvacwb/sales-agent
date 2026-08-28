# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DATASET_PATH=/app/dataset/sales.csv \
    LOG_LEVEL=INFO

# Set working directory
WORKDIR /app

# Install system dependencies if required for builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first for efficient caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code, dataset, and configuration files
COPY src/ /app/src/
COPY dataset/ /app/dataset/
COPY .env.example /app/.env.example
COPY pyproject.toml /app/pyproject.toml

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Default entrypoint runs the CLI interactive loop
ENTRYPOINT ["python", "-m", "src.adapter.inbound.cli.main"]

# AInTandem Agent MCP Scheduler - Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies to system location (not --user)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set metadata
LABEL maintainer="AInTandem Agent MCP Scheduler"
LABEL description="AInTandem Agent MCP Scheduler with MCP integration"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app/src

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r agent && useradd -r -g agent agent

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder (system site-packages)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY config/ /app/config/
COPY src/ /app/src/
COPY storage/ /app/storage/
COPY main.py /app/

# Create necessary directories and set permissions
RUN mkdir -p /app/storage/tasks \
    /app/storage/logs \
    /app/storage/temp \
    && chown -R agent:agent /app

# Switch to non-root user
USER agent

# Expose ports
# 8000 - FastAPI server
# 7860 - Gradio GUI
EXPOSE 8000 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run both API and GUI
CMD ["python", "main.py"]

# Docker Deployment Guide - Qwen Agent MCP Scheduler

Complete guide for building and deploying Qwen Agent MCP Scheduler using Docker.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Dockerfile Explanation](#dockerfile-explanation)
4. [Docker Compose Configuration](#docker-compose-configuration)
5. [Building the Image](#building-the-image)
6. [Running the Container](#running-the-container)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM available for Docker
- 500MB+ disk space

### Install Docker

**macOS**:
```bash
brew install --cask docker
```

**Ubuntu/Debian**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Windows**:
Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## Quick Start

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd agent-infra
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Build and Run

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using Docker directly
docker build -t qwen-agent-scheduler .
docker run -p 8000:8000 -p 7860:7860 qwen-agent-scheduler
```

### 4. Access Services

- **Gradio GUI**: http://localhost:7860
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Dockerfile Explanation

The Dockerfile uses multi-stage build for optimization:

### Stage 1: Builder

```dockerfile
FROM python:3.11-slim AS builder
```

- Installs build dependencies (gcc, g++)
- Installs Python packages to `/root/.local`
- Creates a clean dependency layer

### Stage 2: Runtime

```dockerfile
FROM python:3.11-slim
```

- Installs runtime dependencies (nodejs, npm, curl)
- Copies Python packages from builder
- Creates non-root `agent` user
- Sets up proper directory structure
- Configures health check

### Key Features

1. **Multi-stage build** - Reduces final image size
2. **Non-root user** - Security best practice
3. **Health check** - Automatic container monitoring
4. **Optimized layers** - Better caching and rebuild speed

---

## Docker Compose Configuration

### Main Service

```yaml
qwen-agent:
  build:
    context: .
    dockerfile: Dockerfile
  ports:
    - "8000:8000"  # API
    - "7860:7860"  # GUI
  environment:
    - LOG_LEVEL=INFO
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  volumes:
    - ./config:/app/config:ro
    - qwen-storage:/app/storage
```

### Optional Services

**Nginx Reverse Proxy**:
```bash
docker-compose --profile with-nginx up -d
```

**Redis Caching**:
```bash
docker-compose --profile with-redis up -d
```

**PostgreSQL Database**:
```bash
docker-compose --profile with-postgres up -d
```

**All Optional Services**:
```bash
docker-compose --profile with-nginx --profile with-redis --profile with-postgres up -d
```

---

## Building the Image

### Standard Build

```bash
docker build -t qwen-agent-scheduler:latest .
```

### Build with Arguments

```bash
docker build \
  -t qwen-agent-scheduler:v1.0.0 \
  -t qwen-agent-scheduler:latest \
  --build-arg PYTHON_VERSION=3.11 \
  .
```

### Build for Different Platforms

```bash
# Build for Apple Silicon (M1/M2)
docker buildx build --platform linux/arm64 -t qwen-agent-scheduler:latest .

# Build for Intel/AMD
docker buildx build --platform linux/amd64 -t qwen-agent-scheduler:latest .

# Build for both (multi-arch)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t qwen-agent-scheduler:latest \
  --push \
  .
```

### View Build Details

```bash
# Show image history
docker history qwen-agent-scheduler:latest

# Show image layers
docker inspect qwen-agent-scheduler:latest

# Show image size
docker images qwen-agent-scheduler
```

---

## Running the Container

### Basic Run

```bash
docker run -d \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  qwen-agent-scheduler:latest
```

### Run with Environment Variables

```bash
docker run -d \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  -e LOG_LEVEL=DEBUG \
  -e OPENAI_API_KEY=your_key_here \
  -e DEEPSEEK_API_KEY=your_deepseek_key \
  qwen-agent-scheduler:latest
```

### Run with Volume Mounts

```bash
docker run -d \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  -v $(pwd)/config:/app/config:ro \
  -v qwen-storage:/app/storage \
  qwen-agent-scheduler:latest
```

### Run with Resource Limits

```bash
docker run -d \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  --memory="2g" \
  --cpus="2.0" \
  qwen-agent-scheduler:latest
```

### Run with Auto-Restart

```bash
docker run -d \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  --restart unless-stopped \
  qwen-agent-scheduler:latest
```

### Interactive Run (Development)

```bash
docker run -it \
  --name qwen-agent \
  -p 8000:8000 \
  -p 7860:7860 \
  -v $(pwd):/app \
  qwen-agent-scheduler:latest \
  bash
```

---

## Production Deployment

### Using Docker Compose (Recommended)

```bash
# Start production deployment
docker-compose up -d

# View logs
docker-compose logs -f qwen-agent

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml qwen-agent

# List services
docker service ls

# Remove stack
docker stack rm qwen-agent
```

### Using Kubernetes

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qwen-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: qwen-agent
  template:
    metadata:
      labels:
        app: qwen-agent
    spec:
      containers:
      - name: qwen-agent
        image: qwen-agent-scheduler:latest
        ports:
        - containerPort: 8000
        - containerPort: 7860
        env:
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: qwen-agent-service
spec:
  selector:
    app: qwen-agent
  ports:
  - name: api
    port: 8000
    targetPort: 8000
  - name: gui
    port: 7860
    targetPort: 7860
  type: LoadBalancer
```

Deploy to Kubernetes:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl get pods
kubectl get services
```

---

## Container Management

### View Logs

```bash
# All logs
docker logs qwen-agent

# Follow logs
docker logs -f qwen-agent

# Last 100 lines
docker logs --tail 100 qwen-agent

# Logs from specific time
docker logs --since 1h qwen-agent
```

### Execute Commands

```bash
# Open shell in running container
docker exec -it qwen-agent bash

# Run Python command
docker exec qwen-agent python -c "print('Hello')"

# Check processes
docker exec qwen-agent ps aux

# Check disk usage
docker exec qwen-agent df -h
```

### Container Statistics

```bash
# Resource usage
docker stats qwen-agent

# Container info
docker inspect qwen-agent

# Container processes
docker top qwen-agent
```

### Stop and Remove

```bash
# Stop container
docker stop qwen-agent

# Remove container
docker rm qwen-agent

# Force remove running container
docker rm -f qwen-agent

# Remove image
docker rmi qwen-agent-scheduler:latest
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs qwen-agent

# Check container status
docker ps -a

# Inspect container
docker inspect qwen-agent
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
docker run -p 8001:8000 qwen-agent-scheduler
```

### Permission Issues

```bash
# Fix volume permissions
docker run --rm \
  -v $(pwd)/storage:/app/storage \
  alpine chown -R 1000:1000 /app/storage
```

### Out of Memory

```bash
# Check Docker memory limit
docker system info | grep Memory

# Increase Docker memory limit in Docker Desktop settings
```

### Network Issues

```bash
# List networks
docker network ls

# Create custom network
docker network create qwen-network

# Run with custom network
docker run --network qwen-network qwen-agent-scheduler
```

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything
docker system prune -a --volumes
```

---

## Building for Production

### Optimize Image Size

```dockerfile
# Use .dockerignore to exclude unnecessary files
# Use multi-stage build
# Combine RUN commands
# Clean up package manager cache
```

### Security Scanning

```bash
# Scan image for vulnerabilities
docker scan qwen-agent-scheduler:latest

# Use Trivy
trivy image qwen-agent-scheduler:latest
```

### Tagging Strategy

```bash
# Version tags
docker build -t qwen-agent-scheduler:1.0.0 .
docker build -t qwen-agent-scheduler:1.0 .
docker build -t qwen-agent-scheduler:latest .

# Git commit hash
COMMIT_HASH=$(git rev-parse --short HEAD)
docker build -t qwen-agent-scheduler:${COMMIT_HASH} .
```

### Push to Registry

```bash
# Docker Hub
docker tag qwen-agent-scheduler:latest username/qwen-agent:latest
docker push username/qwen-agent:latest

# AWS ECR
docker tag qwen-agent-scheduler:latest <ecr-repo>/qwen-agent:latest
docker push <ecr-repo>/qwen-agent:latest

# Google GCR
docker tag qwen-agent-scheduler:latest gcr.io/<project>/qwen-agent:latest
docker push gcr.io/<project>/qwen-agent:latest
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Build and Push

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            username/qwen-agent:latest
            username/qwen-agent:${{ github.sha }}
```

---

## Reference

### Useful Commands

```bash
# Quick test
./docker-build-test.sh

# Full stack
docker-compose --profile with-nginx --profile with-redis up -d

# Clean restart
docker-compose down -v
docker-compose up -d

# Backup volumes
docker run --rm -v qwen-storage:/data -v $(pwd):/backup \
  alpine tar czf /backup/qwen-storage-backup.tar.gz /data

# Restore volumes
docker run --rm -v qwen-storage:/data -v $(pwd):/backup \
  alpine tar xzf /backup/qwen-storage-backup.tar.gz -C /
```

### File Locations

| File | Purpose |
|------|---------|
| `Dockerfile` | Image definition |
| `docker-compose.yml` | Service orchestration |
| `.dockerignore` | Build exclusions |
| `docker-build-test.sh` | Build and test script |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | INFO |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API key | - |
| `DASHSCOPE_API_KEY` | Qwen API key | - |
| `BRAVE_API_KEY` | Brave Search API key | - |
| `DATABASE_URL` | PostgreSQL connection | - |

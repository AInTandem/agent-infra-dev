# Deployment Guide

This guide covers deploying AInTandem Agent MCP Scheduler to production environments.

## Table of Contents

1. [Environment Requirements](#environment-requirements)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring & Logging](#monitoring--logging)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

## Environment Requirements

### Minimum Requirements

- **Python**: 3.10 or higher
- **Memory**: 512MB RAM (1GB+ recommended)
- **Disk**: 500MB free space
- **Network**: For API calls and MCP servers

### Recommended Production Requirements

- **CPU**: 2+ cores
- **Memory**: 2GB+ RAM
- **Disk**: 5GB+ SSD storage
- **Network**: Stable internet connection

## Local Development Setup

### Quick Start

```bash
# Clone repository
git clone <your-repo-url>
cd agent-infra

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
python tests/test_integration.py

# Start application
python main.py
```

### Development Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Start with auto-reload
uvicorn api.openapi_server:app --reload --host 0.0.0.0 --port 8000

# Start GUI separately
python -m gui.app
```

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/qwen-agent.service`:

```ini
[Unit]
Description=AInTandem Agent MCP Scheduler
After=network.target

[Service]
Type=simple
User=agent
WorkingDirectory=/opt/qwen-agent
Environment="PATH=/opt/qwen-agent/venv/bin"
ExecStart=/opt/qwen-agent/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qwen-agent
sudo systemctl start qwen-agent
sudo systemctl status qwen-agent
```

### Using Supervisor

Create `/etc/supervisor/conf.d/qwen-agent.conf`:

```ini
[program:qwen-agent]
command=/opt/qwen-agent/venv/bin/python main.py
directory=/opt/qwen-agent
user=agent
autostart=true
autorestart=true
stderr_logfile=/var/log/qwen-agent.err.log
stdout_logfile=/var/log/qwen-agent.out.log
```

Start:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start qwen-agent
```

### Using Gunicorn (Production WSGI Server)

Install gunicorn:

```bash
pip install gunicorn uvicorn[standard]
```

Create `gunicorn_config.py`:

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

Run:

```bash
gunicorn -c gunicorn_config.py api.openapi_server:app
```

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create storage directory
RUN mkdir -p /app/storage/tasks /app/storage/logs

# Expose ports
EXPOSE 8000 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run application
CMD ["python", "main.py"]
```

### docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  qwen-agent:
    build: .
    container_name: qwen-agent
    ports:
      - "8000:8000"  # API
      - "7860:7860"  # GUI
    environment:
      - LOG_LEVEL=INFO
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./config:/app/config:ro
      - ./storage:/app/storage
      - ./logs:/app/storage/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Deploy with Docker

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Cloud Deployment

### AWS ECS/Fargate

1. Push Docker image to ECR
2. Create ECS task definition
3. Configure security groups (ports 8000, 7860)
4. Set environment variables
5. Deploy service

Task Definition Example:

```json
{
  "family": "qwen-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "qwen-agent",
      "image": "<your-ecr-repo>/qwen-agent:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"},
        {"containerPort": 7860, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "OPENAI_API_KEY", "value": "<your-key>"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "storage",
          "containerPath": "/app/storage"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/qwen-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "storage",
      "efsVolumeConfiguration": {
        "fileSystemId": "<your-efs-id>",
        "rootDirectory": "/"
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/<project-id>/qwen-agent

# Deploy to Cloud Run
gcloud run deploy qwen-agent \
  --image gcr.io/<project-id>/qwen-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars LOG_LEVEL=INFO \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --port 8000
```

### Azure Container Instances

```bash
# Create resource group
az group create --name qwen-agent-rg --location eastus

# Create container
az container create \
  --resource-group qwen-agent-rg \
  --name qwen-agent \
  --image <your-registry>/qwen-agent:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8000 7860 \
  --environment-variables LOG_LEVEL=INFO \
  --secure-environment-variables OPENAI_API_KEY=$OPENAI_API_KEY \
  --restart-policy Always
```

## Monitoring & Logging

### Application Logs

Logs are stored in `storage/logs/`:

```
storage/logs/
├── app.log           # Application logs
├── error.log         # Error logs
└── scheduler.log     # Scheduler logs
```

### Log Rotation

Configure in `config/app.yaml`:

```yaml
logging:
  level: INFO
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
  rotation: "100 MB"
  retention: "30 days"
  compression: zip
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check scheduler status
curl http://localhost:8000/v1/tasks

# Monitor system resources
python -c "from core.resource_limiter import SystemResourceMonitor; import json; print(json.dumps(SystemResourceMonitor.get_system_stats(), indent=2))"
```

### Metrics Integration

Use Prometheus + Grafana:

```python
# Add to main.py
from prometheus_client import start_http_server, Counter, Histogram

# Define metrics
request_counter = Counter('api_requests_total', 'Total API requests')
task_counter = Counter('tasks_executed_total', 'Total tasks executed')

# Start metrics server
start_http_server(9090)
```

## Security Best Practices

### Environment Variables

1. Never commit `.env` files
2. Use different API keys for dev/prod
3. Rotate keys regularly
4. Use secret management services:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id qwen-agent/keys

# HashiCorp Vault
vault kv get -field=api_key secret/qwen-agent
```

### Network Security

1. Use HTTPS in production
2. Configure CORS properly
3. Use firewall rules:
   - Only expose ports 8000, 7860
   - Limit IP access if possible
4. Use reverse proxy (nginx):

```nginx
server {
    listen 443 ssl;
    server_name agent.example.com;

    ssl_certificate /etc/ssl/certs/agent.crt;
    ssl_certificate_key /etc/ssl/private/agent.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Sandbox Configuration

For production, use strict security:

```python
from core.security import create_strict_policy

# In config/app.yaml
sandbox:
  enabled: true
  max_memory_mb: 512
  max_cpu_time: 30
  network_access: false
  allow_command_execution: false
```

## Troubleshooting

### Common Issues

**1. Agent Initialization Failed**

```
ERROR: Failed to create agent: Invalid model cfg
```

**Solution**: Check LLM configuration in `config/llm.yaml` and verify API keys.

**2. MCP Server Connection Timeout**

```
WARNING: Failed to connect to MCP server: timeout
```

**Solution**:
- Verify MCP server is running
- Check command and arguments in `config/mcp_servers.yaml`
- Ensure required environment variables are set

**3. Task Not Executing**

```
Error running job: Agent 'researcher' not found
```

**Solution**:
- Verify agent exists and is enabled
- Check agent configuration
- Review scheduler logs

**4. High Memory Usage**

```
Resource violation: Memory usage 600MB exceeds 512MB
```

**Solution**:
- Adjust `max_memory_mb` in sandbox config
- Check for memory leaks in agent code
- Monitor with `psutil`

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

Enable verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Recovery Procedures

**Restore from backup**:

```bash
# Stop services
sudo systemctl stop qwen-agent

# Restore storage
cp -r /backup/storage/* /opt/qwen-agent/storage/

# Restart services
sudo systemctl start qwen-agent
```

**Clear task persistence**:

```bash
# Backup first
cp storage/tasks/tasks.json storage/tasks/tasks.json.backup

# Clear tasks
echo '{"tasks": [], "updated_at": null}' > storage/tasks/tasks.json

# Restart
sudo systemctl restart qwen-agent
```

## Performance Tuning

### Database Optimization (if using PostgreSQL)

```python
# Add connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
```

### Caching

```python
# Add Redis caching
import redis
from functools import lru_cache

redis_client = redis.Redis(host='localhost', port=6379)

@lru_cache(maxsize=1000)
def get_agent_config(agent_name: str):
    return config_manager.get_agent(agent_name)
```

### Load Balancing

Use nginx as load balancer:

```nginx
upstream qwen_agent_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://qwen_agent_backend;
    }
}
```

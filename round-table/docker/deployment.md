# Docker Deployment Guide

This guide covers deploying Round Table using Docker and Docker Compose.

## Prerequisites

- Docker 20.10 or later
- Docker Compose 2.0 or later

## Quick Start

### Using Docker Compose (Recommended)

1. Copy the example environment file:
```bash
cd docker
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Set a secure secret key
SECRET_KEY=your-secure-random-key-here

# Configure environment
ENVIRONMENT=production
```

3. Start the services:
```bash
docker-compose up -d
```

4. Check the status:
```bash
docker-compose ps
docker-compose logs -f
```

5. Stop the services:
```bash
docker-compose down
```

## Manual Docker Build

### Build the API image:

```bash
cd round-table
docker build -f docker/Dockerfile.api -t roundtable-api:latest .
```

### Run Redis:

```bash
docker run -d \
  --name roundtable-redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine
```

### Run the API:

```bash
docker run -d \
  --name roundtable-api \
  -p 8000:8000 \
  --link roundtable-redis:redis \
  -e REDIS_URL=redis://redis:6379/0 \
  -e DATABASE_URL=sqlite+aiosqlite:///./data/roundtable.db \
  -v api_data:/app/data \
  roundtable-api:latest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret key for encryption | (required) |
| `ENVIRONMENT` | Environment (development/production) | development |
| `LOG_LEVEL` | Logging level | INFO |
| `DATABASE_URL` | Database connection string | sqlite+aiosqlite:///./data/roundtable.db |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `API_HOST` | API host | 0.0.0.0 |
| `API_PORT` | API port | 8000 |

## Health Checks

The API includes a health check endpoint:

```bash
curl http://localhost:8000/api/v1/system/health
```

Docker health checks run every 30 seconds after a 40-second start period.

## Volumes

- `redis_data`: Redis persistence data
- `api_data`: API data directory (database, logs)

## Production Deployment

### Using Nginx Reverse Proxy

1. Create an Nginx configuration:

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream roundtable {
        server roundtable-api:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://roundtable;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

2. Enable the Nginx service in `docker-compose.yml`:
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
  depends_on:
    - api
  networks:
    - roundtable-network
```

3. Start with Nginx:
```bash
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up -d
```

### Using HTTPS

1. Obtain SSL certificates (Let's Encrypt recommended)

2. Update Nginx configuration:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://roundtable;
        # ... other proxy settings
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring

### View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f redis
```

### Check resource usage:

```bash
docker stats
```

## Backup and Restore

### Backup database:

```bash
docker exec roundtable-api \
  tar czf - /app/data/roundtable.db > backup-$(date +%Y%m%d).tar.gz
```

### Restore database:

```bash
docker exec -i roundtable-api \
  tar xzf - -C /app/data < backup-20250111.tar.gz
```

## Troubleshooting

### Container won't start:

1. Check logs:
```bash
docker-compose logs api
```

2. Verify environment variables:
```bash
docker-compose config
```

### Connection issues:

1. Verify network:
```bash
docker network inspect roundtable_roundtable-network
```

2. Test Redis connection:
```bash
docker exec roundtable-api nc -zv redis 6379
```

### Health check failing:

1. Check if API is responding:
```bash
docker exec roundtable-api curl http://localhost:8000/api/v1/system/health
```

2. Verify dependencies are healthy:
```bash
docker-compose ps
```

## Scaling

### Run multiple API instances:

```bash
docker-compose up -d --scale api=3
```

Note: You'll need to configure a load balancer for proper request distribution.

## Security Best Practices

1. **Use strong secrets**: Generate a secure `SECRET_KEY`
2. **Limit resource usage**: Set memory and CPU limits
3. **Use HTTPS**: Enable SSL in production
4. **Regular updates**: Keep Docker images updated
5. **Network isolation**: Use Docker networks
6. **Volume permissions**: Ensure proper file permissions

## Cleanup

### Remove all containers and volumes:

```bash
docker-compose down -v
```

### Remove images:

```bash
docker rmi roundtable-api:latest
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [API Documentation](../docs/round-table/api/overview.md)

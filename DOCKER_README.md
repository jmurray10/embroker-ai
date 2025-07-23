# Docker Deployment Guide

This guide provides instructions for running the Embroker Insurance Chatbot using Docker.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose v2.0+
- 4GB RAM minimum
- API Keys: OpenAI and Pinecone

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/jmurray10/embroker-ai.git
cd embroker-ai
```

### 2. Set Up Environment Variables
```bash
cp .env.docker.example .env
# Edit .env with your API keys
```

### 3. Run with Docker Compose

**Development Mode:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Production Mode:**
```bash
docker-compose up -d
```

### 4. Access the Application
- Application: http://localhost:5000
- Health Check: http://localhost:5000/health
- PostgreSQL: localhost:5432 (dev only)

## Docker Commands

### Build and Start Services
```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f chatbot

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Development Workflow
```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Rebuild after dependency changes
docker-compose build --no-cache chatbot

# Enter container shell
docker-compose exec chatbot bash

# Run tests in container
docker-compose exec chatbot pytest
```

## Configuration

### Environment Variables

Required variables in `.env`:
```bash
# OpenAI API Keys
POC_OPENAI_API=sk-proj-...
PINECONE_API_KEY=pcsk_...

# Flask
SESSION_SECRET=your-secret-key

# Optional
OPENAI_MONITORING_KEY=sk-proj-...  # Defaults to POC_OPENAI_API
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### Docker Compose Services

1. **chatbot** - Main Flask application
   - Port: 5000
   - Volumes: logs, sessions
   - Health check enabled

2. **postgres** - PostgreSQL database
   - Port: 5432 (dev only)
   - Persistent volume for data

3. **redis** - Caching layer (optional)
   - Port: 6379
   - Persistent volume for data

4. **nginx** - Reverse proxy (production profile)
   - Port: 80
   - Load balancing and SSL termination

## Production Deployment

### 1. Use Production Compose File
```bash
docker-compose --profile production up -d
```

### 2. Enable HTTPS (Recommended)
Update `docker/nginx.conf` with SSL certificates:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... rest of config
}
```

### 3. Resource Limits
Add to docker-compose.yml:
```yaml
services:
  chatbot:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 4. Monitoring
```bash
# Check health
curl http://localhost:5000/health

# View resource usage
docker stats

# Check logs
docker-compose logs --tail=100 -f chatbot
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "5001:5000"  # Use 5001 instead
   ```

2. **Database Connection Error**
   ```bash
   # Ensure PostgreSQL is healthy
   docker-compose ps postgres
   docker-compose logs postgres
   ```

3. **API Key Issues**
   ```bash
   # Verify environment variables
   docker-compose exec chatbot env | grep API
   ```

4. **Permission Errors**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 ./logs ./sessions
   ```

### Debug Mode
```bash
# Enable debug logging
docker-compose exec chatbot bash
export FLASK_DEBUG=1
python src/app.py
```

## Backup and Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U embroker embroker_insurance > backup.sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U embroker embroker_insurance < backup.sql
```

### Backup Volumes
```bash
# Backup all volumes
docker run --rm -v embroker-ai_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
```

## Security Considerations

1. **Never commit .env files** - Use .env.example as template
2. **Use secrets management** in production (Docker Secrets, Vault, etc.)
3. **Enable firewall** - Only expose necessary ports
4. **Regular updates** - Keep base images updated
5. **Resource limits** - Prevent container resource exhaustion

## Performance Tuning

### Application
- Adjust Gunicorn workers: `--workers 4`
- Enable threading: `--threads 2`
- Set timeout: `--timeout 120`

### PostgreSQL
```sql
-- In postgres container
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### Docker
```bash
# Increase Docker memory (Docker Desktop)
# Settings > Resources > Memory: 4GB+
```

## Logs and Monitoring

### Application Logs
```bash
# View logs
docker-compose exec chatbot tail -f logs/chat.log

# Export logs
docker cp embroker-chatbot:/app/logs ./exported-logs
```

### Container Metrics
```bash
# Real-time stats
docker stats embroker-chatbot

# Detailed inspection
docker inspect embroker-chatbot
```

## Support

For issues or questions:
1. Check container logs: `docker-compose logs`
2. Verify health: `curl http://localhost:5000/health`
3. Review environment: `docker-compose config`
4. Open an issue on GitHub
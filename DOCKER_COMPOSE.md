# Docker Compose Files

Docker Compose configuration nằm trong thư mục `server/`.

## Files:
- `docker-compose.yml` - Production stack (đầy đủ: Postgres, Redis, ES, Flask, Celery, Nginx)
- `docker-compose.dev.yml` - Development (chỉ: ES, Redis, Celery)

## Production Deployment:
```bash
cd server
docker compose up -d --build
```

## Development:
```bash
cd server
docker compose -f docker-compose.dev.yml up -d
```

## Quick Commands:

### Start services:
```bash
cd server
docker compose up -d
```

### Stop services:
```bash
cd server
docker compose down
```

### View logs:
```bash
cd server
docker compose logs -f
```

### Check status:
```bash
cd server
docker compose ps
```

## Architecture:
- **PostgreSQL** - Docker container hoặc Railway managed
- **MongoDB** - MongoDB Atlas (cloud)
- **Redis** - Docker container
- **Elasticsearch** - Docker container (optional)
- **Flask + Celery** - Application containers
- **Nginx** - Reverse proxy with SSL

Xem chi tiết tại: `server/README.production.md`

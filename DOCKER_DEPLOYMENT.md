# DocuMind AI - Docker Deployment Guide

## 📋 Prerequisites

- Docker Engine 24.0+ installed
- Docker Compose 2.20+ installed
- At least 4GB RAM available
- 10GB free disk space
- Groq API key (get it from https://console.groq.com)

## 🚀 Quick Start

### 1. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.docker .env
```

Edit `.env` and add your credentials:

```bash
GROQ_API_KEY=your_actual_groq_api_key_here
JWT_SECRET_KEY=your-secure-random-secret-key-here
```

**Important:** Generate a secure JWT secret key:

```bash
openssl rand -hex 32
```

### 2. Build and Start Services

```bash
# Build the Docker image
docker-compose build

# Start all services (MongoDB + Backend)
docker-compose up -d
```

### 3. Verify Services are Running

```bash
# Check service status
docker-compose ps

# View backend logs
docker-compose logs -f backend

# Check health status
curl http://localhost:8000/api/v1/health
```

### 4. Access the Application

- **API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/api/docs
- **Health Check:** http://localhost:8000/api/v1/health
- **MongoDB:** localhost:27017

## 🛠️ Common Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f mongodb
```

### Development

```bash
# Rebuild after code changes
docker-compose build backend
docker-compose up -d backend

# Execute commands in container
docker-compose exec backend python -c "print('Hello')"

# Access backend shell
docker-compose exec backend bash

# Access MongoDB shell
docker-compose exec mongodb mongosh
```

### Monitoring

```bash
# Check resource usage
docker stats

# View container processes
docker-compose top

# Inspect container
docker-compose exec backend ps aux
```

## 📂 Volume Mounts

The following directories are persisted:

- `./uploads` - Uploaded documents
- `./chroma_db` - Vector database
- `./logs` - Application logs
- MongoDB data (Docker volume)

## 🔧 Configuration

### Environment Variables

All configurations can be overridden via environment variables in `.env`:

**Required:**

- `GROQ_API_KEY` - Your Groq API key
- `JWT_SECRET_KEY` - Secret key for JWT tokens

**Optional (with defaults):**

- `MONGODB_URL` - MongoDB connection string (default: mongodb://mongodb:27017)
- `MONGODB_DB_NAME` - Database name (default: documind_ai)
- `ALLOWED_ORIGINS` - CORS origins (default: http://localhost:3000,http://localhost:5173)
- `PORT` - API port (default: 8000)
- See `docker-compose.yml` for full list

### MongoDB Configuration

MongoDB runs on port 27017. To connect from outside Docker:

```bash
mongosh mongodb://localhost:27017/documind_ai
```

### Ports

- `8000` - Backend API
- `27017` - MongoDB

To change ports, edit `docker-compose.yml`:

```yaml
ports:
  - "8080:8000" # Maps host:8080 to container:8000
```

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Check if ports are already in use
lsof -i :8000
lsof -i :27017

# Remove old containers and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backend can't connect to MongoDB

```bash
# Verify MongoDB is healthy
docker-compose ps

# Check MongoDB logs
docker-compose logs mongodb

# Restart services in order
docker-compose restart mongodb
docker-compose restart backend
```

### Out of memory errors

```bash
# Check memory usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Recommended: At least 4GB RAM
```

### Permission errors with volumes

```bash
# Fix permissions on host
sudo chown -R $USER:$USER ./uploads ./chroma_db ./logs

# Recreate containers
docker-compose down
docker-compose up -d
```

## 🔒 Security Best Practices

1. **Never commit `.env` file** - It contains secrets
2. **Use strong JWT secret** - Generate with `openssl rand -hex 32`
3. **Secure MongoDB** - Add authentication in production
4. **Use HTTPS** - Put behind reverse proxy (nginx/traefik)
5. **Update images** - Regularly update to latest versions
6. **Limit CORS** - Restrict `ALLOWED_ORIGINS` to your domain

## 📊 Health Checks

The backend includes automatic health checks:

```bash
# Manual health check
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "api": "running",
  "version": "2.0.0",
  "mongodb": "connected",
  "chromadb": "connected (X embeddings)"
}
```

## 🚢 Production Deployment

### Option 1: Using Docker Compose

```bash
# Set production environment
export ENVIRONMENT=production

# Use production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Option 2: Using Individual Containers

```bash
# Build image
docker build -t documind-backend:latest .

# Run with external MongoDB
docker run -d \
  --name documind-backend \
  -p 8000:8000 \
  -e MONGODB_URL=mongodb://your-production-mongodb:27017 \
  -e GROQ_API_KEY=your_key \
  -e JWT_SECRET_KEY=your_secret \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/chroma_db:/app/chroma_db \
  documind-backend:latest
```

### Reverse Proxy Setup (Nginx)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔄 Backup & Restore

### Backup

```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --out=/data/backup

# Backup uploads and ChromaDB
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ chroma_db/

# Copy MongoDB backup from container
docker cp documind-mongodb:/data/backup ./mongodb-backup
```

### Restore

```bash
# Restore MongoDB
docker-compose exec mongodb mongorestore /data/backup

# Restore files
tar -xzf backup-20241127.tar.gz
```

## 📝 API Usage Examples

### Register User

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","full_name":"John Doe"}'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Upload Document

```bash
TOKEN="your_jwt_token"
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"
```

### Query Documents

```bash
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is this document about?"}'
```

## 🎯 Performance Tuning

### Memory Optimization

Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
        reservations:
          memory: 2G
```

### Database Optimization

```yaml
services:
  mongodb:
    command: mongod --wiredTigerCacheSizeGB 2
```

## 📞 Support

- **Documentation:** http://localhost:8000/api/docs
- **Health Check:** http://localhost:8000/api/v1/health
- **GitHub Issues:** [Create an issue](https://github.com/madhavgupta3205/DocuMind/issues)

## 🔄 Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker-compose logs -f backend
```

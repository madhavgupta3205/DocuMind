# 🐳 Docker Quick Start

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Groq API key

## Setup in 3 Steps

### 1. Configure Environment

```bash
cp .env.docker .env
# Edit .env and add your GROQ_API_KEY and JWT_SECRET_KEY
```

### 2. Run Setup Script

```bash
./docker-setup.sh
```

### 3. Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs

## Manual Setup

```bash
# Build and start
docker-compose build
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

## Full Documentation

See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for complete documentation.

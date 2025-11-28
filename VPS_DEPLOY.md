# VPS Deployment Steps

## 1. SSH into your VPS
```bash
ssh root@145.223.18.238
```

## 2. Navigate to project directory
```bash
cd DocuMind
```

## 3. Pull latest code from GitHub
```bash
git fetch origin
git reset --hard origin/main
```

## 4. Stop existing containers
```bash
docker compose down
```

## 5. Remove old images (optional, ensures fresh build)
```bash
docker compose build --no-cache
```

## 6. Start containers
```bash
docker compose up -d
```

## 7. Check container status
```bash
docker compose ps
```

## 8. Check backend logs
```bash
docker compose logs -f backend
```

Wait until you see:
- "ChromaDB initialized with X embeddings"
- "DocuMind AI API started successfully!"
- "Uvicorn running on http://0.0.0.0:8000"

Press Ctrl+C to exit logs.

## 9. Test the API
```bash
curl http://localhost:8000/api/v1/health
```

Should return:
```json
{
  "status": "healthy",
  "api": "running",
  "version": "2.0.0",
  "mongodb": "connected",
  "chromadb": "connected (X embeddings)"
}
```

## 10. Test from outside VPS
From your local machine:
```bash
curl http://145.223.18.238:8000/api/v1/health
```

## Done! 🎉
Your backend is now running on: http://145.223.18.238:8000

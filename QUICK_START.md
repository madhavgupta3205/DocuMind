# 🚀 Quick Deployment - Your Setup

## Architecture

- **Backend**: Docker (Spare Laptop) → Port 8000
- **Tunnel**: Cloudflare Tunnel → Exposes backend publicly
- **Frontend**: Vercel → Connects to tunnel URL

## 🎯 Steps to Deploy

### 1️⃣ Backend (On Spare Laptop)

```bash
# Configure environment
cp .env.docker .env
nano .env  # Add GROQ_API_KEY and JWT_SECRET_KEY

# Start backend
./start-backend.sh

# Backend is now running on localhost:8000
```

### 2️⃣ Expose via Cloudflare Tunnel

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Create tunnel
cloudflared tunnel --url http://localhost:8000

# Copy the URL it gives you (e.g., https://random-name.trycloudflare.com)
```

### 3️⃣ Frontend (Deploy to Vercel)

```bash
# Set environment variable in Vercel dashboard
VITE_API_URL=https://random-name.trycloudflare.com

# Deploy
cd frontend
vercel --prod
```

### 4️⃣ Update CORS

```bash
# Edit .env on spare laptop
ALLOWED_ORIGINS=https://your-app.vercel.app

# Restart backend
docker-compose restart backend
```

## ✅ Done!

Your app is now live:

- Frontend: https://your-app.vercel.app
- Backend: https://random-name.trycloudflare.com

## 📝 Full Documentation

See `DEPLOYMENT_GUIDE.md` for detailed instructions, troubleshooting, and advanced setup.

## 🔧 Common Commands

```bash
# View backend logs
docker-compose logs -f backend

# Restart backend
docker-compose restart backend

# Stop everything
docker-compose down

# Start tunnel in background
tmux new -s tunnel
cloudflared tunnel --url http://localhost:8000
# Ctrl+B, then D to detach
```

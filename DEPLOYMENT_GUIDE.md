# 🚀 Deployment Guide - Cloudflare Tunnel + Vercel

This guide is for your specific deployment setup:

- **Backend**: Docker on spare laptop → Cloudflare Tunnel → Public URL
- **Frontend**: Vercel deployment

## 📋 Deployment Architecture

```
Frontend (Vercel)
    ↓ HTTPS
Cloudflare Tunnel (your-backend.trycloudflare.com)
    ↓
Docker Backend (localhost:8000)
    ↓
MongoDB (Docker container)
```

## 🔧 Backend Setup (Spare Laptop)

### 1. Prerequisites

- Docker and Docker Compose installed
- Cloudflare account (free tier works)
- Groq API key

### 2. Configure Environment

Edit `.env` file with your credentials:

```bash
# Required
GROQ_API_KEY=your_actual_groq_api_key
JWT_SECRET_KEY=your_secure_random_secret_key

# CORS - Allow your Vercel domain
ALLOWED_ORIGINS=https://your-app.vercel.app,https://documind.vercel.app
# Or use * for all origins (less secure but easier for testing)
ALLOWED_ORIGINS=*
```

Generate secure JWT secret:

```bash
openssl rand -hex 32
```

### 3. Start Backend with Docker

```bash
# Build and start
docker-compose up -d

# Verify it's running
curl http://localhost:8000/api/v1/health

# Check logs
docker-compose logs -f backend
```

Backend is now running on `localhost:8000` ✅

### 4. Setup Cloudflare Tunnel

#### Option A: Quick Tunnel (No account needed)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared
# or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

# Create tunnel
cloudflared tunnel --url http://localhost:8000

# You'll get a URL like: https://random-name.trycloudflare.com
```

#### Option B: Named Tunnel (Persistent)

```bash
# Login
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create documind-backend

# Configure tunnel (create config.yml)
cat > ~/.cloudflared/config.yml << EOF
tunnel: documind-backend
credentials-file: /Users/$(whoami)/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: documind-api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run documind-backend

# Or run as service (keeps running)
cloudflared service install
```

Your backend is now accessible at your Cloudflare tunnel URL! 🎉

### 5. Test Backend API

```bash
# Replace with your tunnel URL
BACKEND_URL=https://your-tunnel.trycloudflare.com

# Health check
curl $BACKEND_URL/api/v1/health

# API docs
open $BACKEND_URL/api/docs
```

## 🌐 Frontend Setup (Vercel)

### 1. Update Frontend Config

In your frontend code, create/update the API configuration:

**`frontend/src/config.js`** (create this file):

```javascript
export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";
```

**`frontend/.env.production`** (create this file):

```bash
VITE_API_URL=https://your-tunnel.trycloudflare.com
```

### 2. Update API Calls

Replace all hardcoded `http://localhost:8000` with the config:

```javascript
import { API_BASE_URL } from "./config";

// Before:
axios.get("http://localhost:8000/api/v1/auth/me");

// After:
axios.get(`${API_BASE_URL}/api/v1/auth/me`);
```

Or use environment variable directly:

```javascript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

### 3. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# From frontend directory
cd frontend
vercel

# Follow prompts, then deploy to production
vercel --prod
```

Or push to GitHub and connect repository in Vercel dashboard.

### 4. Configure Environment Variable in Vercel

In Vercel Dashboard:

1. Go to your project → Settings → Environment Variables
2. Add: `VITE_API_URL` = `https://your-tunnel.trycloudflare.com`
3. Redeploy

## 🔒 CORS Configuration

Update backend `.env` with your Vercel URL:

```bash
ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

Then restart Docker:

```bash
docker-compose restart backend
```

## 📝 Complete Workflow

### Development:

```bash
# Backend
docker-compose up -d

# Frontend (local)
cd frontend
npm run dev
# Uses http://localhost:8000
```

### Production:

**On Spare Laptop:**

```bash
# 1. Start backend
docker-compose up -d

# 2. Start Cloudflare tunnel
cloudflared tunnel --url http://localhost:8000
# Note the URL: https://random.trycloudflare.com

# 3. Keep terminal open (or use named tunnel as service)
```

**On Vercel:**

```bash
# 1. Set environment variable
VITE_API_URL=https://random.trycloudflare.com

# 2. Deploy
vercel --prod
```

## 🔧 Maintenance Commands

### Backend (Spare Laptop)

```bash
# View logs
docker-compose logs -f backend

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update backend
git pull
docker-compose build backend
docker-compose up -d
```

### Cloudflare Tunnel

```bash
# Check status
cloudflared tunnel info documind-backend

# View tunnel list
cloudflared tunnel list

# Restart tunnel
# Just Ctrl+C and run again for quick tunnel
# Or: sudo systemctl restart cloudflared for service
```

## 🐛 Troubleshooting

### CORS Errors

- Update `ALLOWED_ORIGINS` in backend `.env`
- Restart backend: `docker-compose restart backend`
- Check frontend is using HTTPS (Vercel)

### Tunnel Disconnects

- Quick tunnel disconnects often (use named tunnel for stability)
- Check laptop doesn't go to sleep
- Use `screen` or `tmux` to keep tunnel running

### Backend Not Accessible

```bash
# Check Docker
docker-compose ps

# Check logs
docker-compose logs backend

# Check tunnel
curl http://localhost:8000/api/v1/health
curl https://your-tunnel-url.trycloudflare.com/api/v1/health
```

### Frontend Can't Connect

- Check `VITE_API_URL` is set correctly
- Check Network tab in browser dev tools
- Verify CORS headers in response

## 💡 Pro Tips

### Keep Tunnel Running 24/7

```bash
# Use tmux/screen
tmux new -s cloudflare
cloudflared tunnel --url http://localhost:8000
# Detach: Ctrl+B, then D

# Or install as service (named tunnel)
cloudflared service install
```

### Monitor Backend

```bash
# View real-time logs
docker-compose logs -f backend | grep ERROR

# Check resource usage
docker stats
```

### Backup Data

```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --out=/data/backup

# Backup files
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ chroma_db/
```

## 🎯 Quick Reference

### Your URLs

- **Backend (local)**: http://localhost:8000
- **Backend (public)**: https://your-tunnel.trycloudflare.com
- **Frontend (local)**: http://localhost:5173
- **Frontend (prod)**: https://your-app.vercel.app

### Important Files

- **Backend Config**: `.env`
- **Frontend Config**: `frontend/.env.production`
- **Docker**: `docker-compose.yml`
- **Tunnel**: `~/.cloudflared/config.yml` (named tunnel)

### Key Commands

```bash
# Backend
docker-compose up -d              # Start
docker-compose logs -f backend    # Logs
docker-compose restart backend    # Restart

# Tunnel
cloudflared tunnel --url http://localhost:8000  # Quick
cloudflared tunnel run documind-backend         # Named

# Frontend
vercel --prod                     # Deploy
```

## ✅ Checklist

### Before Going Live:

- [ ] Backend running: `docker-compose ps`
- [ ] Health check works: `curl http://localhost:8000/api/v1/health`
- [ ] Cloudflare tunnel active
- [ ] Backend accessible via tunnel URL
- [ ] Frontend deployed to Vercel
- [ ] `VITE_API_URL` set in Vercel
- [ ] CORS configured with Vercel URL
- [ ] Test: Register → Login → Upload → Query

### Monitoring:

- [ ] Check backend logs daily
- [ ] Monitor disk space (uploads/chroma_db)
- [ ] Keep laptop plugged in
- [ ] Ensure laptop doesn't sleep

---

**You're all set! Your backend is now accessible via Cloudflare tunnel and your frontend on Vercel can communicate with it.** 🚀

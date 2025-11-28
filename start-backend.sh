#!/bin/bash

# Quick deployment script for DocuMind Backend

echo "🚀 DocuMind Backend - Quick Start"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Creating from template..."
    cp .env.docker .env
    echo ""
    echo "📝 Please edit .env and add:"
    echo "   1. Your GROQ_API_KEY"
    echo "   2. Generate JWT_SECRET_KEY: openssl rand -hex 32"
    echo "   3. Set ALLOWED_ORIGINS (your Vercel URL or * for testing)"
    echo ""
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🔍 Checking backend health..."
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend is running at http://localhost:8000"
else
    echo "⚠️  Backend might still be starting up"
    echo "   Check logs: docker-compose logs -f backend"
fi

echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "=================================="
echo "✅ Backend is ready!"
echo ""
echo "📌 Next Steps:"
echo "   1. Setup Cloudflare Tunnel:"
echo "      cloudflared tunnel --url http://localhost:8000"
echo ""
echo "   2. Note the tunnel URL (e.g., https://xyz.trycloudflare.com)"
echo ""
echo "   3. Update your Vercel frontend with this URL:"
echo "      VITE_API_URL=https://xyz.trycloudflare.com"
echo ""
echo "   4. Update CORS in .env with your Vercel URL:"
echo "      ALLOWED_ORIGINS=https://your-app.vercel.app"
echo "      Then: docker-compose restart backend"
echo ""
echo "📚 Full guide: See DEPLOYMENT_GUIDE.md"
echo "=================================="

#!/bin/bash
set -e

echo "🚀 Deploying to VPS..."

# Navigate to project
cd ~/DocuMind

# Fetch latest code
echo "📥 Fetching latest code from GitHub..."
git fetch origin

# Force reset to latest commit
echo "🔄 Resetting to latest code..."
git reset --hard origin/main

# Verify we have the latest commit
echo "✅ Current commit:"
git log -1 --oneline

# Verify auth route exists
echo "🔍 Checking if /me route exists..."
if grep -q "get_current_user_info" app/routes/auth.py; then
    echo "✅ /api/v1/auth/me route found!"
else
    echo "❌ ERROR: /api/v1/auth/me route NOT found!"
    exit 1
fi

# Stop containers
echo "🛑 Stopping containers..."
docker compose down

# Start containers
echo "▶️  Starting containers..."
docker compose up -d

# Wait for containers to be ready
echo "⏳ Waiting for backend to start..."
sleep 10

# Check health
echo "🏥 Checking backend health..."
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "Warning: Health check failed, but continuing..."

echo ""
echo "✅ Deployment complete!"
echo "🌐 Backend URL: http://145.223.18.238:8000"
echo ""
echo "Test the /me endpoint:"
echo "curl http://145.223.18.238:8000/api/v1/auth/me"

#!/bin/bash

# DocuMind Backend Docker Setup Script

set -e

echo "🚀 DocuMind Backend Docker Setup"
echo "================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo ""
    if [ -f .env.docker ]; then
        echo "Creating .env from .env.docker template..."
        cp .env.docker .env
        echo "✅ .env file created"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your:"
        echo "   - GROQ_API_KEY"
        echo "   - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
        echo ""
        read -p "Press Enter to continue after editing .env file..."
    else
        echo "❌ Error: .env.docker template not found"
        exit 1
    fi
fi

# Validate required environment variables
source .env

if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your_groq_api_key_here" ]; then
    echo "❌ Error: GROQ_API_KEY is not set in .env"
    echo "Please add your Groq API key to .env file"
    exit 1
fi

if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "your-super-secret-jwt-key-change-this-in-production" ]; then
    echo "❌ Error: JWT_SECRET_KEY is not set properly in .env"
    echo "Generate a secure key with: openssl rand -hex 32"
    exit 1
fi

echo "✅ Environment variables validated"
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads chroma_db logs
echo "✅ Directories created"
echo ""

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Error: Failed to build Docker image"
    exit 1
fi
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ Services started successfully"
else
    echo "❌ Error: Failed to start services"
    exit 1
fi
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed"
    echo "Check logs with: docker-compose logs backend"
fi
echo ""

# Display service status
echo "📊 Service Status:"
docker-compose ps
echo ""

# Display access information
echo "✅ DocuMind Backend is ready!"
echo ""
echo "🌐 Access Points:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/api/docs"
echo "   - Health Check: http://localhost:8000/api/v1/health"
echo ""
echo "📝 Useful Commands:"
echo "   - View logs: docker-compose logs -f backend"
echo "   - Stop services: docker-compose down"
echo "   - Restart: docker-compose restart"
echo ""
echo "📖 Full documentation: See DOCKER_DEPLOYMENT.md"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from loguru import logger
import sys

from app.config import settings
from app.services.database import MongoDB
from app.services.vector_db import ChromaDB
from app.routes import auth, chat, documents

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting DocuMind AI API...")

    try:
        await MongoDB.connect()
        logger.info("✓ MongoDB connected")

        logger.info(f"✓ ChromaDB initialized with {ChromaDB.get_collection_count()} embeddings")

        logger.info("✓ DocuMind AI API started successfully!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    logger.info("Shutting down DocuMind AI API...")
    await MongoDB.disconnect()
    logger.info("✓ MongoDB disconnected")


app = FastAPI(
    title="DocuMind AI",
    description="RAG-Powered Intelligent Document Query System with JWT Authentication",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded. Try again later.",
            "detail": str(exc.detail)
        }
    )

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/")
async def root():
    return {
        "name": "DocuMind AI",
        "version": "2.0.0",
        "description": "RAG-Powered Intelligent Document Query System",
        "status": "running",
        "endpoints": {
            "auth": "/api/v1/auth",
            "chat": "/api/v1/chat",
            "documents": "/api/v1/documents",
            "docs": "/api/docs"
        }
    }


@app.get("/api/v1/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "api": "running",
        "version": "2.0.0"
    }

    try:
        await MongoDB.client.admin.command('ping')
        health_status["mongodb"] = "connected"
    except Exception as e:
        health_status["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    try:
        count = ChromaDB.get_collection_count()
        health_status["chromadb"] = f"connected ({count} embeddings)"
    except Exception as e:
        health_status["chromadb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )

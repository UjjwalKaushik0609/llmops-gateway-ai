"""
Health check and system status endpoints.
"""
from datetime import datetime
from fastapi import APIRouter
from backend.database.connection import check_db_connection
from backend.memory.cache import check_redis_health
from backend.memory.vector_store import check_chroma_health
from backend.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check including all dependent services."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_health()
    chroma_ok = await check_chroma_health()

    services = {
        "database": "healthy" if db_ok else "unhealthy",
        "redis": "healthy" if redis_ok else "unhealthy",
        "chromadb": "healthy" if chroma_ok else "unhealthy",
    }

    overall = "healthy" if all([db_ok, redis_ok]) else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "services": services,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/")
async def root():
    """Root endpoint with platform info."""
    return {
        "platform": settings.app_name,
        "description": "Intelligent Multi-LLM Routing & Cost Management Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }

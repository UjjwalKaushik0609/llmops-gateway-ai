"""
LLMOps Gateway AI - Main Application Entry Point
"""
import time
import uuid
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database.connection import init_db
from backend.observability.metrics import metrics_endpoint

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.DEBUG if settings.debug else logging.INFO
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LLMOps Gateway AI", env=settings.app_env)
    await init_db()
    logger.info("All services initialized")
    yield
    logger.info("Shutting down LLMOps Gateway AI")


app = FastAPI(
    title="LLMOps Gateway AI",
    description="Intelligent Multi-LLM Routing, Token Optimization & Cost Management Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start_time = time.time()
    response = await call_next(request)
    duration = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration}ms"
    logger.info("HTTP request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=duration)
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Not found", "path": str(request.url.path)})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Unhandled exception", error=str(exc))
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ── Register all routes ────────────────────────────────────────────────────────
from backend.api.routes import health, auth, llm, analytics, keys, memory
from backend.api.routes import providers  # NEW: provider settings + test connection

app.include_router(health.router)
app.include_router(auth.router,      prefix=settings.api_v1_prefix)
app.include_router(llm.router,       prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)
app.include_router(keys.router,      prefix=settings.api_v1_prefix)
app.include_router(memory.router,    prefix=settings.api_v1_prefix)
app.include_router(providers.router, prefix=settings.api_v1_prefix)  # NEW


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    return await metrics_endpoint()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
"""Main FastAPI application for the Notification Service."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

# Internal modules
from src.config.settings import Settings
from src.routes import notifications, health
from src.utils.database import create_tables
from src.utils.redis_client import redis_client
from src.services.queue_service import queue_service

# 🌱 Declare global settings instance
settings: Settings | None = None

# ⚙️ Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO  # Will be updated after settings is loaded
)

logger = structlog.get_logger()

# 🔄 Lifespan events for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global settings
    settings = Settings()

    # Metadata setup
    app.title = settings.app_name
    app.version = settings.app_version
    app.description = "RideShare Pro Notification Service - Handles email and push notifications"
    app.debug = settings.debug
    app.docs_url = "/docs" if settings.debug else None
    app.redoc_url = "/redoc" if settings.debug else None
    app.openapi_url = "/openapi.json"

    # Dynamic logging level
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    logger.info("Starting Notification Service", version=settings.app_version)

    # 🔧 Startup routines
    redis_connected = False
    worker_task = None

    try:
        await create_tables()
        logger.info("Database initialized successfully")

        await redis_client.connect()
        redis_connected = True
        logger.info("Redis connected successfully")

        worker_task = asyncio.create_task(queue_service.start_worker())
        logger.info("Queue worker started")

        yield  # Run the app

    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise

    finally:
        logger.info("Shutting down Notification Service")

        if worker_task:
            await queue_service.stop_worker()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

        if redis_connected:
            await redis_client.disconnect()

        logger.info("Notification Service stopped")

# 🚀 Initialize FastAPI app
app = FastAPI(
    lifespan=lifespan,
    root_path="/api/notifications"
)

# 🌍 CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📜 Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = asyncio.get_event_loop().time()
    correlation_id = request.headers.get("x-correlation-id", f"req-{id(request)}")

    logger.info("HTTP request started", method=request.method, url=str(request.url), correlation_id=correlation_id)

    response = await call_next(request)

    duration = asyncio.get_event_loop().time() - start_time

    logger.info("HTTP request completed", method=request.method, url=str(request.url),
                status_code=response.status_code, duration=f"{duration:.3f}s", correlation_id=correlation_id)

    response.headers["x-correlation-id"] = correlation_id
    return response

# 🛑 Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("x-correlation-id", f"req-{id(request)}")

    logger.error("Unhandled exception", error=str(exc), correlation_id=correlation_id, exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "correlation_id": correlation_id,
            }
        },
        headers={"x-correlation-id": correlation_id},
    )

# 📦 Register routes
app.include_router(health.router)
app.include_router(notifications.router)

# 🧭 Root endpoint
@app.get("/")
async def root():
    if settings is None:
        return {"status": "booting"}
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }

# 🧨 Entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Avoid settings.debug here unless it’s loaded safely
        log_config=None,
    )

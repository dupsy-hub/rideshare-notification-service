"""Main FastAPI application for the Notification Service."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.config.settings import settings
from src.routes import notifications, health
from src.utils.database import create_tables
from src.utils.redis_client import redis_client
from src.services.queue_service import queue_service

# Configure structured logging
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

# Set up logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, settings.log_level.upper()),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Initialize variables
    worker_task = None
    redis_connected = False
    
    # Startup
    logger.info("Starting Notification Service", version=settings.app_version)
    
    try:
        # Initialize database
        await create_tables()
        logger.info("Database initialized successfully")
        
        # Connect to Redis
        await redis_client.connect()
        redis_connected = True
        logger.info("Redis connected successfully")
        
        # Start queue worker in background
        worker_task = asyncio.create_task(queue_service.start_worker())
        logger.info("Queue worker started")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Notification Service")
        
        # Stop queue worker if it was started
        if worker_task is not None:
            await queue_service.stop_worker()
            worker_task.cancel()
            
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect Redis if it was connected
        if redis_connected:
            await redis_client.disconnect()
        
        logger.info("Notification Service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RideShare Pro Notification Service - Handle email and push notifications",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = asyncio.get_event_loop().time()
    
    # Generate correlation ID
    correlation_id = request.headers.get("x-correlation-id", f"req-{id(request)}")
    
    # Log request
    logger.info(
        "HTTP request started",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id,
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = asyncio.get_event_loop().time() - start_time
    
    # Log response
    logger.info(
        "HTTP request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=f"{duration:.3f}s",
        correlation_id=correlation_id,
    )
    
    # Add correlation ID to response headers
    response.headers["x-correlation-id"] = correlation_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    correlation_id = request.headers.get("x-correlation-id", f"req-{id(request)}")
    
    logger.error(
        "Unhandled exception",
        error=str(exc),
        correlation_id=correlation_id,
        exc_info=True,
    )
    
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


# Include routers
app.include_router(health.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_config=None,  # Use our custom logging
    )
"""Health check routes."""

from datetime import datetime
from fastapi import APIRouter, status
from pydantic import BaseModel

from src.utils.database import health_check as db_health_check
from src.utils.redis_client import redis_client
from src.services.email_service import validate_email_config
from src.services.push_service import validate_push_config
from src.config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    timestamp: datetime
    version: str
    dependencies: dict


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    service: str
    timestamp: datetime
    version: str
    dependencies: dict
    checks: dict


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    # Check all dependencies
    db_status = await db_health_check()
    redis_status = await redis_client.health_check()
    
    # Determine overall status
    overall_status = "healthy" if db_status and redis_status else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        service="notification-service",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        dependencies={
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected"
        }
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with all service validations."""
    # Check all dependencies
    db_status = await db_health_check()
    redis_status = await redis_client.health_check()
    email_config_valid = await validate_email_config()
    push_config_valid = await validate_push_config()
    
    # Get queue stats
    try:
        queue_length = await redis_client.queue_length(settings.queue_name)
    except:
        queue_length = -1
    
    # Determine overall status
    critical_services = [db_status, redis_status]
    overall_status = "healthy" if all(critical_services) else "unhealthy"
    
    return DetailedHealthResponse(
        status=overall_status,
        service="notification-service",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        dependencies={
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected",
            "sendgrid": "configured" if email_config_valid else "not_configured",
            "firebase": "configured" if push_config_valid else "not_configured"
        },
        checks={
            "database_query": "success" if db_status else "failed",
            "redis_ping": "success" if redis_status else "failed",
            "queue_length": queue_length,
            "email_config": "valid" if email_config_valid else "invalid",
            "push_config": "valid" if push_config_valid else "invalid"
        }
    )

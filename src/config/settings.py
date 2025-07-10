"""Configuration settings for the Notification Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # SendGrid
    sendgrid_api_key: str
    sendgrid_from_email: str
    
    # Firebase
    firebase_credentials_path: str
    firebase_project_id: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    
    # App
    app_name: str = "RideShare Notification Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Queue
    queue_name: str = "notifications"
    worker_concurrency: int = 5
    retry_attempts: int = 3
    retry_delay: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
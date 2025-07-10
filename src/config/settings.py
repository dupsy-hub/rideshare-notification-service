"""Configuration settings for the Notification Service."""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(env="DATABASE_URL")

    @field_validator("database_url", mode="before")
    @classmethod
    def strip_database_url(cls, v):
        return v.strip() if isinstance(v, str) else v

    # Redis
    redis_url: str = Field(env="REDIS_URL")

    # SendGrid
    sendgrid_api_key: str = Field(env="SENDGRID_API_KEY")
    sendgrid_from_email: str = Field(env="SENDGRID_FROM_EMAIL")

    # Firebase
    firebase_credentials_path: str = Field(env="FIREBASE_CREDENTIALS_PATH")
    firebase_project_id: str = Field(env="FIREBASE_PROJECT_ID")

    # JWT
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=24, env="JWT_EXPIRE_HOURS")

    # App
    app_name: str = Field(default="RideShare Notification Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Queue
    queue_name: str = Field(default="notifications", env="QUEUE_NAME")
    worker_concurrency: int = Field(default=5, env="WORKER_CONCURRENCY")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    retry_delay: int = Field(default=60, env="RETRY_DELAY")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()

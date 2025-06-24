"""Redis client and connection management."""

import redis.asyncio as redis
import json
import logging
from typing import Optional, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for queue operations."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.aclose()
            logger.info("Disconnected from Redis")
    
    async def enqueue(self, queue_name: str, data: dict) -> bool:
        """Add job to queue."""
        try:
            if not self.redis:
                await self.connect()
            
            job_data = json.dumps(data)
            await self.redis.lpush(queue_name, job_data)
            logger.info(f"Job added to queue '{queue_name}': {data.get('notification_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            return False
    
    async def dequeue(self, queue_name: str, timeout: int = 0) -> Optional[dict]:
        """Get job from queue (blocking)."""
        try:
            if not self.redis:
                await self.connect()
            
            result = await self.redis.brpop(queue_name, timeout=timeout)
            if result:
                _, job_data = result
                return json.loads(job_data)
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None
    
    async def queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        try:
            if not self.redis:
                await self.connect()
            
            return await self.redis.llen(queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            if not self.redis:
                await self.connect()
            
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()
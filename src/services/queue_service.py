"""Queue service for processing notifications."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.notification import Notification, NotificationStatus
from src.utils.redis_client import redis_client
from src.utils.database import AsyncSessionLocal
from src.services.email_service import send_email
from src.services.push_service import send_push_notification

logger = logging.getLogger(__name__)


class NotificationQueueService:
    """Service for handling notification queue processing."""
    
    def __init__(self):
        self.running = False
    
    async def enqueue_notification(self, notification_id: uuid.UUID) -> bool:
        """Add notification to processing queue."""
        job_data = {
            "notification_id": str(notification_id),
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        return await redis_client.enqueue(settings.queue_name, job_data)
    
    async def process_notification(self, job_data: Dict[str, Any]) -> bool:
        """Process a single notification from the queue."""
        notification_id = job_data.get("notification_id")
        retry_count = job_data.get("retry_count", 0)
        
        if not notification_id:
            logger.error("Job missing notification_id")
            return False
        
        try:
            async with AsyncSessionLocal() as session:
                # Get notification from database
                result = await session.execute(
                    select(Notification).where(Notification.id == uuid.UUID(notification_id))
                )
                notification = result.scalar_one_or_none()
                
                if not notification:
                    logger.error(f"Notification {notification_id} not found")
                    return False
                
                if notification.status != NotificationStatus.PENDING:
                    logger.info(f"Notification {notification_id} already processed")
                    return True
                
                # Process based on type
                success = False
                error_message = None
                
                if notification.type == "email":
                    success, error_message = await send_email(
                        to_email=notification.recipient,
                        subject=notification.subject or "Notification",
                        content=notification.content
                    )
                elif notification.type == "push":
                    success, error_message = await send_push_notification(
                        device_token=notification.recipient,
                        title=notification.subject or "Notification",
                        body=notification.content
                    )
                else:
                    error_message = f"Unknown notification type: {notification.type}"
                    logger.error(error_message)
                
                # Update notification status
                if success:
                    await session.execute(
                        update(Notification)
                        .where(Notification.id == uuid.UUID(notification_id))
                        .values(
                            status=NotificationStatus.SENT,
                            sent_at=datetime.utcnow(),
                            error_message=None
                        )
                    )
                    logger.info(f"Notification {notification_id} sent successfully")
                else:
                    # Handle retry logic
                    if retry_count < settings.retry_attempts:
                        # Re-queue for retry
                        job_data["retry_count"] = retry_count + 1
                        await redis_client.enqueue(settings.queue_name, job_data)
                        logger.warning(f"Notification {notification_id} failed, retrying ({retry_count + 1}/{settings.retry_attempts})")
                    else:
                        # Mark as failed
                        await session.execute(
                            update(Notification)
                            .where(Notification.id == uuid.UUID(notification_id))
                            .values(
                                status=NotificationStatus.FAILED,
                                error_message=error_message
                            )
                        )
                        logger.error(f"Notification {notification_id} failed permanently: {error_message}")
                
                await session.commit()
                return success
                
        except Exception as e:
            logger.error(f"Error processing notification {notification_id}: {e}")
            return False
    
    async def start_worker(self):
        """Start queue worker to process notifications."""
        self.running = True
        logger.info("Starting notification queue worker")
        
        while self.running:
            try:
                # Get job from queue (blocking with timeout)
                job_data = await redis_client.dequeue(settings.queue_name, timeout=5)
                
                if job_data:
                    await self.process_notification(job_data)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def stop_worker(self):
        """Stop queue worker."""
        self.running = False
        logger.info("Stopping notification queue worker")
    
    async def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "queue_length": await redis_client.queue_length(settings.queue_name),
            "worker_running": self.running
        }


# Global queue service instance
queue_service = NotificationQueueService()
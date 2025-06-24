"""Main notification service combining all notification operations."""

import uuid
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import (
    Notification, 
    NotificationCreate, 
    NotificationResponse,
    NotificationSendResponse,
    NotificationStatus,
    NotificationType
)
from src.services.queue_service import queue_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Main service for handling notifications."""
    
    @staticmethod
    async def create_and_send_notification(
        session: AsyncSession,
        notification_data: NotificationCreate
    ) -> NotificationSendResponse:
        """
        Create a notification record and queue it for sending.
        
        Args:
            session: Database session
            notification_data: Notification data
            
        Returns:
            NotificationSendResponse with notification details
        """
        try:
            # Validate notification type and recipient
            if notification_data.type == NotificationType.EMAIL:
                if not _is_valid_email(notification_data.recipient):
                    raise ValueError("Invalid email address")
                if not notification_data.subject:
                    notification_data.subject = "Notification"
            
            elif notification_data.type == NotificationType.PUSH:
                if not notification_data.recipient:
                    raise ValueError("Device token cannot be empty")
            
            # Create notification record
            notification = Notification(
                user_id=notification_data.user_id,
                type=notification_data.type.value,
                recipient=notification_data.recipient,
                subject=notification_data.subject,
                content=notification_data.content,
                status=NotificationStatus.PENDING
            )
            
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            
            # Queue notification for processing
            queued = await queue_service.enqueue_notification(notification.id)
            
            if not queued:
                # Update status to failed if queueing failed
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Failed to queue notification"
                await session.commit()
                
                return NotificationSendResponse(
                    notification_id=notification.id,
                    status=NotificationStatus.FAILED,
                    message="Failed to queue notification for delivery"
                )
            
            logger.info(f"Notification {notification.id} created and queued successfully")
            
            return NotificationSendResponse(
                notification_id=notification.id,
                status=NotificationStatus.PENDING,
                message="Notification queued for delivery"
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create notification: {e}")
            raise
    
    @staticmethod
    async def get_user_notifications(
        session: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[NotificationResponse]:
        """
        Get notifications for a specific user.
        
        Args:
            session: Database session
            user_id: User ID
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip
            
        Returns:
            List of NotificationResponse objects
        """
        try:
            result = await session.execute(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(desc(Notification.created_at))
                .limit(limit)
                .offset(offset)
            )
            
            notifications = result.scalars().all()
            
            return [
                NotificationResponse.from_orm(notification)
                for notification in notifications
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            raise
    
    @staticmethod
    async def get_notification_by_id(
        session: AsyncSession,
        notification_id: uuid.UUID
    ) -> Optional[NotificationResponse]:
        """
        Get a specific notification by ID.
        
        Args:
            session: Database session
            notification_id: Notification ID
            
        Returns:
            NotificationResponse or None if not found
        """
        try:
            result = await session.execute(
                select(Notification)
                .where(Notification.id == notification_id)
            )
            
            notification = result.scalar_one_or_none()
            
            if notification:
                return NotificationResponse.from_orm(notification)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get notification by ID: {e}")
            raise
    
    @staticmethod
    async def get_notification_stats(session: AsyncSession) -> dict:
        """
        Get notification statistics.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with notification statistics
        """
        try:
            # Get counts by status
            pending_result = await session.execute(
                select(Notification)
                .where(Notification.status == NotificationStatus.PENDING)
            )
            pending_count = len(pending_result.scalars().all())
            
            sent_result = await session.execute(
                select(Notification)
                .where(Notification.status == NotificationStatus.SENT)
            )
            sent_count = len(sent_result.scalars().all())
            
            failed_result = await session.execute(
                select(Notification)
                .where(Notification.status == NotificationStatus.FAILED)
            )
            failed_count = len(failed_result.scalars().all())
            
            # Get queue stats
            queue_stats = await queue_service.get_queue_stats()
            
            return {
                "pending": pending_count,
                "sent": sent_count,
                "failed": failed_count,
                "total": pending_count + sent_count + failed_count,
                "queue_length": queue_stats["queue_length"],
                "worker_running": queue_stats["worker_running"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            raise


def _is_valid_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
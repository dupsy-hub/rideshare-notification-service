"""Notification database models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


class NotificationType(str, Enum):
    """Notification type enumeration."""
    EMAIL = "email"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    """Notification database model."""
    
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(String(20), nullable=False)
    recipient = Column(String(255), nullable=False)  # email or device token
    subject = Column(String(200), nullable=True)  # for emails only
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_notifications_user_id', 'user_id'),
        Index('idx_notifications_status', 'status'),
        Index('idx_notifications_type', 'type'),
        Index('idx_notifications_created_at', 'created_at'),
    )


# Pydantic models for API requests/responses
class NotificationCreate(BaseModel):
    """Request model for creating a notification."""
    user_id: uuid.UUID
    type: NotificationType
    recipient: str
    subject: Optional[str] = None
    content: str


class NotificationResponse(BaseModel):
    """Response model for notification."""
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    recipient: str
    subject: Optional[str]
    content: str
    status: str
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class NotificationSendResponse(BaseModel):
    """Response model for sending notification."""
    notification_id: uuid.UUID
    status: str
    sent_at: Optional[datetime] = None
    message: str = "Notification queued for delivery"
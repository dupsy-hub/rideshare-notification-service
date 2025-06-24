"""Notification API routes."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationSendResponse
)
from src.services.notification_service import NotificationService
from src.utils.database import get_database
from src.utils.auth import get_current_user_id, TokenData, get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/send", response_model=NotificationSendResponse)
async def send_notification(
    notification: NotificationCreate,
    session: AsyncSession = Depends(get_database),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Send a notification (email or push).
    
    - **user_id**: Target user ID for the notification
    - **type**: Notification type (email or push)
    - **recipient**: Email address or device token
    - **subject**: Email subject (required for email notifications)
    - **content**: Notification content/body
    """
    try:
        # Validate that user can send notifications (basic auth check)
        if not current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Send the notification
        result = await NotificationService.create_and_send_notification(
            session=session,
            notification_data=notification
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.get("/history", response_model=List[NotificationResponse])
async def get_notification_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database)
):
    """
    Get notification history for the current user.
    
    - **limit**: Maximum number of notifications to return (1-100)
    - **offset**: Number of notifications to skip
    """
    try:
        notifications = await NotificationService.get_user_notifications(
            session=session,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification history"
        )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_database),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a specific notification by ID.
    
    - **notification_id**: The ID of the notification to retrieve
    """
    try:
        notification = await NotificationService.get_notification_by_id(
            session=session,
            notification_id=notification_id
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Basic authorization: users can only see their own notifications
        # In a real app, you might want more sophisticated authorization
        if notification.user_id != current_user.user_id:
            # Allow service accounts or admins to view any notification
            if current_user.role not in ["admin", "service"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification"
        )


@router.get("/admin/stats")
async def get_notification_stats(
    session: AsyncSession = Depends(get_database),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get notification statistics (admin only).
    
    Returns counts of notifications by status and queue information.
    """
    try:
        # Basic admin check
        if current_user.role not in ["admin", "service"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        stats = await NotificationService.get_notification_stats(session=session)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification statistics"
        )
"""Push notification service using Firebase Cloud Messaging."""

import logging
from typing import Tuple
import firebase_admin
from firebase_admin import credentials, messaging
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None


def _initialize_firebase():
    """Initialize Firebase Admin SDK."""
    global _firebase_app
    
    if _firebase_app is None:
        try:
            # Initialize with service account credentials
            cred = credentials.Certificate(settings.firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': settings.firebase_project_id,
            })
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise
    
    return _firebase_app


async def send_push_notification(device_token: str, title: str, body: str) -> Tuple[bool, str]:
    """
    Send push notification via Firebase Cloud Messaging.
    
    Args:
        device_token: FCM device token
        title: Notification title
        body: Notification body
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Ensure Firebase is initialized
        _initialize_firebase()
        
        # Create the message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon='ic_notification',
                    color='#FF6B35'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        badge=1,
                        sound='default'
                    )
                )
            )
        )
        
        # Send the message
        response = messaging.send(message)
        
        logger.info(f"Push notification sent successfully to {device_token[:20]}...")
        return True, ""
        
    except messaging.InvalidArgumentError as e:
        error_msg = f"Invalid FCM argument: {str(e)}"
        logger.error(f"Failed to send push notification: {error_msg}")
        return False, error_msg
        
    except messaging.UnregisteredError as e:
        error_msg = f"Unregistered device token: {str(e)}"
        logger.error(f"Failed to send push notification: {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Push notification failed: {str(e)}"
        logger.error(f"Failed to send push notification: {error_msg}")
        return False, error_msg


async def validate_push_config() -> bool:
    """Validate Firebase configuration."""
    try:
        if not settings.firebase_credentials_path or not settings.firebase_project_id:
            logger.error("Firebase configuration missing")
            return False
        
        # Try to initialize Firebase
        _initialize_firebase()
        return True
        
    except Exception as e:
        logger.error(f"Firebase configuration validation failed: {e}")
        return False


async def send_batch_push_notifications(tokens_and_messages: list) -> Tuple[int, int, list]:
    """
    Send multiple push notifications in batch.
    
    Args:
        tokens_and_messages: List of tuples (device_token, title, body)
    
    Returns:
        Tuple of (success_count: int, failure_count: int, failed_tokens: list)
    """
    try:
        # Ensure Firebase is initialized
        _initialize_firebase()
        
        messages = []
        for device_token, title, body in tokens_and_messages:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=device_token,
            )
            messages.append(message)
        
        # Send batch
        response = messaging.send_all(messages)
        
        failed_tokens = []
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                failed_tokens.append(tokens_and_messages[idx][0])
        
        logger.info(f"Batch push notifications: {response.success_count} sent, {response.failure_count} failed")
        return response.success_count, response.failure_count, failed_tokens
        
    except Exception as e:
        logger.error(f"Batch push notification failed: {e}")
        return 0, len(tokens_and_messages), [t[0] for t in tokens_and_messages]
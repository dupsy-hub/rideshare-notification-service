"""Email service using SendGrid."""

import logging
from typing import Tuple
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent, PlainTextContent
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize SendGrid client
sendgrid_client = SendGridAPIClient(api_key=settings.sendgrid_api_key)


async def send_email(to_email: str, subject: str, content: str) -> Tuple[bool, str]:
    """
    Send email via SendGrid.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        content: Email content (HTML or plain text)
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Create the email message
        message = Mail(
            from_email=From(settings.sendgrid_from_email),
            to_emails=To(to_email),
            subject=Subject(subject),
            html_content=HtmlContent(content)
        )
        
        # Send the email
        response = sendgrid_client.send(message)
        
        # Check response status
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent successfully to {to_email}")
            return True, ""
        else:
            error_msg = f"SendGrid API error: Status {response.status_code}"
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Email sending failed: {str(e)}"
        logger.error(f"Failed to send email to {to_email}: {error_msg}")
        return False, error_msg


async def validate_email_config() -> bool:
    """Validate SendGrid configuration."""
    try:
        if not settings.sendgrid_api_key or not settings.sendgrid_from_email:
            logger.error("SendGrid configuration missing")
            return False
        
        # Test API key by making a simple request
        # Note: This is a basic validation, you might want to implement a more thorough check
        return True
        
    except Exception as e:
        logger.error(f"SendGrid configuration validation failed: {e}")
        return False
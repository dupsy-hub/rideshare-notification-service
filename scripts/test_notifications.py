#!/usr/bin/env python3
"""Test script for notification service."""

import sys
import uuid
import asyncio
import json
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import httpx
from dotenv import load_dotenv
from src.utils.auth import create_access_token

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"


def create_test_token():
    """Create a test JWT token."""
    test_user_data = {
        "user_id": str(uuid.uuid4()),
        "email": "test@rideshare.com",
        "role": "admin"
    }
    return create_access_token(test_user_data)


async def test_health_check():
    """Test health check endpoint."""
    print("🏥 Testing health check...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health/")
        
        if response.status_code == 200:
            print("✅ Health check passed")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(response.text)
            return False


async def test_send_email():
    """Test sending an email notification."""
    print("📧 Testing email notification...")
    
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    notification_data = {
        "user_id": str(uuid.uuid4()),
        "type": "email",
        "recipient": "test@example.com",
        "subject": "Test Email from RideShare",
        "content": "This is a test email notification from the RideShare platform."
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/notifications/send",
            json=notification_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Email notification queued successfully")
            print(json.dumps(response.json(), indent=2))
            return response.json()["notification_id"]
        else:
            print(f"❌ Email notification failed: {response.status_code}")
            print(response.text)
            return None


async def test_send_push():
    """Test sending a push notification."""
    print("📱 Testing push notification...")
    
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    notification_data = {
        "user_id": str(uuid.uuid4()),
        "type": "push",
        "recipient": "fake-device-token-for-testing",
        "subject": "Test Push Notification",
        "content": "This is a test push notification from RideShare!"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/notifications/send",
            json=notification_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Push notification queued successfully")
            print(json.dumps(response.json(), indent=2))
            return response.json()["notification_id"]
        else:
            print(f"❌ Push notification failed: {response.status_code}")
            print(response.text)
            return None


async def test_get_notification(notification_id: str):
    """Test getting a notification by ID."""
    print(f"🔍 Testing get notification {notification_id}...")
    
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/notifications/{notification_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Got notification successfully")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Get notification failed: {response.status_code}")
            print(response.text)
            return False


async def test_get_stats():
    """Test getting notification statistics."""
    print("📊 Testing notification statistics...")
    
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/notifications/admin/stats",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Got statistics successfully")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Get statistics failed: {response.status_code}")
            print(response.text)
            return False


async def main():
    """Run all tests."""
    print("🧪 Starting Notification Service Tests")
    print("=" * 50)
    
    # Test health check first
    if not await test_health_check():
        print("❌ Service is not healthy, stopping tests")
        return
    
    print()
    
    # Test sending email
    email_id = await test_send_email()
    print()
    
    # Test sending push notification
    push_id = await test_send_push()
    print()
    
    # Wait a moment for processing
    print("⏳ Waiting for notifications to process...")
    await asyncio.sleep(2)
    
    # Test getting notifications
    if email_id:
        await test_get_notification(email_id)
        print()
    
    if push_id:
        await test_get_notification(push_id)
        print()
    
    # Test statistics
    await test_get_stats()
    
    print()
    print("🎉 Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
# 🔔 RideShare Pro - Notification Service

A production-ready notification service for the RideShare Pro platform, built with **FastAPI**, **Redis queuing**, and **PostgreSQL**. Supports email notifications via SendGrid and push notifications via Firebase.

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  Redis Queue    │────│ Background      │
│  (REST API)     │    │  (Async Jobs)   │    │ Worker Process  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                       │
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   SendGrid      │    │   Firebase      │
│   (Database)    │    │   (Email)       │    │   (Push)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Features**

- ✅ **Email Notifications** - SendGrid integration with HTML support
- ✅ **Push Notifications** - Firebase Cloud Messaging for mobile apps
- ✅ **Redis Queue Processing** - Async background job processing with retries
- ✅ **JWT Authentication** - Secure API access with role-based permissions
- ✅ **Health Checks** - Kubernetes-ready liveness and readiness probes
- ✅ **Structured Logging** - JSON logging with correlation IDs
- ✅ **Docker Support** - Multi-stage builds for production deployment
- ✅ **Auto-retry Logic** - Failed notifications automatically retried
- ✅ **Notification History** - Track all sent notifications per user

## 📦 **Quick Start**

### **Prerequisites**

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- SendGrid account & API key
- Firebase project & service account credentials

### **1. Clone & Setup**

```bash
# Run the setup script
chmod +x setup_notification_service.sh
./setup_notification_service.sh

cd rideshare-notification-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration**

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rideshare_notifications

# Redis
REDIS_URL=redis://localhost:6379/0

# SendGrid
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@rideshare.com

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_PROJECT_ID=your-firebase-project

# JWT
JWT_SECRET_KEY=your-super-secret-key
```

### **3. Database Setup**

```bash
# Initialize database tables
python scripts/init_db.py
```

### **4. Start Services**

**Option A: Local Development**

```bash
# Start dependencies
docker-compose up postgres redis -d

# Run the service
python scripts/run_dev.py
```

**Option B: Full Docker**

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f notification-service
```

### **5. Test the Service**

```bash
# Run test suite
python scripts/test_notifications.py

# Check API documentation
curl http://localhost:8000/docs
```

## 📋 **API Reference**

### **Authentication**

All endpoints require JWT authentication except health checks:

```bash
Authorization: Bearer <jwt_token>
```

### **Core Endpoints**

#### **Send Notification**

```http
POST /api/notifications/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "type": "email",
  "recipient": "user@example.com",
  "subject": "Welcome to RideShare!",
  "content": "Thank you for joining our platform."
}
```

#### **Get Notification History**

```http
GET /api/notifications/history?limit=50&offset=0
Authorization: Bearer <token>
```

#### **Get Notification Details**

```http
GET /api/notifications/{notification_id}
Authorization: Bearer <token>
```

#### **Health Check**

```http
GET /health/
GET /health/detailed
GET /health/ready    # Kubernetes readiness probe
GET /health/live     # Kubernetes liveness probe
```

### **Notification Types**

| Type    | Description       | Required Fields                           |
| ------- | ----------------- | ----------------------------------------- |
| `email` | Send via SendGrid | `recipient` (email), `subject`, `content` |
| `push`  | Send via Firebase | `recipient` (device_token), `content`     |

## 🔧 **Development**

### **Project Structure**

```
rideshare-notification-service/
├── src/
│   ├── config/          # Configuration settings
│   ├── models/          # Database models & Pydantic schemas
│   ├── routes/          # FastAPI route handlers
│   ├── services/        # Business logic & external integrations
│   ├── utils/           # Database, Redis, Auth utilities
│   └── main.py          # FastAPI application
├── scripts/             # Development & deployment scripts
├── tests/               # Test suite
├── docs/                # Documentation
├── Dockerfile           # Container image
├── docker-compose.yml   # Local development stack
└── requirements.txt     # Python dependencies
```

### **Adding New Notification Types**

1. **Update the enum** in `src/models/notification.py`:

```python
class NotificationType(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"  # New type
```

2. **Create service handler** in `src/services/`:

```python
# src/services/sms_service.py
async def send_sms(phone: str, message: str) -> Tuple[bool, str]:
    # Implementation here
    pass
```

3. **Update queue processor** in `src/services/queue_service.py`:

```python
elif notification.type == "sms":
    success, error_message = await send_sms(
        phone=notification.recipient,
        message=notification.content
    )
```

### **Testing**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_notifications.py

# Run integration tests
python scripts/test_notifications.py
```

### **Code Quality**

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/
```

## 🐳 **Docker Deployment**

### **Build Image**

```bash
# Build production image
docker build -t rideshare/notification-service:latest .

# Multi-architecture build
docker buildx build --platform linux/amd64,linux/arm64 \
  -t rideshare/notification-service:latest .
```

### **Environment Variables**

```yaml
# docker-compose.override.yml
services:
  notification-service:
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
      - REDIS_URL=redis://redis:6379/0
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - FIREBASE_CREDENTIALS_PATH=/app/firebase-creds.json
    volumes:
      - ./firebase-credentials.json:/app/firebase-creds.json:ro
```

## 📊 **Monitoring & Observability**

### **Health Checks**

- **Basic**: `GET /health/` - Service status with dependencies
- **Detailed**: `GET /health/detailed` - Full system diagnostics
- **Kubernetes**: `/health/ready` and `/health/live` endpoints

### **Logging**

Structured JSON logs with correlation IDs:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level": "info",
  "logger": "notification_service",
  "message": "Notification sent successfully",
  "notification_id": "123e4567-e89b-12d3-a456-426614174000",
  "correlation_id": "req-456789"
}
```

### **Key Metrics**

Monitor these metrics for production health:

- **Queue Length**: `GET /api/notifications/admin/stats`
- **Success/Failure Rates**: Database notification status counts
- **Processing Time**: Queue job processing duration
- **External API Health**: SendGrid/Firebase response times

## 🚨 **Troubleshooting**

### **Common Issues**

**Queue Not Processing Jobs**

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Check queue length
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/notifications/admin/stats
```

**Database Connection Errors**

```bash
# Test database connectivity
python scripts/init_db.py

# Check PostgreSQL logs
docker-compose logs postgres
```

**SendGrid/Firebase Errors**

```bash
# Check configuration
curl http://localhost:8000/health/detailed

# Test external APIs manually
python -c "
from src.services.email_service import validate_email_config
import asyncio
print(asyncio.run(validate_email_config()))
"
```

### **Performance Tuning**

**High Queue Backlog**

- Increase `WORKER_CONCURRENCY` setting
- Scale horizontally with multiple service instances
- Optimize external API timeouts

**Database Performance**

- Monitor slow queries in PostgreSQL logs
- Add indexes for frequently queried fields
- Consider read replicas for notification history

## 🔐 **Security Considerations**

- **JWT Secrets**: Use strong, unique keys for production
- **API Keys**: Store SendGrid/Firebase credentials securely
- **Database**: Use connection encryption and strong passwords
- **Rate Limiting**: Implement per-user rate limits for production
- **Input Validation**: All inputs are validated and sanitized

## 📈 **Scaling Guidelines**

**Horizontal Scaling**

- Service is stateless - add more instances behind load balancer
- Use shared Redis and PostgreSQL instances
- Configure proper health checks for Kubernetes HPA

**Vertical Scaling**

- Increase `WORKER_CONCURRENCY` for more queue throughput
- Allocate more CPU for background job processing
- Scale database connections based on worker count

**Queue Management**

- Monitor queue depth and processing times
- Implement dead letter queues for failed jobs
- Consider message partitioning for high throughput

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run quality checks: `black`, `isort`, `flake8`, `pytest`
5. Submit pull request

## 📄 **License**

This project is part of the RideShare Pro microservices platform.

---

**🎯 Ready to handle millions of notifications!** 🚀

# ------------ Builder Stage ------------
FROM python:3.11-slim AS builder

# Set environment variables for cleaner, faster builds
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building packages
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt


# ------------ Production Stage ------------
FROM python:3.11-slim AS production

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install minimal runtime dependencies
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/

# Set appropriate permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Define health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dewey Backend Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Install dev dependencies
COPY pyproject.toml .
RUN pip install -e ".[dev]"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Create non-root user
RUN groupadd -r dewey && useradd -r -g dewey dewey

# Install only production dependencies
COPY pyproject.toml .
RUN pip install .

# Copy application code
COPY --chown=dewey:dewey . .

# Switch to non-root user
USER dewey

# Expose port
EXPOSE 8000

# Run with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

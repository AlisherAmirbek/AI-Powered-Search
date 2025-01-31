FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=2345

# Create app directory and user
RUN useradd -m appuser && \
    mkdir -p /app/data

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY build/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:$PORT/health || exit 1

# Expose and run the application
EXPOSE $PORT
CMD ["python", "main.py"]

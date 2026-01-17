# Use Python 3.10 slim image for smaller footprint
FROM python:3.10-slim

# Set metadata labels
LABEL maintainer="Trading Bot Team"
LABEL description="Mean Reversion Trading Bot for Binance Futures"

# Set environment variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr (for real-time logging)
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# These are required for some Python packages (numpy, pandas, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
# This layer will only rebuild if requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . .

# Create logs directory inside container
RUN mkdir -p /app/logs

# Create a non-root user for security (recommended for production)
# This prevents the container from running as root
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Health check (optional but recommended)
# This allows Docker to monitor if the container is healthy
# Adjust the interval and timeout as needed
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/logs') else 1)"

# Default command to run the production bot
CMD ["python", "bot_mean_reversion_production.py"]

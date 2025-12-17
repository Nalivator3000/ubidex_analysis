FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY 07_scripts/ ./scripts/
COPY README.md .

# Create directories for database and output
RUN mkdir -p /data /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/data/events.db

# Default command (can be overridden in docker-compose)
CMD ["python", "--version"]


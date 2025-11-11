# 🤖 VibeJobHunter - Autonomous Job Hunting Engine
# Optimized for Railway.app deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (minimal for web scraping)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/autonomous_data \
    /app/logs \
    /app/tailored_resumes \
    /app/cover_letters \
    /app/autonomous_data/cache && \
    chmod -R 777 /app/autonomous_data \
    /app/logs \
    /app/tailored_resumes \
    /app/cover_letters

# Copy entrypoint script
COPY railway-entrypoint.sh /app/railway-entrypoint.sh
RUN chmod +x /app/railway-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Entrypoint
ENTRYPOINT ["/app/railway-entrypoint.sh"]

# 🤖 VibeJobHunter - Autonomous Job Hunting Engine
# Optimized for Railway.app deployment
# v4.0 - AI CO-FOUNDER EDITION - Build: Nov 23, 2025 20:58 UTC

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Cache buster for Railway - forces fresh rebuild
ENV BUILD_VERSION=4.2_PLAYWRIGHT_ATS
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BUILD_TIMESTAMP=20251217_220000
ENV GIT_COMMIT=d43c9e3
ENV STRATEGIC_CAPABILITIES=true

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (including Playwright browser requirements)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to save space)
RUN playwright install chromium && \
    echo "✅ Playwright Chromium installed"

# Copy application code (v4.0 AI CO-FOUNDER - Cache bust timestamp: 2025-11-23 21:30)
# Force rebuild: Changing this comment breaks Docker cache layer
COPY . .
RUN find /app -type f -name "*.pyc" -delete && find /app -type d -name "__pycache__" -delete
RUN echo "🔥 COPIED FRESH CODE - v4.0 AI CO-FOUNDER - Build: $(date)" && \
    ls -la src/notifications/ && \
    echo "Checking for linkedin_cmo_v4.py:" && \
    test -f src/notifications/linkedin_cmo_v4.py && echo "✅ AI Co-Founder file exists!" || echo "❌ File missing!"

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

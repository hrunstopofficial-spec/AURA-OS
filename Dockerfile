# JARVIS Core 24/7 Autonomous Cloud Daemon
FROM python:3.11-slim

# Prevent interactive prompts & bufferless output
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (ffmpeg for voice notes, curl, git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    beautifulsoup4 \
    requests \
    qrcode \
    Pillow \
    google-auth \
    google-auth-oauthlib \
    google-api-python-client \
    reportlab

# Copy codebase
COPY . .

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; exit(0)"

# Start 24/7 Telegram Bridge Daemon in background AND Uvicorn Web Server on $PORT
CMD sh -c "python -u tools/telegram_bridge.py & exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"

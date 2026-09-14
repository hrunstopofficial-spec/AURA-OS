#!/usr/bin/env bash
# AURA-OS Cloud Server Startup Script
# Automatically launches 24/7 Telegram Bridge Daemon alongside Uvicorn Web Engine

echo "========================================================"
echo "🚀 AURA-OS: Starting 24/7 Telegram Bridge Daemon in BG..."
echo "========================================================"
python -u tools/telegram_bridge.py &
TELEGRAM_PID=$!
echo "✅ Telegram Bridge Daemon active with PID: $TELEGRAM_PID"

echo "========================================================"
echo "⚡ AURA-OS: Starting FastAPI Production Web Server..."
echo "========================================================"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

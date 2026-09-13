#!/usr/bin/env bash
# ==============================================================================
# JARVIS 24/7 CLOUD SERVER 1-CLICK INSTALLER
# Works on Ubuntu 22.04 / 24.04 LTS (Oracle Cloud Free, DigitalOcean, Hetzner, AWS)
# ==============================================================================

set -e

echo "🚀 Starting JARVIS 24/7 Cloud Server Deployment..."

# 1. Update OS packages
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg curl

# 2. Setup Working Directory
APP_DIR="/root/jarvis-core"
if [ ! -d "$APP_DIR" ]; then
    echo "Cloning JARVIS repository..."
    # If deploying from GitHub, replace with Mukil's repo:
    # git clone <YOUR_GIT_REPO_URL> $APP_DIR
    mkdir -p $APP_DIR
fi

cd $APP_DIR

# 3. Install Python Dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
pip3 install google-auth google-auth-oauthlib google-api-python-client reportlab

# 4. Configure Systemd 24/7 Background Service
echo "⚙️ Setting up systemd 24/7 background service..."
sudo cp systemd/jarvis.service /etc/systemd/system/jarvis.service
sudo systemctl daemon-reload
sudo systemctl enable jarvis.service
sudo systemctl restart jarvis.service

# 5. Status Check
sleep 3
sudo systemctl status jarvis.service --no-pager

echo ""
echo "🎉 JARVIS IS NOW RUNNING 24/7 ON YOUR CLOUD SERVER!"
echo "• Check live logs: journalctl -u jarvis.service -f"
echo "• Restart service: sudo systemctl restart jarvis.service"
echo "• Stop service:    sudo systemctl stop jarvis.service"

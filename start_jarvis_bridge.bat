@echo off
title JARVIS Cloud-PC WebSocket Bridge Worker
cd /d "C:\Users\mukil\jarvis-core"
echo ========================================================
echo 🌌 JARVIS CLOUD ⟷ LOCAL PC AUTONOMOUS BRIDGE WORKER
echo ========================================================
echo Connecting to Render Cloud: wss://aura-os-n6n3.onrender.com
python start_pc_bridge_worker.py
pause

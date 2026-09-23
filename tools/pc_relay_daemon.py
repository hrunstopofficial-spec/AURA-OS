"""
AURA-OS Local PC Relay Daemon
tools/pc_relay_daemon.py - Persistent background worker running on Mukil's Windows PC.
Connects to Render Cloud WebSocket Hub, executes Antigravity CLI and PC tools,
and returns live results + screenshot proofs to Telegram/Cloud.
"""
import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.antigravity_bridge import run_antigravity_task
from tools.pc_tools import (
    run_powershell,
    take_pc_screenshot,
    open_browser_url,
    play_youtube_song,
    get_system_telemetry,
    set_system_volume,
    set_screen_brightness,
    lock_workstation,
    auto_apply_job
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (PCRelayDaemon) %(message)s"
)
logger = logging.getLogger("PCRelayDaemon")

DEFAULT_CLOUD_WS_URL = os.getenv(
    "AURA_CLOUD_WS_URL",
    "wss://aura-os-n6n3.onrender.com/api/v1/bridge/ws?worker_id=mukil_pc&token=mukil-aura-pc-bridge-secret-2026"
)
LOCAL_DEV_WS_URL = "ws://localhost:8000/api/v1/bridge/ws?worker_id=mukil_pc&token=mukil-aura-pc-bridge-secret-2026"


class PCRelayDaemon:
    def __init__(self, ws_url: Optional[str] = None):
        self.ws_url = ws_url or DEFAULT_CLOUD_WS_URL
        self.is_running = True
        self.current_ws = None

    async def execute_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches incoming cloud task to appropriate local PC subsystem."""
        task_id = task_payload.get("task_id", f"task_{int(time.time())}")
        task_type = task_payload.get("type", "EXECUTE_INTENT")
        command = (task_payload.get("command") or "").strip()
        params = task_payload.get("parameters", {})

        logger.info(f"⚡ Received Task [{task_id}] Type='{task_type}': '{command[:80]}'")
        start_t = time.time()
        output_text = ""
        photo_path = None
        status = "COMPLETED"

        try:
            # 1. ANTIGRAVITY CODING TASK
            if task_type in ["ANTIGRAVITY_PROMPT", "CODE", "AGY"] or any(k in command.lower() for k in ["agy", "antigravity", "write code", "refactor"]):
                logger.info(f"Spawning Antigravity CLI for: {command[:60]}")
                agy_res = run_antigravity_task(command)
                output_text = agy_res.get("output_preview", "Antigravity task completed.")
                if agy_res.get("drive_link"):
                    output_text += f"\n\n📁 Drive Report: {agy_res['drive_link']}"
                if not agy_res.get("success"):
                    status = "FAILED"

            # 2. POWERSHELL COMMAND
            elif task_type == "POWERSHELL" or command.startswith("powershell ") or command.startswith("Get-") or command.startswith("dir "):
                cmd_clean = command.replace("powershell ", "", 1) if command.startswith("powershell ") else command
                output_text = run_powershell(cmd_clean)

            # 3. SCREENSHOT
            elif task_type == "SCREENSHOT" or "screenshot" in command.lower():
                shot = take_pc_screenshot()
                photo_path = shot
                output_text = f"PC Screenshot captured: {os.path.basename(shot) if shot else 'Failed'}"

            # 4. BROWSER OPEN
            elif "open " in command.lower() and ("http" in command.lower() or ".com" in command.lower()):
                words = command.split()
                target_url = next((w for w in words if "http" in w or ".com" in w), "https://google.com")
                output_text = open_browser_url(target_url)

            # 5. YOUTUBE MUSIC
            elif "play " in command.lower() and "youtube" in command.lower():
                query = command.lower().replace("play ", "").replace("on youtube", "").strip()
                output_text = play_youtube_song(query)

            # 6. SYSTEM VITALS
            elif any(k in command.lower() for k in ["vitals", "battery", "cpu", "ram", "hardware"]):
                telemetry = get_system_telemetry()
                output_text = (
                    f"🔋 Battery: {telemetry['battery']['percentage']}%\n"
                    f"⚡ CPU: {telemetry['cpu']['percentage']}%\n"
                    f"🧠 RAM: {telemetry['ram']['percentage']}% ({telemetry['ram']['used_gb']}GB / {telemetry['ram']['total_gb']}GB)\n"
                    f"💾 Disk: {telemetry['disk']['percentage']}% ({telemetry['disk']['free_gb']}GB free)\n"
                    f"🔊 Volume: {telemetry['volume']}"
                )

            # 7. LOCK PC
            elif "lock" in command.lower() and "pc" in command.lower():
                output_text = lock_workstation()

            # 8. GENERAL INTENT VIA AGENT BRAIN
            else:
                try:
                    from app.tools.agent_brain import AutonomousAgentBrain
                    brain = AutonomousAgentBrain()
                    res_text, shot = await brain.process_user_intent(user_input=command, user_name="Mukil")
                    output_text = res_text
                    photo_path = shot
                except Exception as brain_err:
                    # Fallback to Antigravity CLI
                    agy_res = run_antigravity_task(command)
                    output_text = agy_res.get("output_preview", f"Executed: {command}")

        except Exception as e:
            logger.error(f"Task [{task_id}] execution failed: {e}", exc_info=True)
            status = "FAILED"
            output_text = f"Local execution error: {str(e)}"

        elapsed_ms = round((time.time() - start_t) * 1000, 2)
        return {
            "task_id": task_id,
            "status": status,
            "output_text": output_text,
            "photo_path": photo_path,
            "execution_time_ms": elapsed_ms,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

    async def run(self):
        """Persistent connection loop with exponential backoff."""
        import websockets

        backoff = 3
        while self.is_running:
            try:
                logger.info(f"Connecting to Cloud Bridge: {self.ws_url.split('?')[0]}...")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10
                ) as ws:
                    self.current_ws = ws
                    backoff = 3
                    logger.info("🟢 CONNECTED to Cloud Bridge! Local PC is now ONLINE.")

                    while self.is_running:
                        try:
                            msg_text = await ws.recv()
                            task_payload = json.loads(msg_text)
                            logger.info(f"Incoming task from Cloud: {task_payload.get('task_id')}")

                            # Execute task asynchronously
                            result = await self.execute_task(task_payload)

                            # Send response back to cloud
                            await ws.send(json.dumps(result))
                            logger.info(f"✅ Result for [{result['task_id']}] sent back to Cloud.")

                        except websockets.ConnectionClosed:
                            logger.warning("WebSocket connection closed by server.")
                            break
                        except Exception as loop_err:
                            logger.error(f"Error handling task: {loop_err}")

            except Exception as conn_err:
                logger.warning(f"Connection failed: {conn_err}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(30, backoff * 2)


if __name__ == "__main__":
    url_to_use = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CLOUD_WS_URL
    daemon = PCRelayDaemon(ws_url=url_to_use)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("PC Relay Daemon stopped by user.")

"""Standalone Client Worker for Mukil's Local PC.
Connects to the 24/7 Cloud Server via WebSocket, listens for tasks from Telegram,
and executes them locally on the physical PC hardware using AutonomousAgentBrain & Antigravity.
"""
import asyncio
import json
import logging
import os
import sys
import websockets
from dotenv import load_dotenv

# Load local environment
load_dotenv()

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.agent_brain import AutonomousAgentBrain

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "pc_bridge_worker.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("PCWorkerClient")

CLOUD_SERVER_URL = os.getenv("CLOUD_SERVER_URL", "wss://aura-os-n6n3.onrender.com/api/v1/bridge/ws")
BRIDGE_SECRET = os.getenv("PC_BRIDGE_SECRET", "mukil-aura-pc-bridge-secret-2026")
WORKER_ID = os.getenv("WORKER_ID", "mukil_primary_pc")


async def run_pc_worker():
    """Persistent loop that maintains a connection to the Cloud Server."""
    brain = AutonomousAgentBrain()
    ws_uri = f"{CLOUD_SERVER_URL}?worker_id={WORKER_ID}&token={BRIDGE_SECRET}"

    logger.info("=" * 60)
    logger.info("🌌 JARVIS LOCAL PC WORKER BRIDGE STARTING...")
    logger.info(f"📍 Target Server: {CLOUD_SERVER_URL}")
    logger.info(f"💻 Worker ID: {WORKER_ID}")
    logger.info("=" * 60)

    while True:
        try:
            logger.info(f"Connecting to Cloud Server at {CLOUD_SERVER_URL}...")
            async with websockets.connect(ws_uri) as ws:
                logger.info("🟢 100% CONNECTED! Local PC Worker is listening for Cloud tasks...")
                while True:
                    raw_msg = await ws.recv()
                    task = json.loads(raw_msg)
                    task_id = task.get("task_id", "unknown")
                    command = task.get("command", "")
                    logger.info(f"⚡ Received Cloud Task [{task_id}]: '{command}'")

                    # Execute task locally on PC via AutonomousAgentBrain
                    res_text, photo_path = await brain.process_user_intent(
                        user_input=command,
                        user_name="Mukil",
                    )

                    response_payload = {
                        "task_id": task_id,
                        "status": "COMPLETED",
                        "output_text": res_text,
                        "photo_path": photo_path,
                    }
                    await ws.send(json.dumps(response_payload))
                    logger.info(f"✅ Finished Task [{task_id}] & reported back to Cloud Server.")

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"Connection to Cloud Server lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as ex:
            logger.error(f"Unexpected worker loop error: {ex}. Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_pc_worker())
    except KeyboardInterrupt:
        logger.info("PC Worker stopped by user.")

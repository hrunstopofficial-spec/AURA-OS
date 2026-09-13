"""
AURA-OS System Agent WebSocket Client
system_agent/client.py - Reconnect Loop with Exponential Backoff + Jitter,
Independent Heartbeat Task, and Local Executor Dispatcher.
"""
import os
import sys
import json
import random
import asyncio
import logging
from typing import Optional, Callable, Any
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.protocol import TaskResult, PresenceHeartbeat
from system_agent.executor import system_executor, SafeSystemExecutor

logger = logging.getLogger("system_agent_client")

MAX_BACKOFF_SECONDS = 30.0
BASE_BACKOFF_SECONDS = 1.0
BACKOFF_FACTOR = 1.5
HEARTBEAT_INTERVAL_SECONDS = 10


def calculate_reconnect_delay(
    attempt: int,
    base: float = BASE_BACKOFF_SECONDS,
    factor: float = BACKOFF_FACTOR,
    max_delay: float = MAX_BACKOFF_SECONDS
) -> float:
    """Calculates exponential backoff with additive jitter to prevent thundering herd."""
    raw_delay = base * (factor ** max(0, attempt - 1))
    jitter = random.uniform(0.1, 0.5)
    return min(max_delay, round(raw_delay + jitter, 2))


class SystemAgentClient:
    def __init__(
        self,
        server_ws_url: str = "wss://aura-os-n6n3.onrender.com/api/v1/bridge/ws",
        executor: Optional[SafeSystemExecutor] = None
    ):
        self.server_ws_url = server_ws_url
        self.executor = executor or system_executor
        self.is_connected = False
        self.reconnect_attempts = 0
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.running = False

    async def _heartbeat_loop(self, send_callback: Callable[[str], Any]):
        """Runs concurrently and independently of task execution. Sends signed frames."""
        logger.info("💓 Starting independent presence heartbeat task...")
        while self.running and self.is_connected:
            try:
                hb = self.executor.generate_signed_heartbeat(queue_depth=0)
                hb_json = hb.model_dump_json()
                await send_callback(hb_json)
                logger.debug(f"💓 Sent signed heartbeat (Agent: {hb.agent_id})")
            except Exception as hb_err:
                logger.warning(f"Heartbeat transmission error: {hb_err}")
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    async def handle_incoming_message(self, raw_message: str, send_callback: Callable[[str], Any]):
        """Processes an incoming TaskRequest and dispatches output back to server."""
        # Runs executor synchronously or in threadpool to prevent blocking the event loop
        result: TaskResult = await asyncio.to_thread(
            self.executor.process_raw_request, raw_message
        )
        # Send verified TaskResult back to server
        await send_callback(result.model_dump_json())
        logger.info(f"📤 Dispatched verified TaskResult for {result.task_id} (Status: {result.status.value})")

    def stop(self):
        self.running = False
        self.is_connected = False
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()

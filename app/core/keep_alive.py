"""
24/7 Always-Awake Keep-Alive Engine for Render.com & Cloud Containers.
Prevents Render free tier from sleeping by self-pinging the /health endpoint every 2 minutes (120 seconds).
"""
import os
import asyncio
import logging
import httpx

logger = logging.getLogger("KeepAliveEngine")

class RenderKeepAlive:
    def __init__(self, interval_seconds: int = 120):
        self.interval = interval_seconds
        self.is_running = False
        self.task = None

    async def _ping_loop(self):
        logger.info(f"⚡ Render Keep-Alive Engine started (Pinging every {self.interval}s to prevent cloud sleep)...")
        # Give server 10s to fully bind on startup
        await asyncio.sleep(10)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while self.is_running:
                try:
                    # Self ping localhost:$PORT/health or public Render URL if configured
                    port = os.environ.get("PORT", "8000")
                    render_url = os.environ.get("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{port}")
                    target = f"{render_url.rstrip('/')}/health"
                    
                    resp = await client.get(target)
                    if resp.status_code == 200:
                        logger.info(f"💓 Render Keep-Alive Ping SUCCESS: {target} (HTTP 200) - Container Awake 24/7")
                    else:
                        logger.warning(f"Render Keep-Alive Ping returned status {resp.status_code}")
                except Exception as e:
                    logger.debug(f"Keep-Alive ping notice: {e}")
                
                await asyncio.sleep(self.interval)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._ping_loop())

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()

keep_alive_engine = RenderKeepAlive(interval_seconds=120)

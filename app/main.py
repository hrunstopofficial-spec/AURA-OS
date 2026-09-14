import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse

from app.api.v1.router import api_v1_router
from app.api.v1.routes.health import health_check
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.database.session import init_db

# Initialize structured logging
setup_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager: handles startup and shutdown tasks."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENVIRONMENT}] mode...")
    # Initialize database tables and schema
    await init_db()
    
    # Start 24/7 Render Keep-Alive Pinger (Prevents Cloud Sleep every 2 mins)
    from app.core.keep_alive import keep_alive_engine
    keep_alive_engine.start()

    # Start 24/7 Telegram Bridge Daemon when deployed to Cloud / Production
    telegram_process = None
    from config import TELEGRAM_BOT_TOKEN
    token = os.getenv("TELEGRAM_BOT_TOKEN") or TELEGRAM_BOT_TOKEN
    is_cloud = bool(os.getenv("RENDER") or settings.ENVIRONMENT == "production" or os.getenv("RUN_TELEGRAM_BOT") == "true")
    if is_cloud and token:
        bridge_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "telegram_bridge.py")
        if os.path.exists(bridge_script):
            logger.info("🚀 Starting 24/7 Telegram Bridge Daemon on Cloud Container...")
            try:
                import subprocess
                import sys
                sub_env = os.environ.copy()
                sub_env["TELEGRAM_BOT_TOKEN"] = token
                telegram_process = subprocess.Popen([sys.executable, "-u", bridge_script], env=sub_env)
                logger.info(f"✅ Telegram Bridge Daemon running with PID: {telegram_process.pid}")
            except Exception as e:
                logger.error(f"Failed to launch Telegram Bridge Daemon: {e}")
    
    yield

    if telegram_process and telegram_process.poll() is None:
        logger.info("Terminating Telegram Bridge background process...")
        try:
            telegram_process.terminate()
            telegram_process.wait(timeout=5)
        except Exception:
            telegram_process.kill()

    keep_alive_engine.stop()
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="Cloud-First Persistent Agentic Operating System API",
        version=settings.API_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root Level Endpoints
    app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

    @app.get("/", tags=["Root"])
    async def root_hub(request: Request):
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            hub_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_mobile_hub.html")
            if os.path.exists(hub_path):
                with open(hub_path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            return HTMLResponse("<h1>AURA-OS Mobile Hub is online.</h1>")
        return JSONResponse(
            content={
                "name": settings.APP_NAME,
                "version": settings.API_VERSION,
                "status": "online",
                "docs": "/docs",
                "hub": "/app",
            }
        )

    @app.get("/app", tags=["Root"], response_class=HTMLResponse)
    async def app_hub():
        hub_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_mobile_hub.html")
        if os.path.exists(hub_path):
            with open(hub_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("<h1>AURA-OS Mobile Hub is online.</h1>")

    @app.get("/login", tags=["Demo"], response_class=HTMLResponse)
    async def login_page():
        login_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "login_demo.html")
        if os.path.exists(login_path):
            with open(login_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("<h1>Login demo not found.</h1>")

    @app.get("/manifest.json", tags=["PWA"])
    async def get_manifest():
        m_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "manifest.json")
        return FileResponse(m_path, media_type="application/json")

    @app.get("/sw.js", tags=["PWA"])
    async def get_service_worker():
        sw_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sw.js")
        return FileResponse(sw_path, media_type="application/javascript")

    # Mount API v1 Routes
    app.include_router(api_v1_router)

    # Global Exception Handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred.",
                "path": request.url.path,
            },
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

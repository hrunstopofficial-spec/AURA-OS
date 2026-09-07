"""Health probe and readiness endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.database.session import check_db_health

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Structured health response."""
    status: str = Field(..., description="Overall system health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="API Version")
    environment: str = Field(..., description="Running environment")
    database: str = Field(..., description="Database connection status: connected | disconnected")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health of API server and database connectivity."""
    settings = get_settings()
    db_healthy = await check_db_health()
    return HealthResponse(
        status="healthy" if db_healthy else "degraded",
        app_name=settings.APP_NAME,
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        database="connected" if db_healthy else "disconnected",
    )


@router.get("/system-diagnosis")
async def system_diagnosis():
    """Live AURA-OS Hardware Vitals & Health Diagnosis."""
    from tools.registry import registry
    from tools import system_tools
    from storage.memory.system_metrics import metrics_store
    from agents.analysis_engine import analysis_engine

    vitals_res = registry.execute_tool("get_system_vitals")
    if not vitals_res["success"]:
        return {"error": vitals_res["error"]}

    vitals = vitals_res["result"]
    metrics_store.record_snapshot(vitals)
    delta = metrics_store.compute_telemetry_delta(vitals, hours=24.0)
    diagnosis = analysis_engine.analyze(vitals, delta)
    return diagnosis


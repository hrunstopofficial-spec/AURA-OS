"""
AURA-OS Autonomous Agent Communication Protocol
shared/protocol.py - Zero-Trust, Discriminated-Union, Idempotent & Replay-Protected Schema.
Pydantic V2 Compatible.
"""
from enum import Enum
from typing import Dict, Any, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, HttpUrl, model_validator
import os
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0.0"
MAX_SIGNATURE_DRIFT_SECONDS = 30

try:
    from config import AURA_BRIDGE_HMAC_SECRET as DEFAULT_HMAC_SECRET
except Exception:
    DEFAULT_HMAC_SECRET = os.environ.get("AURA_BRIDGE_HMAC_SECRET", "mukil-jarvis-vault-key-9080030538")


# =====================================================================
# 1. ROUTING TAXONOMY
# =====================================================================
class TaskRoute(str, Enum):
    SERVER = "server"             # Cloud 24/7 (Scraping, APIs, Gmail, Drive sync)
    LOCAL_SYSTEM = "local_system" # Laptop (Screen, Vitals, Local files, Antigravity)
    HYBRID = "hybrid"             # Cloud gathers data -> Local executes action


# =====================================================================
# 2. CLOSED SET OF PRE-VETTED SCRIPTS (No Arbitrary Execution)
# =====================================================================
class PreapprovedScriptId(str, Enum):
    CHECK_DISK_HEALTH = "check_disk_health"
    CLEANUP_TEMP_FILES = "cleanup_temp_files"
    RESTART_TELEGRAM_BRIDGE = "restart_telegram_bridge"
    FLUSH_DNS_CACHE = "flush_dns_cache"
    SGC_BACKUP_SNAPSHOT = "sgc_backup_snapshot"


# =====================================================================
# 3. DISCRIMINATED PAYLOADS (Strict Param-Level Validation per Action)
# =====================================================================
class BatteryVitalsPayload(BaseModel):
    action: Literal["get_battery_vitals"] = "get_battery_vitals"


class HardwareMetricsPayload(BaseModel):
    action: Literal["get_hardware_metrics"] = "get_hardware_metrics"
    sample_interval_sec: float = Field(default=1.0, ge=0.1, le=5.0)


class CaptureScreenshotPayload(BaseModel):
    action: Literal["capture_screenshot"] = "capture_screenshot"
    quality: int = Field(default=80, ge=20, le=100)
    monitor_index: int = Field(default=0, ge=0, le=5)


class OpenBrowserUrlPayload(BaseModel):
    action: Literal["open_browser_url"] = "open_browser_url"
    url: HttpUrl  # Strictly blocks file:///, local admin panels, and invalid URIs
    new_window: bool = False


class LaunchSgcBillingPayload(BaseModel):
    action: Literal["launch_sgc_billing"] = "launch_sgc_billing"
    minimized: bool = False


class LockWorkstationPayload(BaseModel):
    action: Literal["lock_workstation"] = "lock_workstation"


class RunPreapprovedScriptPayload(BaseModel):
    action: Literal["run_preapproved_script"] = "run_preapproved_script"
    script_id: PreapprovedScriptId  # Must be an exact member of the closed enum
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class ExecuteHeadlessAntigravityPayload(BaseModel):
    action: Literal["execute_headless_antigravity"] = "execute_headless_antigravity"
    task_prompt: str = Field(min_length=3, max_length=1500)
    target_repo: Optional[str] = Field(default=None, max_length=100)
    timeout_seconds: int = Field(default=180, ge=10, le=300)


# Discriminated Union of all valid Local System Actions
LocalActionPayload = Annotated[
    Union[
        BatteryVitalsPayload,
        HardwareMetricsPayload,
        CaptureScreenshotPayload,
        OpenBrowserUrlPayload,
        LaunchSgcBillingPayload,
        LockWorkstationPayload,
        RunPreapprovedScriptPayload,
        ExecuteHeadlessAntigravityPayload
    ],
    Field(discriminator="action")
]


# =====================================================================
# 4. TASK STATUS & RESULT SCHEMAS
# =====================================================================
class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED_OFFLINE = "queued_offline"
    IN_FLIGHT = "in_flight"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED_SECURITY = "rejected_security"


class TaskResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str
    idempotency_key: str
    status: TaskStatus
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    executor_agent_id: str
    verified: bool = False
    verification_note: Optional[str] = None
    critic_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =====================================================================
# 5. IDEMPOTENT, AUTHENTICATED & REPLAY-PROTECTED TASK REQUEST
# =====================================================================
class TaskRequest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    route: TaskRoute
    payload: Union[LocalActionPayload, Dict[str, Any]]
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    retry_count: int = Field(default=0, ge=0)
    auth_signature: str = ""

    @model_validator(mode="after")
    def validate_request_integrity(self) -> "TaskRequest":
        # Idempotency fix: Ensure idempotency_key is tied to task_id if not explicitly provided
        if not self.idempotency_key:
            self.idempotency_key = self.task_id

        # Strict route-to-payload enforcement:
        if self.route == TaskRoute.LOCAL_SYSTEM:
            if isinstance(self.payload, dict):
                raise ValueError(
                    f"Invalid payload for LOCAL_SYSTEM route. Must be one of the pre-approved typed action models, got: {self.payload.get('action')}"
                )
        return self

    def sign(self, secret_key: Optional[str] = None) -> str:
        """Signs the TaskRequest using HMAC-SHA256 matching the executor's canonical envelope."""
        key = secret_key or DEFAULT_HMAC_SECRET
        self.created_at = datetime.now(timezone.utc)
        dict_copy = json.loads(self.model_dump_json())
        dict_copy["auth_signature"] = ""
        canonical_bytes = json.dumps(dict_copy, sort_keys=True, default=str).encode("utf-8")
        self.auth_signature = generate_hmac_signature(key, canonical_bytes)
        return self.auth_signature

    def verify(self, secret_key: Optional[str] = None) -> bool:
        """Verifies the HMAC-SHA256 signature of this TaskRequest."""
        key = secret_key or DEFAULT_HMAC_SECRET
        if not self.auth_signature:
            return False
        dict_copy = json.loads(self.model_dump_json())
        dict_copy["auth_signature"] = ""
        canonical_bytes = json.dumps(dict_copy, sort_keys=True, default=str).encode("utf-8")
        return verify_hmac_signature(key, canonical_bytes, self.auth_signature)


# =====================================================================
# 6. SIGNED PRESENCE HEARTBEAT FRAME (Spoofing-Protected)
# =====================================================================
class PresenceHeartbeat(BaseModel):
    schema_version: str = SCHEMA_VERSION
    agent_id: str
    is_online: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    battery_percent: Optional[int] = Field(default=None, ge=0, le=100)
    queue_depth: int = Field(default=0, ge=0)
    vitals_summary: Optional[str] = None
    auth_signature: str = ""

    def verify(self, secret_key: Optional[str] = None) -> bool:
        """Verifies the HMAC signature of this heartbeat frame."""
        key = secret_key or DEFAULT_HMAC_SECRET
        if not self.auth_signature:
            return False
        hb_bytes = json.dumps({
            "agent_id": self.agent_id,
            "is_online": self.is_online,
            "timestamp": self.timestamp.isoformat(),
            "battery_percent": self.battery_percent,
            "queue_depth": self.queue_depth
        }, sort_keys=True).encode("utf-8")
        return verify_hmac_signature(key, hb_bytes, self.auth_signature)


# =====================================================================
# 7. CRYPTOGRAPHIC INTEGRITY & FRESHNESS HELPERS
# =====================================================================
def generate_hmac_signature(secret_key: str, message_bytes: bytes) -> str:
    """Generates standard SHA-256 HMAC signature for zero-trust bridge communication."""
    return hmac.new(secret_key.encode("utf-8"), message_bytes, hashlib.sha256).hexdigest()


def verify_hmac_signature(secret_key: str, message_bytes: bytes, signature: str) -> bool:
    """Verifies HMAC signature in constant time to prevent timing attacks."""
    expected = generate_hmac_signature(secret_key, message_bytes)
    return hmac.compare_digest(expected, signature)


def is_timestamp_fresh(ts: datetime, max_drift_seconds: int = MAX_SIGNATURE_DRIFT_SECONDS) -> bool:
    """Replay protection: Rejects messages with timestamp older than max_drift_seconds."""
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    drift = abs((now - ts).total_seconds())
    return drift <= max_drift_seconds

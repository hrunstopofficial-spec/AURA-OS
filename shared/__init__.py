"""
AURA-OS Shared Core Architecture Package
"""
from shared.protocol import (
    TaskRoute,
    LocalActionPayload,
    BatteryVitalsPayload,
    HardwareMetricsPayload,
    CaptureScreenshotPayload,
    OpenBrowserUrlPayload,
    LaunchSgcBillingPayload,
    LockWorkstationPayload,
    RunPreapprovedScriptPayload,
    ExecuteHeadlessAntigravityPayload,
    PreapprovedScriptId,
    TaskStatus,
    TaskRequest,
    TaskResult,
    PresenceHeartbeat,
    generate_hmac_signature,
    verify_hmac_signature,
    is_timestamp_fresh,
    SCHEMA_VERSION
)

__all__ = [
    "TaskRoute",
    "LocalActionPayload",
    "BatteryVitalsPayload",
    "HardwareMetricsPayload",
    "CaptureScreenshotPayload",
    "OpenBrowserUrlPayload",
    "LaunchSgcBillingPayload",
    "LockWorkstationPayload",
    "RunPreapprovedScriptPayload",
    "ExecuteHeadlessAntigravityPayload",
    "PreapprovedScriptId",
    "TaskStatus",
    "TaskRequest",
    "TaskResult",
    "PresenceHeartbeat",
    "generate_hmac_signature",
    "verify_hmac_signature",
    "is_timestamp_fresh",
    "SCHEMA_VERSION"
]

from shared.registry import registry, ToolRegistry, ToolMetadata
from shared.verifier import verifier, TaskVerifier, CriticEvaluation
__all__.extend(["registry", "ToolRegistry", "ToolMetadata", "verifier", "TaskVerifier", "CriticEvaluation"])


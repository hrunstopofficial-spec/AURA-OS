"""
AURA-OS Step 4 Verification Test Suite
tests/test_offline_queue_hybrid.py - Validates Offline Task Queue,
Presence Verification, Idempotency, and Hybrid Dispatch / Queue Draining.
"""
import os
import sys
import time
import json
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.protocol import (
    TaskRequest,
    TaskRoute,
    TaskStatus,
    PresenceHeartbeat,
    BatteryVitalsPayload,
    CaptureScreenshotPayload
)
from shared.task_queue import task_queue, TaskQueueManager
from server_agent.presence_manager import presence_manager
from server_agent.hybrid_dispatcher import hybrid_dispatcher
from server_agent.router import server_router
from system_agent.executor import system_executor

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "memory", "test_task_queue.sqlite")
TEST_PRESENCE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "memory", "test_system_presence.json")


def setup_module():
    """Clear test databases and test presence files."""
    presence_manager.presence_file = TEST_PRESENCE_FILE
    if os.path.exists(TEST_PRESENCE_FILE):
        os.remove(TEST_PRESENCE_FILE)
    with task_queue._get_connection() as conn:
        conn.execute("DELETE FROM task_queue")
        conn.commit()


def test_1_offline_enqueueing():
    """When System Agent is offline, LOCAL_SYSTEM tasks must be enqueued into SQLite."""
    presence_manager.presence_file = TEST_PRESENCE_FILE
    if os.path.exists(TEST_PRESENCE_FILE):
        os.remove(TEST_PRESENCE_FILE)
    
    assert not presence_manager.is_system_agent_online()

    # Dispatch local task through router
    resp = server_router.handle_message("Check my PC battery and vitals", user_name="Mukil")

    assert resp.is_task is True
    assert resp.tool_name in ["get_battery_vitals", "get_system_vitals", "get_hardware_metrics"]
    assert resp.task_result is not None
    assert resp.task_result.status == TaskStatus.QUEUED_OFFLINE
    assert "Task Queued" in resp.reply
    assert resp.task_id[:8] in resp.reply

    # Verify task exists in SQLite database
    queued_task = task_queue.get_task(resp.task_id)
    assert queued_task is not None
    assert queued_task["status"] == "queued_offline"
    print(f"\n[Test 1 Passed] Task {resp.task_id[:8]} ({resp.tool_name}) properly queued in SQLite while PC offline.")


def test_2_idempotency_protection():
    """Duplicate task with identical idempotency key must not produce duplicate queue entries."""
    task_req = TaskRequest(
        task_id="idemp-test-001",
        idempotency_key="idemp-key-unique-999",
        route=TaskRoute.LOCAL_SYSTEM,
        payload=BatteryVitalsPayload(action="get_battery_vitals")
    )
    task_req.sign()

    # Enqueue first time
    id1 = task_queue.enqueue_task(task_req, tool_name="get_battery_vitals")
    # Enqueue second time with identical key
    id2 = task_queue.enqueue_task(task_req, tool_name="get_battery_vitals")

    assert id1 == id2
    record = task_queue.get_task_by_idempotency_key("idemp-key-unique-999")
    assert record is not None
    assert record["task_id"] == "idemp-test-001"
    print("\n[Test 2 Passed] Idempotency duplicate successfully suppressed.")


def test_3_heartbeat_presence_verification():
    """System Agent signed heartbeat must be verified and bring presence to ONLINE."""
    presence_manager.presence_file = TEST_PRESENCE_FILE

    # Generate legitimate signed heartbeat from executor
    hb = system_executor.generate_signed_heartbeat(queue_depth=0)
    assert hb.verify() is True

    # Record heartbeat
    recorded = presence_manager.record_heartbeat(hb)
    assert recorded is True
    assert presence_manager.is_system_agent_online(freshness_window_sec=10.0) is True

    info = presence_manager.get_presence_info()
    assert info["is_online"] is True
    assert info["agent_id"] == system_executor.agent_id
    print("\n[Test 3 Passed] Signed PresenceHeartbeat validated and System Agent marked ONLINE.")


def test_4_online_immediate_dispatch():
    """When System Agent is online, LOCAL_SYSTEM tasks must execute immediately with hardware telemetry."""
    presence_manager.presence_file = TEST_PRESENCE_FILE
    hb = system_executor.generate_signed_heartbeat(queue_depth=0)
    presence_manager.record_heartbeat(hb)
    assert presence_manager.is_system_agent_online() is True

    # Dispatch battery/vitals task
    resp = server_router.handle_message("Check my PC battery and vitals", user_name="Mukil")

    assert resp.is_task is True
    assert resp.tool_name in ["get_battery_vitals", "get_system_vitals", "get_hardware_metrics"]
    assert resp.task_result is not None
    assert resp.task_result.status == TaskStatus.SUCCESS
    assert resp.task_result.verified is True
    print(f"\n[Test 4 Passed] Task {resp.tool_name} executed immediately online: Result={resp.task_result.result_data}")


def test_5_queue_draining():
    """When System Agent comes online, queued offline tasks must drain and execute in FIFO order."""
    presence_manager.presence_file = TEST_PRESENCE_FILE
    # 1. Take System Agent offline and enqueue a screenshot task
    if os.path.exists(TEST_PRESENCE_FILE):
        os.remove(TEST_PRESENCE_FILE)
    assert not presence_manager.is_system_agent_online()

    with task_queue._get_connection() as conn:
        conn.execute("DELETE FROM task_queue")
        conn.commit()

    offline_req = TaskRequest(
        task_id="drain-screenshot-001",
        idempotency_key="drain-key-screenshot-001",
        route=TaskRoute.LOCAL_SYSTEM,
        payload=CaptureScreenshotPayload(action="capture_screenshot", quality=80)
    )
    offline_req.sign()
    task_queue.enqueue_task(offline_req, tool_name="capture_screenshot")

    assert task_queue.count_queued_tasks(TaskRoute.LOCAL_SYSTEM) >= 1

    # 2. System Agent comes online (sends heartbeat)
    hb = system_executor.generate_signed_heartbeat(queue_depth=1)
    presence_manager.record_heartbeat(hb)
    assert presence_manager.is_system_agent_online() is True

    # 3. Trigger queue draining
    drained = hybrid_dispatcher.drain_offline_queue()
    assert len(drained) >= 1

    # Check that the drained task completed successfully
    drained_screenshot = [t for t in drained if t.task_id == "drain-screenshot-001"][0]
    assert drained_screenshot.status == TaskStatus.SUCCESS
    assert drained_screenshot.verified is True
    assert "screenshot_path" in drained_screenshot.result_data or "file_path" in drained_screenshot.result_data
    sc_path = drained_screenshot.result_data.get("screenshot_path") or drained_screenshot.result_data.get("file_path")

    # Verify task in SQLite is now SUCCESS
    updated_record = task_queue.get_task("drain-screenshot-001")
    assert updated_record["status"] == "success"
    print(f"\n[Test 5 Passed] Successfully drained offline queue. Screenshot saved: {sc_path}")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

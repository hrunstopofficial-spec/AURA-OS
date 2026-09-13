"""
AURA-OS Hybrid Task Dispatcher & Offline Queue Worker
server_agent/hybrid_dispatcher.py - Routes tasks across Cloud Server and Local PC,
manages offline queueing when PC is disconnected, and drains queue upon reconnection.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from shared.protocol import TaskRequest, TaskResult, TaskRoute, TaskStatus
from shared.task_queue import task_queue, TaskQueueManager
from shared.verifier import verifier
from server_agent.presence_manager import presence_manager, PresenceManager
from system_agent.executor import system_executor

logger = logging.getLogger("hybrid_dispatcher")


class HybridTaskDispatcher:
    def __init__(
        self,
        queue: Optional[TaskQueueManager] = None,
        presence: Optional[PresenceManager] = None
    ):
        self.queue = queue or task_queue
        self.presence = presence or presence_manager

    def dispatch_local_system_task(
        self,
        task_req: TaskRequest,
        tool_name: str,
        user_request_text: str = ""
    ) -> TaskResult:
        """
        Dispatches a LOCAL_SYSTEM task:
        - If System Agent is ONLINE: Executes immediately on PC node.
        - If System Agent is OFFLINE: Enqueues into SQLite queue for delayed execution.
        """
        is_online = self.presence.is_system_agent_online()

        if not is_online:
            logger.warning(f"📴 PC Node is OFFLINE. Enqueueing task [{task_req.task_id}] ({tool_name}) for delayed execution.")
            self.queue.enqueue_task(task_req, tool_name=tool_name, status=TaskStatus.QUEUED_OFFLINE)

            return TaskResult(
                task_id=task_req.task_id,
                idempotency_key=task_req.idempotency_key,
                status=TaskStatus.QUEUED_OFFLINE,
                result_data={
                    "queued": True,
                    "tool_name": tool_name,
                    "task_id": task_req.task_id,
                    "queue_count": self.queue.count_queued_tasks(TaskRoute.LOCAL_SYSTEM),
                    "note": "Laptop offline; task queued in persistent SQLite store."
                },
                executor_agent_id="offline_queue",
                verified=True,
                verification_note="Task queued successfully while PC is offline."
            )

        # PC Node is ONLINE -> Execute immediately via System Executor
        logger.info(f"🟢 PC Node is ONLINE. Dispatching task [{task_req.task_id}] ({tool_name}) to System Agent...")
        try:
            # Sign the request if not already signed
            if not task_req.auth_signature or task_req.auth_signature == "internal_server_authorized":
                task_req.sign()

            raw_result: TaskResult = system_executor.process_task_request(task_req)

            # Two-layer verification pass
            payload_dict = task_req.payload if isinstance(task_req.payload, dict) else task_req.payload.model_dump()
            verified_result = verifier.verify_task_result(
                task_id=task_req.task_id,
                original_user_request=user_request_text or f"Execute {tool_name}",
                tool_name=tool_name,
                tool_params=payload_dict,
                raw_result_data=raw_result.result_data,
                executor_agent_id=raw_result.executor_agent_id,
                execution_time_ms=raw_result.execution_time_ms
            )

            # If task was previously queued, record completion
            self.queue.complete_task(task_req.task_id, verified_result)
            return verified_result

        except Exception as exec_err:
            logger.error(f"Error during live dispatch to System Agent: {exec_err}")
            return TaskResult(
                task_id=task_req.task_id,
                idempotency_key=task_req.idempotency_key,
                status=TaskStatus.FAILED,
                error_message=str(exec_err),
                executor_agent_id="system_agent",
                verified=False
            )

    def drain_offline_queue(self) -> List[TaskResult]:
        """
        Drains pending QUEUED_OFFLINE tasks when System Agent comes online.
        Executes each task in FIFO order and returns verified results.
        """
        if not self.presence.is_system_agent_online():
            logger.info("Cannot drain offline queue: System Agent is still offline.")
            return []

        pending_tasks = self.queue.get_pending_tasks(route=TaskRoute.LOCAL_SYSTEM, limit=10)
        if not pending_tasks:
            return []

        logger.info(f"⚡ Draining {len(pending_tasks)} offline tasks for System Agent...")
        drained_results: List[TaskResult] = []

        for task_row in pending_tasks:
            task_id = task_row["task_id"]
            tool_name = task_row["tool_name"]
            payload_dict = json.loads(task_row["payload_json"])

            self.queue.mark_in_flight(task_id)

            # Reconstruct TaskRequest
            task_req = TaskRequest(
                task_id=task_id,
                idempotency_key=task_row["idempotency_key"],
                route=TaskRoute.LOCAL_SYSTEM,
                payload=payload_dict,
                retry_count=task_row.get("retry_count", 0)
            )
            task_req.sign()

            result = self.dispatch_local_system_task(
                task_req=task_req,
                tool_name=tool_name,
                user_request_text=f"Drained offline task {tool_name}"
            )
            drained_results.append(result)

        logger.info(f"✅ Successfully drained {len(drained_results)} offline tasks.")
        return drained_results


# Shared global instance
hybrid_dispatcher = HybridTaskDispatcher()

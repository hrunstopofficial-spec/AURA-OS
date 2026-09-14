"""
AURA-OS Persistent Offline Task Queue
shared/task_queue.py - SQLite-backed persistent queue for asynchronous,
offline, and hybrid task dispatch with idempotency protection.
"""
import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from shared.protocol import TaskRequest, TaskResult, TaskRoute, TaskStatus

logger = logging.getLogger("aura_task_queue")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "storage", "memory", "task_queue.sqlite")


class TaskQueueManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and indexes for resilient persistent queueing."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    task_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    route TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    result_json TEXT,
                    retry_count INTEGER DEFAULT 0,
                    completed_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status_route ON task_queue(status, route)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency ON task_queue(idempotency_key)")
            conn.commit()

    def enqueue_task(
        self,
        task_req: TaskRequest,
        tool_name: str,
        status: TaskStatus = TaskStatus.QUEUED_OFFLINE
    ) -> str:
        """
        Enqueues an idempotent TaskRequest into the SQLite queue.
        If idempotency_key already exists, returns existing task_id.
        """
        if isinstance(task_req.payload, dict):
            payload_dict = task_req.payload
        elif hasattr(task_req.payload, "model_dump"):
            payload_dict = task_req.payload.model_dump(mode="json")
        else:
            payload_dict = dict(task_req.payload)
        payload_str = json.dumps(payload_dict, default=str)
        created_at_str = task_req.created_at.isoformat()

        with self._get_connection() as conn:
            # Check for existing idempotency key
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, status FROM task_queue WHERE idempotency_key = ?", (task_req.idempotency_key,))
            existing = cursor.fetchone()
            if existing:
                logger.info(f"🔁 Task with idempotency_key '{task_req.idempotency_key}' already queued as {existing['task_id']}")
                return existing["task_id"]

            cursor.execute("""
                INSERT INTO task_queue (
                    task_id, idempotency_key, created_at, route, tool_name,
                    payload_json, status, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_req.task_id,
                task_req.idempotency_key,
                created_at_str,
                task_req.route.value,
                tool_name,
                payload_str,
                status.value,
                task_req.retry_count
            ))
            conn.commit()

        logger.info(f"📥 Enqueued task [{task_req.task_id}] (Tool: '{tool_name}', Route: '{task_req.route.value}', Status: '{status.value}')")
        return task_req.task_id

    def get_pending_tasks(
        self,
        route: Optional[TaskRoute] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Returns pending or queued_offline tasks ordered by creation time (FIFO)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if route:
                cursor.execute("""
                    SELECT * FROM task_queue
                    WHERE status IN ('pending', 'queued_offline') AND route = ?
                    ORDER BY created_at ASC LIMIT ?
                """, (route.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM task_queue
                    WHERE status IN ('pending', 'queued_offline')
                    ORDER BY created_at ASC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def mark_in_flight(self, task_id: str) -> bool:
        """Marks a task as actively in-flight."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE task_queue SET status = ? WHERE task_id = ?", (TaskStatus.IN_FLIGHT.value, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def complete_task(self, task_id: str, result: TaskResult) -> bool:
        """Stores final execution result and marks task as SUCCESS or FAILED."""
        completed_at_str = result.completed_at.isoformat()
        result_str = json.dumps(result.result_data, default=str)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue SET
                    status = ?,
                    error_message = ?,
                    result_json = ?,
                    completed_at = ?
                WHERE task_id = ?
            """, (
                result.status.value,
                result.error_message,
                result_str,
                completed_at_str,
                task_id
            ))
            conn.commit()
            logger.info(f"✅ Completed task [{task_id}] -> Status: {result.status.value}")
            return cursor.rowcount > 0

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single task record by task_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_task_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a task record by its unique idempotency_key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM task_queue WHERE idempotency_key = ?", (idempotency_key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def count_queued_tasks(self, route: Optional[TaskRoute] = None) -> int:
        """Returns the number of tasks waiting in queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if route:
                cursor.execute("SELECT COUNT(*) FROM task_queue WHERE status IN ('pending', 'queued_offline') AND route = ?", (route.value,))
            else:
                cursor.execute("SELECT COUNT(*) FROM task_queue WHERE status IN ('pending', 'queued_offline')")
            return cursor.fetchone()[0]


# Shared global instance
task_queue = TaskQueueManager()

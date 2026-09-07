import os
import sys
import sqlite3
import json
import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "system_metrics.db")


class SystemMetricsStore:
    """Persistent SQLite Timeseries engine for AURA hardware vitals."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vitals_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_pct REAL NOT NULL,
                    memory_pct REAL NOT NULL,
                    memory_avail_mb REAL NOT NULL,
                    disk_pct REAL NOT NULL,
                    battery_pct REAL,
                    is_charging INTEGER,
                    net_latency_ms REAL,
                    top_proc_json TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vitals_timestamp 
                ON vitals_history(timestamp)
            """)
            conn.commit()

    def record_snapshot(self, vitals: Dict[str, Any]) -> int:
        """Insert a telemetry snapshot into the SQLite timeseries store."""
        timestamp = vitals.get("timestamp") or datetime.datetime.now().isoformat()
        cpu_pct = vitals.get("cpu", {}).get("cpu_percent", 0.0)
        memory_pct = vitals.get("memory", {}).get("percent", 0.0)
        memory_avail_mb = vitals.get("memory", {}).get("available_mb", 0.0)
        disk_pct = vitals.get("disk", {}).get("percent", 0.0)
        battery_pct = vitals.get("battery", {}).get("battery_percent")
        is_charging = 1 if vitals.get("battery", {}).get("is_charging") else 0
        net_latency_ms = vitals.get("network", {}).get("latency_ms", -1.0)
        top_proc_json = json.dumps(vitals.get("top_processes", []))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vitals_history (
                    timestamp, cpu_pct, memory_pct, memory_avail_mb,
                    disk_pct, battery_pct, is_charging, net_latency_ms, top_proc_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, cpu_pct, memory_pct, memory_avail_mb,
                disk_pct, battery_pct, is_charging, net_latency_ms, top_proc_json
            ))
            conn.commit()
            return cursor.lastrowid

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the latest N telemetry recordings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM vitals_history 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_historical_average(self, hours: float = 24.0) -> Dict[str, Any]:
        """Compute aggregate average of metrics across the specified past hours."""
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as sample_count,
                    AVG(cpu_pct) as avg_cpu,
                    AVG(memory_pct) as avg_memory,
                    AVG(disk_pct) as avg_disk,
                    AVG(net_latency_ms) as avg_latency
                FROM vitals_history
                WHERE timestamp >= ?
            """, (cutoff,))
            row = cursor.fetchone()
            if row and row["sample_count"] > 0:
                return {
                    "sample_count": row["sample_count"],
                    "avg_cpu": round(row["avg_cpu"] or 0.0, 1),
                    "avg_memory": round(row["avg_memory"] or 0.0, 1),
                    "avg_disk": round(row["avg_disk"] or 0.0, 1),
                    "avg_latency": round(row["avg_latency"] or 0.0, 1)
                }
            return {
                "sample_count": 0,
                "avg_cpu": None,
                "avg_memory": None,
                "avg_disk": None,
                "avg_latency": None
            }

    def compute_telemetry_delta(self, current_vitals: Dict[str, Any], hours: float = 24.0) -> Dict[str, Any]:
        """Compare current live vitals against historical window average."""
        hist = self.get_historical_average(hours=hours)
        curr_cpu = current_vitals.get("cpu", {}).get("cpu_percent", 0.0)
        curr_mem = current_vitals.get("memory", {}).get("percent", 0.0)
        curr_disk = current_vitals.get("disk", {}).get("percent", 0.0)

        if hist["sample_count"] == 0 or hist["avg_cpu"] is None:
            return {
                "has_history": False,
                "message": "First measurement logged. Baseline telemetry established.",
                "sample_count": 0
            }

        cpu_delta = round(curr_cpu - hist["avg_cpu"], 1)
        mem_delta = round(curr_mem - hist["avg_memory"], 1)
        disk_delta = round(curr_disk - hist["avg_disk"], 1)

        # Better/Worse determination: Negative delta on CPU/Mem is improvement
        if cpu_delta <= -5.0 or mem_delta <= -5.0:
            trend = "BETTER / COOLER"
        elif cpu_delta >= 10.0 or mem_delta >= 10.0:
            trend = "UNDER PRESSURE"
        else:
            trend = "STABLE / NORMAL"

        return {
            "has_history": True,
            "sample_count": hist["sample_count"],
            "window_hours": hours,
            "trend": trend,
            "cpu_delta": cpu_delta,
            "memory_delta": mem_delta,
            "disk_delta": disk_delta,
            "avg_cpu": hist["avg_cpu"],
            "avg_memory": hist["avg_memory"]
        }


# Global singleton instance
metrics_store = SystemMetricsStore()

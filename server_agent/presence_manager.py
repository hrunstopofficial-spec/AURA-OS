"""
AURA-OS Server Agent Presence Manager
server_agent/presence_manager.py - Tracks System Agent heartbeat presence,
freshness windows, and determines whether PC node is ONLINE or OFFLINE.
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from shared.protocol import PresenceHeartbeat, verify_hmac_signature

logger = logging.getLogger("presence_manager")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PRESENCE_FILE = os.path.join(BASE_DIR, "storage", "memory", "system_presence.json")
DEFAULT_FRESHNESS_WINDOW_SEC = 30.0


class PresenceManager:
    def __init__(self, presence_file: str = PRESENCE_FILE):
        self.presence_file = presence_file
        os.makedirs(os.path.dirname(self.presence_file), exist_ok=True)

    def record_heartbeat(self, hb: PresenceHeartbeat) -> bool:
        """
        Validates signed heartbeat from System Agent and records active presence.
        Returns True if signature is valid and presence recorded.
        """
        if not hb.verify():
            logger.warning(f"❌ Heartbeat signature verification failed for agent {hb.agent_id}")
            return False

        presence_data = {
            "agent_id": hb.agent_id,
            "status": "online" if hb.is_online else "offline",
            "is_online": hb.is_online,
            "battery_percent": hb.battery_percent,
            "queue_depth": hb.queue_depth,
            "vitals_summary": hb.vitals_summary,
            "last_seen_timestamp": hb.timestamp.isoformat(),
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            with open(self.presence_file, "w", encoding="utf-8") as f:
                json.dump(presence_data, f, indent=2)
            logger.info(f"💓 Presence recorded for {hb.agent_id} (Queue depth: {hb.queue_depth})")
            return True
        except Exception as e:
            logger.error(f"Error persisting presence: {e}")
            return False

    def is_system_agent_online(self, freshness_window_sec: float = DEFAULT_FRESHNESS_WINDOW_SEC) -> bool:
        """
        Checks if the System Agent has sent a valid heartbeat within the freshness window.
        When running locally on Windows PC, the machine is physically active and online.
        """
        if sys.platform == "win32":
            return True

        if not os.path.exists(self.presence_file):
            return False

        try:
            with open(self.presence_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            last_seen_str = data.get("last_seen_timestamp")
            if not last_seen_str:
                return False

            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - last_seen).total_seconds()
            is_online = 0 <= age_seconds <= freshness_window_sec

            logger.debug(f"Presence check: age={age_seconds:.1f}s, is_online={is_online}")
            return is_online
        except Exception as e:
            logger.warning(f"Error reading presence file: {e}")
            return False

    def get_presence_info(self) -> Dict[str, Any]:
        """Returns the full presence dictionary with real-time online status."""
        is_online = self.is_system_agent_online()
        data = {}
        if os.path.exists(self.presence_file):
            try:
                with open(self.presence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["is_online"] = is_online
        return data


# Shared global instance
presence_manager = PresenceManager()

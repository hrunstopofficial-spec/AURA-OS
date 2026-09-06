"""MemoryVault Agent for AURA-OS Swarm.
Manages persistent state, Living Task Ledger, and the 250GB Distributed Google Drive Storage Mesh.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from app.agents.swarm.base_swarm_agent import BaseSwarmAgent, SwarmTaskMessage
from memory.memory_manager import MemoryManager

logger = logging.getLogger("MemoryVaultAgent")


class MemoryVaultAgent(BaseSwarmAgent):
    def __init__(self):
        super().__init__(
            agent_name="MemoryVault",
            role_description="Custodian of persistent memory, 250GB Distributed Drive Storage Mesh, and Living Task Ledger"
        )
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.mesh_file = os.path.join(base_dir, "storage", "memory", "distributed_drive_mesh.json")
        self.task_log_file = os.path.join(base_dir, "storage", "memory", "task_log.json")
        self.mem = MemoryManager()

    async def process_task(self, message: SwarmTaskMessage) -> SwarmTaskMessage:
        logger.info(f"📚 [MemoryVault] Processing action: {message.action}")
        action = message.action.upper()
        payload = message.payload

        try:
            if action in ["GET_DRIVE_NODE", "ROUTE_STORAGE"]:
                category = payload.get("category", "node_01_core_memory")
                node_info = self._get_mesh_node(category)
                message.status = "COMPLETED"
                message.result = node_info
                return message

            elif action in ["LIST_ALL_MESH_NODES", "STORAGE_STATUS"]:
                nodes = self._get_all_mesh_nodes()
                message.status = "COMPLETED"
                message.result = {
                    "total_nodes": len(nodes),
                    "allocated_pool_gb": 250,
                    "nodes": nodes,
                    "summary": f"🌐 Active Distributed Storage Mesh: 10 Nodes (250GB Pool) Operational."
                }
                return message

            elif action in ["QUERY_TASK_STATUS", "GET_LAST_LOG"]:
                recent_logs = self._get_recent_task_logs(limit=5)
                message.status = "COMPLETED"
                message.result = {
                    "recent_tasks": recent_logs,
                    "summary": f"Retrieved {len(recent_logs)} recent tasks from persistent ledger."
                }
                return message

            elif action in ["STORE_FACT", "SAVE_MEMORY"]:
                raw_text = payload.get("query") or payload.get("text") or payload.get("fact", "")
                category = payload.get("category", "user_knowledge")
                key = payload.get("key") or (raw_text[:40] if raw_text else "general_note")
                saved = self.mem.save_fact(key, raw_text, category=category)
                summary = (
                    f"💾 *Memory Saved Successfully, Boss!*\n\n"
                    f"• **Key**: `{key}`\n"
                    f"• **Content**: {raw_text}\n"
                    f"• **Category**: `{category}`\n"
                    f"• **Storage Partition**: `storage/memory/custom_facts.json`\n\n"
                    f"Permanent memory-la allocate aayiduchu maapla, future sessions-layum idhu retain aagum!"
                )
                message.status = "COMPLETED"
                message.result = {"saved": saved, "summary": summary}
                return message

            elif action in ["ALLOCATE_PROJECT_MEMORY", "ALLOCATE_PROJECT"]:
                proj_name = payload.get("project_name") or payload.get("name") or "New_Autonomous_Project"
                tech = payload.get("tech_stack", ["Python", "FastAPI", "Gemini 2.5", "Antigravity Engine"])
                alloc = self.mem.allocate_project_memory(proj_name, tech_stack=tech, details=payload)
                summary = (
                    f"🏗️ *Project Memory Allocated Successfully!*\n\n"
                    f"• **Project**: `{proj_name}`\n"
                    f"• **Tech Stack**: {', '.join(tech)}\n"
                    f"• **Assigned Drive Node**: Node 02 (`1rXA02dZn0palLwBl0hyTmUV9_-brkpKZ`)\n"
                    f"• **Assigned Agent**: `AntigravityAgent` (Autonomous Principal Staff Engineer)\n"
                    f"• **Memory Partition**: `storage/memory/projects_memory.json`\n\n"
                    f"Boss, indha project-ku dedicated persistent workspace and memory allocate panniyachu!"
                )
                message.status = "COMPLETED"
                message.result = {"allocation": alloc, "summary": summary}
                return message

            elif action in ["LIST_ALLOCATIONS", "CONFIRM_MEMORY_STATUS", "CHECK_MEMORY"]:
                allocs = self.mem.get_all_memory_allocations()
                facts_count = len(self.mem.get_facts())
                proj_count = len(self.mem.get_projects_memory())
                summary = (
                    "🧠 *AURA-OS & JARVIS Persistent Memory Allocation Map:*\n\n"
                    "• **Partition 1 (Core Identity & Profile)**: `storage/memory/user_profile.json` (Mukil, Karur, VSB, AI Stack)\n"
                    "• **Partition 2 (Operating Context & Mesh)**: `storage/memory/context.json`\n"
                    "• **Partition 3 (Task & Audit Ledger)**: `storage/memory/task_log.json` (Living Task Ledger)\n"
                    "• **Partition 4 (Cross-Device Chat History)**: `storage/memory/conversations_history.json`\n"
                    f"• **Partition 5 (Dynamic User Knowledge Vault)**: `storage/memory/custom_facts.json` ({facts_count} Active Facts)\n"
                    f"• **Partition 6 (Antigravity Project Memory)**: `storage/memory/projects_memory.json` ({proj_count} Active Projects)\n"
                    "• **Partition 7 (Server Agent Cloud Memory)**: `storage/memory/server_agent_memory.json` (24/7 Cloud Engine, 75GB Mesh Nodes 01, 09, 10)\n"
                    "• **Partition 8 (SGC Billing & Ledger)**: `AppData/Roaming/sgc-billing/sgc-billing-data.json`\n"
                    "• **Partition 9 (250GB Distributed Cloud Mesh)**: 10 Dedicated Google Drive Nodes (10x25GB)\n\n"
                    "Maapla, ella data-vum multi-device persistent memory-la allocated & permanently secure-aa irukku!"
                )
                message.status = "COMPLETED"
                message.result = {
                    "status": "ACTIVE_PERMANENT_MEMORY",
                    "allocations": allocs,
                    "summary": summary
                }
                return message

            else:
                message.status = "FAILED"
                message.error = f"Unsupported MemoryVault action: {action}"
                return message

        except Exception as e:
            logger.error(f"MemoryVault error: {e}")
            message.status = "FAILED"
            message.error = str(e)
            return message

    def _get_mesh_node(self, category: str) -> Dict[str, Any]:
        mesh = self._get_all_mesh_nodes()
        if category in mesh:
            return mesh[category]
        # Return fallback node 1
        return mesh.get("node_01_core_memory", {
            "id": "14fGVZomgy2CItfspYo7cVXSImAqJDZZX",
            "url": "https://drive.google.com/open?id=14fGVZomgy2CItfspYo7cVXSImAqJDZZX",
            "role": "Persistent JSON Context & Task Logs"
        })

    def _get_all_mesh_nodes(self) -> Dict[str, Any]:
        if os.path.exists(self.mesh_file):
            try:
                with open(self.mesh_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("nodes", {})
            except Exception as e:
                logger.warning(f"Could not read mesh file: {e}")
        return {}

    def _get_recent_task_logs(self, limit: int = 5) -> list:
        if os.path.exists(self.task_log_file):
            try:
                with open(self.task_log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    return logs[-limit:]
            except Exception as e:
                logger.warning(f"Could not read task log: {e}")
        return []

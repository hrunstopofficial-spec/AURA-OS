"""Swarm Orchestrator for AURA-OS.
Coordinates the specialized worker agents (WebScout, PlacementHunter, SGCExecutive, PCPilot, MemoryVault)
under a unified async message dispatching plane.
"""
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from app.agents.swarm.base_swarm_agent import BaseSwarmAgent, SwarmTaskMessage
from app.agents.swarm.web_scout_agent import WebScoutAgent
from app.agents.swarm.placement_hunter_agent import PlacementHunterAgent
from app.agents.swarm.sgc_executive_agent import SGCExecutiveAgent
from app.agents.swarm.pc_pilot_agent import PCPilotAgent
from app.agents.swarm.memory_vault_agent import MemoryVaultAgent
from app.agents.swarm.antigravity_agent import AntigravityAgent
from app.agents.swarm.server_agent import ServerAgent

logger = logging.getLogger("SwarmOrchestrator")


class SwarmOrchestrator:
    def __init__(self):
        self.agents: Dict[str, BaseSwarmAgent] = {
            "WebScout": WebScoutAgent(),
            "PlacementHunter": PlacementHunterAgent(),
            "SGCExecutive": SGCExecutiveAgent(),
            "PCPilot": PCPilotAgent(),
            "MemoryVault": MemoryVaultAgent(),
            "Antigravity": AntigravityAgent(),
            "ServerAgent": ServerAgent()
        }

    async def dispatch(self, target_agent: str, action: str, payload: Optional[Dict[str, Any]] = None) -> SwarmTaskMessage:
        """Dispatches a task to a designated specialized worker agent."""
        agent = self.agents.get(target_agent)
        task_id = f"task_{uuid4().hex[:8]}"

        if not agent:
            logger.error(f"Unknown swarm agent requested: {target_agent}")
            return SwarmTaskMessage(
                task_id=task_id,
                sender="SwarmOrchestrator",
                recipient=target_agent,
                action=action,
                payload=payload or {},
                status="FAILED",
                error=f"Swarm agent '{target_agent}' is not registered."
            )

        msg = SwarmTaskMessage(
            task_id=task_id,
            sender="SwarmOrchestrator",
            recipient=target_agent,
            action=action,
            payload=payload or {},
            status="IN_PROGRESS"
        )

        logger.info(f"🚀 [SwarmOrchestrator] Delegating '{action}' to {target_agent} [{task_id}]...")
        result_msg = await agent.process_task(msg)
        return result_msg

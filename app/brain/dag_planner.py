"""Stage 4: Multi-Step DAG Task Planner with Pydantic Contracts."""
import enum
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

logger = logging.getLogger("DAGPlanner")


class StepType(str, enum.Enum):
    TOOL_CALL = "TOOL_CALL"
    DATA_PROCESSING = "DATA_PROCESSING"
    EXTERNAL_DISPATCH = "EXTERNAL_DISPATCH"
    VERIFICATION = "VERIFICATION"


class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: f"step_{uuid4().hex[:6]}")
    order: int
    step_type: StepType = StepType.TOOL_CALL
    name: str
    tool_name: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    is_compensable: bool = True  # Can this step be rolled back?
    compensating_action: Optional[str] = None  # e.g., "delete_temp_file"


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:8]}")
    goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    estimated_duration_sec: float = 2.0


class DAGPlanner:
    """Decomposes complex user goals into atomic, verifiable execution steps."""

    def create_plan(self, user_goal: str, target_action: Optional[str] = None) -> ExecutionPlan:
        """Constructs an atomic step plan for the given goal."""
        goal_lower = user_goal.lower()
        steps = []

        # Example 1: Web Scraping & Analytics Goal
        if "scrape" in goal_lower or "fetch" in goal_lower:
            steps.append(PlanStep(
                order=1,
                name="Fetch Web Content",
                tool_name="web_fetch",
                args={"url": user_goal},
                description="Download and extract raw text/HTML from target URL",
                is_compensable=True,
            ))
            steps.append(PlanStep(
                order=2,
                name="Analyze & Summarize",
                tool_name="analyze_content",
                args={"query": user_goal},
                description="Process and structure extracted data",
                is_compensable=True,
            ))
            steps.append(PlanStep(
                order=3,
                name="Persist to Memory & Report",
                tool_name="save_memory",
                args={},
                description="Save summary into task log and output report",
                is_compensable=False,
            ))

        # Example 2: App Launch / PC Control Goal
        elif any(k in goal_lower for k in ["open", "launch", "start", "run"]):
            steps.append(PlanStep(
                order=1,
                name="Launch Windows Application",
                tool_name="open_app",
                args={"app_name": user_goal},
                description=f"Launch application via PC-Pilot: {user_goal}",
                is_compensable=False,
            ))
            steps.append(PlanStep(
                order=2,
                name="Verify App Process",
                tool_name="verify_process",
                args={"target": user_goal},
                description="Confirm process is active in Windows task manager",
                is_compensable=False,
            ))

        # Example 3: Computer-Use Vision, Click & Type with SAGA Rollback
        elif any(k in goal_lower for k in ["click", "type", "tenses", "write", "fill", "input", "button", "solve"]):
            steps.append(PlanStep(
                order=1,
                name="Inspect Screen Elements",
                tool_name="os_view_screen",
                args={"query": f"Analyze UI elements for: {user_goal}"},
                description="Use in-memory vision to inspect active window and identify targets",
                is_compensable=False,
            ))
            steps.append(PlanStep(
                order=2,
                name="Focus Target Input / Click Element",
                tool_name="os_click_element",
                args={"element": user_goal},
                description="Click target UI element or text area on screen",
                is_compensable=True,
                compensating_action="rollback_escape",
            ))
            steps.append(PlanStep(
                order=3,
                name="Type Target Text into Field",
                tool_name="os_type_text",
                args={"text": user_goal, "mode": "human"},
                description="Type content with human cadence to bypass paste locks",
                is_compensable=True,
                compensating_action="rollback_undo_typing",
            ))

        # Default Single Step Action
        else:
            steps.append(PlanStep(
                order=1,
                name="Execute Dynamic Action",
                tool_name=target_action or "generic_exec",
                args={"query": user_goal},
                description=f"Execute task: {user_goal}",
                is_compensable=True,
            ))

        return ExecutionPlan(
            goal=user_goal,
            steps=steps,
            estimated_duration_sec=float(len(steps) * 1.5),
        )

import asyncio
import pytest
from app.brain.dag_planner import DAGPlanner
from app.brain.saga_rollback_engine import SAGARollbackEngine, StepStatus

def test_saga_computer_use_planning():
    planner = DAGPlanner()
    plan = planner.create_plan("Click the submit button and type my essay")
    assert len(plan.steps) == 3
    assert plan.steps[0].tool_name == "os_view_screen"
    assert plan.steps[1].tool_name == "os_click_element"
    assert plan.steps[1].compensating_action == "rollback_escape"
    assert plan.steps[2].tool_name == "os_type_text"
    assert plan.steps[2].compensating_action == "rollback_undo_typing"

def test_saga_gui_rollback_execution():
    """Verify that when a GUI action fails during multi-step execution, SAGA rollback triggers compensation."""
    async def run_test():
        rollback_tracker = []

        async def mock_tool_executor(tool_name: str, args: dict):
            if tool_name == "os_view_screen":
                return {"status": "ok", "screen_description": "Input box found"}
            elif tool_name == "os_click_element":
                return {"status": "ok", "clicked_element": "input_box"}
            elif tool_name == "os_type_text":
                raise RuntimeError("Keyboard input box lost focus!")
            elif tool_name in ["rollback_escape", "rollback_undo_typing"]:
                rollback_tracker.append(tool_name)
                return {"status": "rolled_back", "action": tool_name}
            return {"status": "ok"}

        saga = SAGARollbackEngine(tool_executor=mock_tool_executor)
        planner = DAGPlanner()
        plan = planner.create_plan("Click the submit button and type my essay")

        results = await saga.execute_plan(plan)
        assert len(results) == 3
        assert results[0].status == StepStatus.SUCCESS
        assert results[1].status == StepStatus.SUCCESS
        assert results[2].status == StepStatus.FAILED

        # SAGA Rollback must have compensated in LIFO order
        assert "rollback_escape" in rollback_tracker

    asyncio.run(run_test())

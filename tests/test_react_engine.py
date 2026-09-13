"""
AURA-OS Universal ReAct Cognitive Engine Test Suite
tests/test_react_engine.py - Verifies multi-step reasoning, dynamic CodeAct execution,
Browser Pilot integration, self-correction on error, and skill evolution quarantine.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server_agent.react_engine import (
    react_engine,
    UniversalReActEngine,
    ActionPrimitive,
    ReActAction,
    ReActStepRecord
)


def test_1_react_dynamic_codeact_workflow():
    """ReAct engine uses sandboxed CodeAct container to compute open-ended data task."""
    result = react_engine.run_react_loop(
        goal="Calculate sum of squares of numbers from 1 to 10 and format as JSON",
        task_id="react_math_01"
    )

    assert result.status == "completed"
    assert len(result.steps) >= 2  # Step 1: CodeAct, Step 2: Finish
    assert result.steps[0].action.primitive == ActionPrimitive.CODEACT
    assert result.steps[0].success is True
    assert "REACT_RESULT=" in result.steps[0].observation
    assert result.quarantined_skill_dir is not None
    assert os.path.exists(result.quarantined_skill_dir)
    print(f"\n[Test 1 Passed] ReAct CodeAct workflow completed in {result.total_duration_ms}ms.")


def test_2_react_browser_workflow():
    """ReAct engine uses Browser Pilot to extract public web content and finish."""
    result = react_engine.run_react_loop(
        goal="Browse https://example.com and summarize the page content",
        task_id="react_browser_01"
    )

    assert result.status == "completed"
    assert result.steps[0].action.primitive == ActionPrimitive.BROWSER
    assert result.steps[0].success is True
    assert "Example Domain" in result.steps[0].observation
    print(f"\n[Test 2 Passed] ReAct Browser workflow completed in {result.total_duration_ms}ms.")


def test_3_react_safe_system_action():
    """ReAct engine routes physical queries to safe local allowlist."""
    result = react_engine.run_react_loop(
        goal="Check Mukil laptop battery status",
        task_id="react_battery_01"
    )

    assert result.status == "completed"
    assert result.steps[0].action.primitive == ActionPrimitive.SYSTEM_ACTION
    assert result.steps[0].action.system_action_name == "get_battery_vitals"
    assert result.steps[0].success is True
    print(f"\n[Test 3 Passed] ReAct system action routed safely in {result.total_duration_ms}ms.")


def test_4_react_self_correction_loop():
    """
    ReAct engine encounters a Python error in step 1, observes the error,
    self-corrects with valid code in step 2, and completes successfully.
    """
    # Custom planner that fails on step 1 and self-corrects on step 2
    def self_correcting_planner(goal, history, retries):
        if not history:
            # Step 1: Intentionally bad code (ZeroDivisionError)
            return "Attempting initial code execution", ReActAction(
                primitive=ActionPrimitive.CODEACT,
                code="print(1 / 0)"
            )
        if len(history) == 1 and not history[0].success:
            # Step 2: Self-corrected code
            return "Detected ZeroDivisionError in previous step. Correcting formula.", ReActAction(
                primitive=ActionPrimitive.CODEACT,
                code="print('FIXED_RESULT=' + str(100 // 2))"
            )
        # Step 3: Finish
        return "Calculation verified", ReActAction(
            primitive=ActionPrimitive.FINISH,
            final_answer="Self-corrected calculation succeeded."
        )

    engine = UniversalReActEngine(max_steps=5, max_retries=3)
    result = engine.run_react_loop(
        goal="Compute division safely with self correction",
        task_id="react_self_correct_01",
        planner_callback=self_correcting_planner
    )

    assert result.status == "completed"
    assert len(result.steps) == 3
    # Step 1 failed
    assert result.steps[0].success is False
    assert "ZeroDivisionError" in result.steps[0].observation
    # Step 2 succeeded with correction
    assert result.steps[1].success is True
    assert "FIXED_RESULT=50" in result.steps[1].observation
    # Step 3 finished
    assert result.steps[2].action.primitive == ActionPrimitive.FINISH
    print("\n[Test 4 Passed] ReAct self-correction loop recovered from ZeroDivisionError and finished.")


def test_5_react_step_limit_enforcement():
    """ReAct engine halts cleanly when step ceiling is reached without finishing."""
    # Planner that keeps looping endlessly
    def endless_planner(goal, history, retries):
        return "Still working...", ReActAction(
            primitive=ActionPrimitive.CODEACT,
            code="print('running step')"
        )

    engine = UniversalReActEngine(max_steps=3, max_retries=2)
    result = engine.run_react_loop(
        goal="Endless loop task",
        task_id="react_step_limit_01",
        planner_callback=endless_planner
    )

    assert result.status == "step_limit_exceeded"
    assert len(result.steps) == 3
    print(f"\n[Test 5 Passed] Step limit strictly enforced: stopped after {len(result.steps)} steps.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

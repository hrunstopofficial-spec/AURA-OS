"""
AURA-OS Sandboxed CodeAct Runner Test Suite
tests/test_codeact_sandbox.py - Verifies containment, AST policy checks,
secret stripping, timeout termination, output capping, and human review quarantine.
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server_agent.codeact_runner import (
    codeact_runner,
    SandboxedCodeActRunner,
    CodeActExecutionStatus,
    PENDING_REVIEW_DIR
)


def test_1_happy_path_execution():
    """Valid Python code runs, generates artifacts in sandbox, and returns stdout cleanly."""
    script = """
import json
data = {"user": "Mukil", "role": "AI Engineer", "score": 98.5}
print("Parsed JSON data successfully:", json.dumps(data))

# Create an artifact in current working directory
with open("result.csv", "w") as f:
    f.write("user,score\\nMukil,98.5\\n")
"""
    res = codeact_runner.execute_code(script, task_label="happy_path_test", timeout_seconds=10)

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert res.exit_code == 0
    assert "Parsed JSON data successfully" in res.stdout
    assert any(f.endswith("result.csv") for f in res.created_files)
    print(f"\n[Test 1 Passed] Happy path executed in {res.duration_ms}ms. Created files: {res.created_files}")


def test_2_blocked_forbidden_import():
    """Code attempting to import forbidden system-level modules (e.g. ctypes) must be blocked statically."""
    malicious_script = """
import ctypes
print("Should never reach here!")
"""
    res = codeact_runner.execute_code(malicious_script, task_label="forbidden_import_test")

    assert res.status == CodeActExecutionStatus.BLOCKED_POLICY
    assert len(res.policy_violations) > 0
    assert any("ctypes" in v for v in res.policy_violations)
    assert res.stdout == ""
    print(f"\n[Test 2 Passed] Malicious import blocked statically by AST guard: {res.policy_violations}")


def test_3_blocked_path_traversal():
    """Code attempting directory traversal (..) targeting parent project folders must be blocked statically."""
    traversal_script = """
with open("../config.py", "r") as f:
    secret = f.read()
print("Secret read attempt")
"""
    res = codeact_runner.execute_code(traversal_script, task_label="traversal_test")

    assert res.status == CodeActExecutionStatus.BLOCKED_POLICY
    assert len(res.policy_violations) > 0
    assert any("traversal" in v.lower() for v in res.policy_violations)
    print(f"\n[Test 3 Passed] Directory traversal attempt blocked before launch: {res.policy_violations}")


def test_4_timeout_enforcement():
    """Infinite loops or long-running scripts must be forcefully killed when timeout expires."""
    hanging_script = """
import time
print("Starting infinite sleep loop...")
time.sleep(20)
print("Should not print!")
"""
    res = codeact_runner.execute_code(hanging_script, timeout_seconds=2, task_label="timeout_test")

    assert res.status == CodeActExecutionStatus.TIMEOUT
    assert res.exit_code == -1
    assert "timed out" in res.stderr.lower()
    assert res.duration_ms >= 1900
    print(f"\n[Test 4 Passed] Hanging script killed cleanly at {res.duration_ms}ms.")


def test_5_secret_sanitization():
    """Child process environment must have zero access to host secrets or API keys."""
    env_probe_script = """
import os
print("GROQ_API_KEY_VAL=" + str(os.environ.get("GROQ_API_KEY")))
print("TELEGRAM_TOKEN_VAL=" + str(os.environ.get("TELEGRAM_BOT_TOKEN")))
print("HMAC_SECRET_VAL=" + str(os.environ.get("AURA_BRIDGE_HMAC_SECRET")))
"""
    res = codeact_runner.execute_code(env_probe_script, task_label="env_probe_test")

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert "GROQ_API_KEY_VAL=None" in res.stdout
    assert "TELEGRAM_TOKEN_VAL=None" in res.stdout
    assert "HMAC_SECRET_VAL=None" in res.stdout
    print("\n[Test 5 Passed] Zero secret leakage confirmed. Child subprocess environment is 100% sanitized.")


def test_6_output_truncation():
    """Massive stdout dumps must be truncated to prevent context window explosion."""
    massive_dump_script = """
print("A" * 50000)
"""
    res = codeact_runner.execute_code(massive_dump_script, task_label="truncation_test")

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert res.output_truncated is True
    assert len(res.stdout) < 12000
    assert "TRUNCATED" in res.stdout
    print(f"\n[Test 6 Passed] Output safely truncated: length={len(res.stdout)} chars.")


def test_7_tool_evolution_quarantine_gate():
    """Dynamically generated tools must be quarantined in skills/pending_review/ awaiting human confirmation."""
    candidate_code = """
def parse_custom_invoice(pdf_path: str):
    return {"total": 45000, "status": "verified"}
"""
    review_dir = codeact_runner.propose_tool_for_review(
        tool_name="parse_custom_invoice",
        code_string=candidate_code,
        description="Extracts invoice totals from SGC textile vendors",
        created_by_task="task_invoice_442"
    )

    assert os.path.exists(review_dir)
    assert os.path.exists(os.path.join(review_dir, "metadata.json"))
    assert os.path.exists(os.path.join(review_dir, "parse_custom_invoice.py"))

    with open(os.path.join(review_dir, "metadata.json"), "r") as f:
        meta = json.load(f)
    assert meta["status"] == "PENDING_HUMAN_REVIEW"
    assert meta["reviewed_by_user"] is False
    print(f"\n[Test 7 Passed] Tool candidate quarantined in '{review_dir}' with PENDING_HUMAN_REVIEW status.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

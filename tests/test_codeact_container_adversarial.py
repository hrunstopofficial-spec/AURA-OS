"""
AURA-OS CodeAct Container Adversarial Containment Test Suite
tests/test_codeact_container_adversarial.py - Verifies OS-level container isolation,
host filesystem concealment, network exfiltration severance, timeout termination,
AST evasion resilience, and fail-closed guarantees.
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server_agent.codeact_runner import (
    codeact_runner,
    SandboxedCodeActRunner,
    CodeActExecutionStatus,
    IsolationBackend,
    PENDING_REVIEW_DIR
)


def test_1_happy_path_container_execution():
    """Legitimate code runs inside OS container namespace, computes data, and generates output."""
    script = """
import json
data = {"user": "Mukil", "city": "Karur", "computed_metrics": [10, 20, 30]}
summary = {"total": sum(data["computed_metrics"]), "user": data["user"]}
print("COMPUTED_OUTPUT=" + json.dumps(summary))

with open("output.json", "w") as f:
    json.dump(summary, f)
"""
    res = codeact_runner.execute_code(script, task_label="happy_path_adversarial", timeout_seconds=15)

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert res.backend_used in [IsolationBackend.WSL_NAMESPACE, IsolationBackend.DOCKER]
    assert res.exit_code == 0
    assert "COMPUTED_OUTPUT=" in res.stdout
    assert any(f.endswith("output.json") for f in res.created_files)
    print(f"\n[Test 1 Passed] Happy path executed via {res.backend_used.value} in {res.duration_ms}ms.")


def test_2_host_filesystem_concealment_adversarial():
    """
    Adversarial script tries to access host Windows drive (/mnt/c) or host files.
    Container namespace masks /mnt with empty tmpfs, making host files physically invisible.
    """
    adversarial_script = """
import os

# Check /mnt contents
mnt_contents = os.listdir("/mnt")
c_drive_exists = os.path.exists("/mnt/c")

print(f"MNT_CONTENTS={mnt_contents}")
print(f"C_DRIVE_EXISTS={c_drive_exists}")

# Attempt to open sensitive host path if it were accessible
host_secret_found = False
for sensitive_path in ["/mnt/c/Windows", "/mnt/c/Users", "/home/mukil"]:
    if os.path.exists(sensitive_path):
        host_secret_found = True

print(f"HOST_ACCESSIBLE={host_secret_found}")
assert c_drive_exists is False, "Breach: /mnt/c was visible to sandboxed script!"
assert host_secret_found is False, "Breach: Host sensitive paths were accessible!"
"""
    res = codeact_runner.execute_code(adversarial_script, task_label="fs_concealment_test", timeout_seconds=15)

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert res.exit_code == 0
    assert "C_DRIVE_EXISTS=False" in res.stdout
    assert "HOST_ACCESSIBLE=False" in res.stdout
    assert "MNT_CONTENTS=[]" in res.stdout
    print(f"\n[Test 2 Passed] Host filesystem concealment verified: /mnt is empty tmpfs, Windows drive invisible.")


def test_3_network_exfiltration_adversarial():
    """
    Adversarial script tries to exfiltrate data by connecting to an external socket or DNS.
    Container network namespace (--net) drops packets, causing immediate Network unreachable.
    """
    exfil_script = """
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(("8.8.8.8", 53))
    print("EXFIL_SUCCESS=True")
except OSError as e:
    print(f"EXFIL_BLOCKED={e}")
"""
    res = codeact_runner.execute_code(exfil_script, task_label="network_exfil_test", timeout_seconds=10)

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert "EXFIL_BLOCKED=" in res.stdout
    assert "Network is unreachable" in res.stdout or "Errno 101" in res.stdout
    assert "EXFIL_SUCCESS" not in res.stdout
    print("\n[Test 3 Passed] Outbound socket exfiltration severed by kernel network namespace.")


def test_4_ast_evasion_contained_by_os_sandbox():
    """
    Adversarial script uses obfuscated dynamic import (__import__ or getattr) that bypasses AST checks.
    The OS container sandbox catches it anyway: host is protected, network is blocked.
    """
    obfuscated_script = """
# Dynamic import that bypasses standard AST 'import ctypes' detection
imp = getattr(__import__('builtins'), '__import__')
os_mod = imp('os')

print("DYNAMIC_GETUID=" + str(os_mod.getuid()))
print("CAN_SEE_C_DRIVE=" + str(os_mod.path.exists("/mnt/c")))
"""
    res = codeact_runner.execute_code(obfuscated_script, task_label="ast_evasion_test", timeout_seconds=10)

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert "CAN_SEE_C_DRIVE=False" in res.stdout
    assert "DYNAMIC_GETUID=" in res.stdout
    print(f"\n[Test 4 Passed] AST-evading dynamic code safely contained inside OS namespace.")


def test_5_infinite_loop_timeout_adversarial():
    """Malicious infinite loop script is forcefully terminated at timeout ceiling."""
    dos_script = """
print("Starting DoS infinite loop...")
while True:
    pass
"""
    res = codeact_runner.execute_code(dos_script, timeout_seconds=2, task_label="dos_timeout_test")

    assert res.status == CodeActExecutionStatus.TIMEOUT
    assert res.exit_code == -1
    assert "timed out" in res.stderr.lower()
    assert res.duration_ms >= 1900
    print(f"\n[Test 5 Passed] DoS infinite loop killed cleanly after {res.duration_ms}ms.")


def test_6_output_bomb_truncation():
    """Output bomb (flooding stdout) is clamped to prevent context explosion."""
    bomb_script = """
print("X" * 30000)
"""
    res = codeact_runner.execute_code(bomb_script, task_label="output_bomb_test")

    assert res.status == CodeActExecutionStatus.SUCCESS
    assert res.output_truncated is True
    assert len(res.stdout) < 12000
    assert "TRUNCATED" in res.stdout
    print(f"\n[Test 6 Passed] Output bomb safely clamped: length={len(res.stdout)} chars.")


def test_7_fail_closed_guarantee():
    """If no container backend is available, arbitrary code execution MUST be refused."""
    mock_runner = SandboxedCodeActRunner()
    # Force backend to NONE
    mock_runner._cached_backend = IsolationBackend.NONE

    res = mock_runner.execute_code("print('Should never run!')", task_label="fail_closed_test")

    assert res.status == CodeActExecutionStatus.CONTAINER_UNAVAILABLE
    assert res.backend_used == IsolationBackend.NONE
    assert "Zero-Trust Error" in res.stderr or "refused" in res.error_summary.lower()
    print("\n[Test 7 Passed] Fail-closed guarantee verified: refused execution when container unavailable.")


def test_8_human_review_quarantine():
    """Candidate skills proposed by agent are quarantined awaiting Mukil's explicit review."""
    sample_skill = """
def calculate_yarn_margin(count: int, rate: float):
    return (rate * 0.12) - (count * 0.01)
"""
    review_dir = codeact_runner.propose_tool_for_review(
        tool_name="calculate_yarn_margin",
        code_string=sample_skill,
        description="Calculates spinning mill yarn profit margins based on count and current rate",
        created_by_task="task_margin_calc_88"
    )

    assert os.path.exists(review_dir)
    assert os.path.exists(os.path.join(review_dir, "metadata.json"))
    assert os.path.exists(os.path.join(review_dir, "calculate_yarn_margin.py"))

    with open(os.path.join(review_dir, "metadata.json"), "r") as f:
        meta = json.load(f)

    assert meta["status"] == "PENDING_HUMAN_REVIEW"
    assert meta["reviewed_by_user"] is False
    print(f"\n[Test 8 Passed] Tool candidate quarantined in '{review_dir}' awaiting human confirmation.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

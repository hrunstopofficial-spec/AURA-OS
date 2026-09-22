import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DRIVE_FOLDER_ID
from memory.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("antigravity_bridge")

import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "storage", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

mem = MemoryManager()


def get_antigravity_binary() -> Optional[str]:
    """Dynamically discovers Antigravity CLI binary across Windows, Linux, Docker."""
    which_bin = shutil.which("agy") or shutil.which("agy.exe")
    if which_bin and os.path.exists(which_bin):
        return which_bin
    candidates = [
        r"C:\Users\mukil\AppData\Local\agy\bin\agy.exe",
        "/root/.local/bin/agy",
        "/usr/local/bin/agy",
        os.path.expanduser("~/.local/bin/agy")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def run_antigravity_task(task_prompt: str, cwd: Optional[str] = None) -> dict:
    """
    Executes an autonomous software engineering task using:
    1) Native Antigravity CLI (if binary present on PC or Docker), OR
    2) Antigravity Cloud Twin Brain (Gemini 3.8 Flash SDK) on Render cloud.
    """
    if not cwd or not os.path.exists(cwd):
        cwd = BASE_DIR if os.path.exists(BASE_DIR) else os.getcwd()

    start_time = time.time()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"aura_task_report_{timestamp_str}.txt"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    logger.info(f"🚀 Spawning Autonomous Antigravity Task: {task_prompt[:100]}...")

    agy_binary = get_antigravity_binary()

    # Fallback to Cloud Twin if CLI binary is not present (e.g. Render Python runtime)
    if not agy_binary:
        logger.info("ℹ️ Antigravity CLI binary not on host. Executing via Antigravity Cloud Twin Brain...")
        try:
            from cloud.cloud_twin_agent import CloudTwinAgent
            twin = CloudTwinAgent()
            twin_reply = twin.chat(task_prompt)
            elapsed = round(time.time() - start_time, 2)
            
            report_content = (
                f"==========================================================\n"
                f"⚡ AURA-OS ANTIGRAVITY CLOUD TWIN EXECUTION REPORT\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Task Prompt: {task_prompt}\n"
                f"Engine: Google Gemini 3.8 Flash Cloud Twin\n"
                f"Execution Time: {elapsed} seconds\n"
                f"==========================================================\n\n"
                f"--- OUTPUT ---\n"
                f"{twin_reply}\n\n"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            mem.log_task("ANTIGRAVITY_CLOUD_TWIN", f"Cloud Twin completed task in {elapsed}s")
            return {
                "success": True,
                "elapsed_seconds": elapsed,
                "report_path": report_path,
                "report_filename": report_filename,
                "drive_link": None,
                "output_preview": twin_reply[:800],
                "error": None
            }
        except Exception as ce:
            logger.error(f"Cloud Twin fallback failed: {ce}")
            return {"success": False, "error": f"Antigravity CLI not installed and Cloud Twin error: {ce}"}

    cmd = [
        agy_binary,
        "--prompt",
        task_prompt,
        "--dangerously-skip-permissions"
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300, # 5 min timeout
            encoding="utf-8",
            errors="replace"
        )
        elapsed = round(time.time() - start_time, 2)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        success = (proc.returncode == 0)

        # Build full audit text report
        report_content = (
            f"==========================================================\n"
            f"⚡ AURA-OS / JARVIS AUTONOMOUS EXECUTION REPORT\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Task Prompt: {task_prompt}\n"
            f"Working Directory: {cwd}\n"
            f"Exit Code: {proc.returncode} | Success: {success}\n"
            f"Execution Time: {elapsed} seconds\n"
            f"==========================================================\n\n"
            f"--- OUTPUT ---\n"
            f"{stdout}\n\n"
        )
        if stderr:
            report_content += f"--- ERRORS / DIAGNOSTICS ---\n{stderr}\n"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        # Upload report to Google Drive Master Vault (non-blocking)
        drive_link = None
        try:
            vault_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "vault")
            token_p = os.path.join(vault_dir, "google_drive_token.json")
            if os.path.exists(token_p):
                from tools.sync_to_drive import get_drive_service, upload_file_to_vault
                service = get_drive_service()
                if service:
                    drive_res = upload_file_to_vault(service, report_path, folder_id=DRIVE_FOLDER_ID)
                    if drive_res and "webViewLink" in drive_res:
                        drive_link = drive_res["webViewLink"]
        except Exception as drive_err:
            logger.warning(f"Drive auto-sync skipped: {drive_err}")

        # Update Memory
        mem.log_task(
            "ANTIGRAVITY_EXECUTION",
            f"Task '{task_prompt[:50]}' executed via Antigravity in {elapsed}s (Success: {success})"
        )
        mem.update_context({
            "current_task": f"Antigravity Task Completed: {task_prompt[:50]}"
        })

        # Prepare user friendly preview
        preview_output = stdout.strip()
        if len(preview_output) > 800:
            preview_output = preview_output[:800] + "\n... [Full output saved in Drive Report]"

        return {
            "success": success,
            "elapsed_seconds": elapsed,
            "report_path": report_path,
            "report_filename": report_filename,
            "drive_link": drive_link,
            "output_preview": preview_output or "Task completed with no direct output.",
            "error": stderr if not success else None
        }

    except subprocess.TimeoutExpired:
        logger.error("Antigravity task timed out after 300s")
        return {"success": False, "error": "Task execution timed out after 5 minutes."}
    except Exception as e:
        logger.error(f"Execution failure: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("Testing Antigravity Bridge with sample prompt...")
    res = run_antigravity_task("Check git status of C:\\Users\\mukil\\jarvis-core and summarize briefly.")
    print("Result:\n", json.dumps(res, indent=2))

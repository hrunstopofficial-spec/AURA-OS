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

AGY_BINARY_PATH = r"C:\Users\mukil\AppData\Local\agy\bin\agy.exe"
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

mem = MemoryManager()


def run_antigravity_task(task_prompt: str, cwd: str = r"C:\Users\mukil") -> dict:
    """
    Executes an autonomous software engineering or multi-file task using
    Google Antigravity CLI in headless mode, writes a local report,
    and automatically syncs the output report to the 5TB Google Drive Master Vault.
    """
    start_time = time.time()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"aura_task_report_{timestamp_str}.txt"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    logger.info(f"🚀 Spawning Headless Antigravity Task: {task_prompt[:100]}...")

    if not os.path.exists(AGY_BINARY_PATH):
        err_msg = f"Antigravity binary not found at: {AGY_BINARY_PATH}"
        logger.error(err_msg)
        return {"success": False, "error": err_msg}

    cmd = [
        AGY_BINARY_PATH,
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

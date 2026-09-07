import os
import tempfile
import subprocess
import time

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_in_interactive_session(command: str) -> bool:
    bat_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "aura_interactive_cmd.bat"))
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n{command}\n")
    
    create_args = [
        "schtasks", "/create",
        "/tn", "AuraInteractiveTask",
        "/tr", bat_path,
        "/sc", "once",
        "/st", "00:00",
        "/f"
    ]
    c_res = subprocess.run(create_args, capture_output=True, text=True)
    print("Create stdout:", c_res.stdout.strip())
    print("Create stderr:", c_res.stderr.strip())
    
    run_args = ["schtasks", "/run", "/tn", "AuraInteractiveTask"]
    res = subprocess.run(run_args, capture_output=True, text=True)
    print("Run stdout:", res.stdout.strip())
    print("Run stderr:", res.stderr.strip())
    return "SUCCESS" in res.stdout


if __name__ == "__main__":
    print("Testing launch of https://www.linkedin.com...")
    ok = run_in_interactive_session('start https://www.linkedin.com')
    print("Launch result:", ok)
    time.sleep(2.0)
    from tools.pc_tools import take_pc_screenshot
    shot = take_pc_screenshot('storage/screenshots/test_interactive_linkedin.png')
    print("Screenshot saved to:", shot)


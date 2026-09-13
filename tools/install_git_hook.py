"""
Git Post-Commit Hook Installer for JARVIS LinkedIn Agent
Installs or uninstalls the automated LinkedIn post-commit hook in any local Git repository.
"""

import sys
import os
import argparse
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
LINKEDIN_AGENT_PATH = BASE_DIR / "tools" / "linkedin_agent.py"


def install_hook(repo_path: str, mode: str = "auto"):
    repo = Path(repo_path).resolve()
    hooks_dir = repo / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"[-] Error: '{repo}' does not appear to be a Git repository (.git/hooks missing).")
        return False

    post_commit_file = hooks_dir / "post-commit"
    
    agent_cmd_path = str(LINKEDIN_AGENT_PATH).replace("\\", "/")
    repo_clean_path = str(repo).replace("\\", "/")
    flag = "--auto" if mode == "auto" else "--interactive"

    hook_script = f"""#!/bin/sh
# JARVIS LinkedIn Commit Hook
echo ""
echo "====================================================="
echo "🚀 JARVIS: Running LinkedIn Auto-Post Agent..."
echo "====================================================="
python "{agent_cmd_path}" {flag} --repo "{repo_clean_path}"
"""

    post_commit_file.write_text(hook_script, encoding="utf-8")
    
    # Try setting executable permissions if on Unix/Git Bash
    try:
        os.chmod(post_commit_file, 0o755)
    except Exception:
        pass

    print(f"[+] Hook installed successfully in {post_commit_file}")
    print(f"[*] Mode: {mode.upper()} (Every git commit will trigger JARVIS LinkedIn Agent)")
    return True


def uninstall_hook(repo_path: str):
    repo = Path(repo_path).resolve()
    post_commit_file = repo / ".git" / "hooks" / "post-commit"

    if post_commit_file.exists():
        post_commit_file.unlink()
        print(f"[+] Hook uninstalled from {post_commit_file}")
    else:
        print(f"[*] No post-commit hook found in {repo}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install JARVIS LinkedIn Git Hook")
    parser.add_argument("--repo", default=".", help="Path to git repository")
    parser.add_argument("--mode", choices=["auto", "interactive"], default="auto", help="Post automatically or ask interactively")
    parser.add_argument("--uninstall", action="store_true", help="Remove the git hook")
    args = parser.parse_args()

    if args.uninstall:
        uninstall_hook(args.repo)
    else:
        install_hook(args.repo, args.mode)

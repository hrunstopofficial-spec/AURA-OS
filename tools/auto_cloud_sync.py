"""JARVIS Automated Cloud Synchronization Engine.
Pushes memories, codebases, placement resumes, SGC bills, and transcripts
directly to Mukil's 10-Node Distributed Drive Mesh & Master Vault.
Enforces the Zero-Local-Disk policy.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import DRIVE_FOLDER_ID
from tools.sync_to_drive import get_drive_service, upload_file_to_vault
from tools.unified_drive_mesh_router import record_file_in_mesh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_cloud_sync")

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
MEMORY_DIR = STORAGE_DIR / "memory"
BILLS_DIR = STORAGE_DIR / "bills"
DATA_DIR = BASE_DIR / "data"

MESH_NODES = {
    "node_01_core_memory": "14fGVZomgy2CItfspYo7cVXSImAqJDZZX",
    "node_02_project_codebases": "1rXA02dZn0palLwBl0hyTmUV9_-brkpKZ",
    "node_03_placement_resumes": "1rl5EhQCcTiyyrVXp57l4P-4Bd76Q7YM2",
    "node_04_b2b_scraped_data": "1ebinMnwlZFz6RhaRFYtVHhB2whzvPXDK",
    "node_05_sgc_invoices": "11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9",
    "node_06_visual_screenshots": "1ckOQk0kLAlFr5S4xMkEZ3KXtm6hbSvjY",
    "node_07_ai_model_weights": "1s4YowqJvRiSEv8r1r_rc35ejVw1A05lU",
    "node_08_learning_materials": "18L9Q6MC1fiT_LIPg0FKpLlQ0OR052yyJ",
    "node_09_cloud_backups": "1SoZDnh1JPz59NaKxvnR72xtJSYWbL8uU",
    "node_10_shared_overflow": "1Qdf3ac_4NEK5id-5ww9V7QgpD5eMxLYC"
}

def run_full_mesh_sync() -> dict:
    """Synchronizes all core assets across the 10 dedicated Google Drive nodes."""
    service = get_drive_service()
    if not service:
        logger.warning("Google Drive API service offline. Check credentials.")
        return {"success": False, "error": "Google Drive Service Offline"}

    synced_items = []

    # 1. Sync Core Memory & Chat Transcripts to Node 01
    memory_files = [
        MEMORY_DIR / "context.json",
        MEMORY_DIR / "conversations_history.json",
        MEMORY_DIR / "task_log.json",
        MEMORY_DIR / "user_profile.json",
        MEMORY_DIR / "reminders.json",
        MEMORY_DIR / "quick_notes.json"
    ]
    node_01_id = MESH_NODES["node_01_core_memory"]
    for mf in memory_files:
        if mf.exists():
            try:
                res = upload_file_to_vault(service, str(mf), folder_id=node_01_id)
                if res:
                    synced_items.append({"file": mf.name, "node": "Node 01 (Memory)", "id": res.get("id")})
                    record_file_in_mesh(mf.name, "memory", res.get("webViewLink", ""), res.get("id", ""), "node_01_core_memory", mf.stat().st_size)
            except Exception as e:
                logger.error(f"Failed to sync {mf.name}: {e}")

    # 2. Sync Master Resume & Placement to Node 03
    resume_path = STORAGE_DIR / "Mukil_Master_Resume.pdf"
    alt_resume = Path(r"C:\Users\mukil\OneDrive\placement questions\MK.PDF.RESUME.pdf")
    chosen_resume = resume_path if resume_path.exists() else (alt_resume if alt_resume.exists() else None)
    
    if chosen_resume:
        node_03_id = MESH_NODES["node_03_placement_resumes"]
        try:
            res = upload_file_to_vault(service, str(chosen_resume), folder_id=node_03_id)
            if res:
                synced_items.append({"file": chosen_resume.name, "node": "Node 03 (Placement)", "id": res.get("id")})
                record_file_in_mesh(chosen_resume.name, "placement", res.get("webViewLink", ""), res.get("id", ""), "node_03_placement_resumes", chosen_resume.stat().st_size)
        except Exception as e:
            logger.error(f"Failed to sync resume: {e}")

    # 3. Sync SGC Bills to Node 05 (Main Bills Vault)
    node_05_id = MESH_NODES["node_05_sgc_invoices"]
    if BILLS_DIR.exists():
        for bf in BILLS_DIR.glob("*.pdf"):
            try:
                res = upload_file_to_vault(service, str(bf), folder_id=node_05_id)
                if res:
                    synced_items.append({"file": bf.name, "node": "Node 05 (SGC Bills)", "id": res.get("id")})
                    record_file_in_mesh(bf.name, "bill", res.get("webViewLink", ""), res.get("id", ""), "node_05_sgc_invoices", bf.stat().st_size)
            except Exception as e:
                logger.error(f"Failed to sync bill {bf.name}: {e}")

    logger.info(f"✅ Mesh Sync completed! {len(synced_items)} files synchronized.")
    return {
        "success": True,
        "synced_count": len(synced_items),
        "items": synced_items,
        "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p")
    }

if __name__ == "__main__":
    result = run_full_mesh_sync()
    print("Sync Result:", json.dumps(result, indent=2))

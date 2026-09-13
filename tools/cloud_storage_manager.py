"""Cloud-First Zero-Local-Disk Storage Engine for JARVIS.
Streams all generated assets (invoices, resumes, notes, scraped datasets, screenshots, audio)
directly to the 250GB Distributed Google Drive Mesh (10 Dedicated Nodes x 25GB)
and automatically purges local temporary files to ensure 0 MB PC disk footprint.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DRIVE_FOLDER_ID
from tools.sync_to_drive import get_drive_service, upload_file_to_vault

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_storage_manager")

BASE_DIR = Path(__file__).resolve().parent.parent
MESH_REGISTRY_PATH = BASE_DIR / "storage" / "memory" / "distributed_drive_mesh.json"

CATEGORY_NODE_MAP = {
    "bill": "node_05_sgc_invoices",
    "invoice": "node_05_sgc_invoices",
    "resume": "node_03_placement_resumes",
    "cv": "node_03_placement_resumes",
    "placement": "node_03_placement_resumes",
    "lead": "node_04_b2b_scraped_data",
    "mill": "node_04_b2b_scraped_data",
    "b2b": "node_04_b2b_scraped_data",
    "code": "node_02_project_codebases",
    "project": "node_02_project_codebases",
    "screenshot": "node_06_visual_screenshots",
    "proof": "node_06_visual_screenshots",
    "audio": "node_07_ai_model_weights",
    "voice": "node_07_ai_model_weights",
    "learning": "node_08_learning_materials",
    "dsa": "node_08_learning_materials",
    "memory": "node_01_core_memory",
    "chat": "node_01_core_memory",
    "convo": "node_01_core_memory",
    "transcript": "node_01_core_memory",
    "backup": "node_09_cloud_backups",
    "general": "node_10_shared_overflow"
}

def load_drive_mesh() -> Dict[str, Any]:
    if MESH_REGISTRY_PATH.exists():
        try:
            with open(MESH_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load drive mesh: {e}")
    return {}

def get_node_folder_id(category: str) -> str:
    mesh = load_drive_mesh()
    subfolders = mesh.get("subfolders", {})
    nodes = mesh.get("nodes", {})
    cat_lower = category.lower().strip()
    node_key = CATEGORY_NODE_MAP.get(cat_lower, "node_01_core_memory")
    node_info = subfolders.get(node_key) or nodes.get(node_key)
    if node_info and "id" in node_info:
        return node_info["id"]
    return mesh.get("master_vault_id", DRIVE_FOLDER_ID)

def upload_and_purge(local_file_path: str, category: str = "general", delete_local: bool = True) -> Dict[str, Any]:
    """
    Uploads a generated file directly to the appropriate Google Drive Mesh Node
    and purges the local copy if delete_local=True.
    """
    if not os.path.exists(local_file_path):
        return {"success": False, "error": f"File {local_file_path} not found"}

    target_folder_id = get_node_folder_id(category)
    service = get_drive_service()
    
    if not service:
        logger.warning(f"Drive service offline, keeping local copy: {local_file_path}")
        return {"success": False, "error": "Google Drive service offline", "local_kept": True}

    try:
        drive_res = upload_file_to_vault(service, local_file_path, folder_id=target_folder_id)
        if not drive_res:
            return {"success": False, "error": "Drive upload returned None"}

        file_id = drive_res.get("id")
        web_link = drive_res.get("webViewLink")
        file_size_kb = os.path.getsize(local_file_path) / 1024

        # Zero-local-storage purge
        if delete_local:
            try:
                os.remove(local_file_path)
                logger.info(f"🗑️ Zero-Disk Policy: Purged local file '{local_file_path}' ({file_size_kb:.1f} KB freed)")
            except Exception as pe:
                logger.warning(f"Could not purge local file: {pe}")

        return {
            "success": True,
            "drive_id": file_id,
            "drive_url": web_link,
            "category": category,
            "target_node_id": target_folder_id,
            "local_purged": delete_local
        }
    except Exception as e:
        logger.error(f"Failed to upload {local_file_path} to drive: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

def cleanup_local_cache():
    """Scans and frees disk space from old local logs, screenshots, and audio caches."""
    purged_count = 0
    bytes_freed = 0
    cache_dirs = [
        BASE_DIR / "storage" / "screenshots",
        BASE_DIR / "storage" / "videos",
        BASE_DIR / "storage" / "audio"
    ]
    for d in cache_dirs:
        if d.exists():
            for f in d.glob("*.*"):
                try:
                    size = f.stat().st_size
                    f.unlink()
                    purged_count += 1
                    bytes_freed += size
                except Exception:
                    pass
    return {"purged_count": purged_count, "mb_freed": round(bytes_freed / (1024 * 1024), 2)}

if __name__ == "__main__":
    print("Mesh status:", load_drive_mesh().get("allocated_capacity"))
    print("Cleanup result:", cleanup_local_cache())

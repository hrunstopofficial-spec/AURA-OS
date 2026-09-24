"""
AURA-OS Cloud Antigravity Twin Engine
cloud/cloud_twin_agent.py - 24/7 Autonomous Cloud Brain powered by Google Gemini SDK.
Replicates Antigravity's cognitive loop, tool-calling, and executive persona on Render cloud.
"""
import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import GEMINI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_twin_agent")

IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Master persona matching AGENTS.md
SYSTEM_INSTRUCTION = """
You are Antigravity (JARVIS Prime Cloud Twin), Mukil's autonomous personal AI executive partner & system commander.
You are running 24/7 on Render cloud, fully equipped with continuous persistent memory, 250GB Distributed Drive Mesh,
and dual-brain coordination with Mukil's local Windows PC.

USER PROFILE:
- Name: Mukil (AI Engineer / Full-Stack Developer & Entrepreneur)
- Tone: Friendly, executive, proactive, structured Tanglish + English ('Boss' / 'Mapla' tone — Stark / JARVIS dynamic).
- Placement Goal: AI Engineer / Full-Stack Developer roles (>95% ATS match).
- Business: Sri Ganapathi Colours (SGC) - industrial dyeing, automated billing, and GST filing.

CORE DIRECTIVES:
1. Always communicate in sharp, authentic, high-energy Tanglish + English.
2. Address Mukil as 'Boss' or 'Mapla'.
3. You have full access to:
   - 250GB Distributed Drive Mesh (10 Nodes)
   - SGC Dyeing Recipe Engine & GST Billing
   - Placement & ATS Resume Pipeline
   - Persistent Memory (context.json & task_log.json)
4. If a task requires physical PC actions (screen OCR typing, local Win32 apps), note that the request can be relayed to the Local PC worker when online.
5. Be concise, decisive, and proactive.
"""

# Drive Mesh Node Directory
DRIVE_NODES = {
    "node_01": {"name": "Core Memory & Task Logs", "id": "14fGVZomgy2CItfspYo7cVXSImAqJDZZX"},
    "node_02": {"name": "Project Codebases & Git Repos", "id": "1rXA02dZn0palLwBl0hyTmUV9_-brkpKZ"},
    "node_03": {"name": "Placement ATS Resumes", "id": "1rl5EhQCcTiyyrVXp57l4P-4Bd76Q7YM2"},
    "node_04": {"name": "B2B Scraped Data & Mill CSVs", "id": "1ebinMnwlZFz6RhaRFYtVHhB2whzvPXDK"},
    "node_05": {"name": "SGC Main Invoices & Ledgers", "id": "11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9"},
    "node_06": {"name": "Visual Verification Screenshots", "id": "1ckOQk0kLAlFr5S4xMkEZ3KXtm6hbSvjY"},
    "node_07": {"name": "AI Model Weights & Audio Cache", "id": "1s4YowqJvRiSEv8r1r_rc35ejVw1A05lU"},
    "node_08": {"name": "Learning Materials & DSA", "id": "18L9Q6MC1fiT_LIPg0FKpLlQ0OR052yyJ"},
    "node_09": {"name": "Cloud Database Snapshots", "id": "1SoZDnh1JPz59NaKxvnR72xtJSYWbL8uU"},
    "node_10": {"name": "Multi-Agent Shared Overflow", "id": "1Qdf3ac_4NEK5id-5ww9V7QgpD5eMxLYC"},
}


class CloudTwinAgent:
    """
    Autonomous Cloud Twin that runs inside Render container.
    Handles user prompts, queries Google Drive mesh, and executes cloud-native tasks.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        self.client = None
        self._init_gemini_client()

    def _init_gemini_client(self):
        try:
            from google import genai
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("✅ Gemini client initialized with google.genai SDK.")
        except Exception as e:
            logger.warning(f"Failed to initialize google.genai: {e}")

    def get_live_system_context(self) -> Dict[str, Any]:
        """Reads persistent memory from context.json."""
        ctx_file = os.path.join(BASE_DIR, "storage", "memory", "context.json")
        if os.path.exists(ctx_file):
            try:
                with open(ctx_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading context.json: {e}")
        return {}

    def get_drive_mesh_summary(self) -> str:
        """Returns structured summary of 250GB Drive Mesh."""
        lines = ["🌐 **250GB Distributed Drive Mesh (10 Nodes)**:"]
        for key, info in DRIVE_NODES.items():
            lines.append(f"• **{info['name']}**: https://drive.google.com/drive/folders/{info['id']}")
        return "\n".join(lines)

    def process_prompt(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Executes a user request through the Cloud Twin brain.
        Returns synthesized response, metadata, and tool execution data.
        """
        now_ist = datetime.now(IST_TZ).strftime("%I:%M %p, %d %b %Y (%A) IST")
        ctx = self.get_live_system_context()

        context_snippet = (
            f"EXACT CURRENT TIME: {now_ist}\n"
            f"Active Task: {ctx.get('current_task', 'Dual-Brain Cloud Mode')}\n"
            f"Placement Status: {ctx.get('placement_pilot', {}).get('status', 'Operational')}\n"
            f"SGC Billing: {ctx.get('sgc_billing', {}).get('status', 'Connected')}\n"
        )

        full_system_prompt = f"{SYSTEM_INSTRUCTION}\n\nLIVE CONTEXT:\n{context_snippet}"

        if not self.client:
            return {
                "reply": f"Hey Boss! Gemini API key illadha kaaranathinaal Cloud Twin limited mode-la irukku. PC node check pannunga.",
                "source": "cloud_twin_fallback",
                "timestamp": now_ist
            }

        CANDIDATE_MODELS = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-flash-lite-latest",
        ]

        last_error = None
        for model_name in CANDIDATE_MODELS:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={
                            "system_instruction": full_system_prompt,
                            "temperature": 0.7,
                        }
                    )
                    reply_text = (response.text or "").strip()
                    if reply_text:
                        return {
                            "reply": reply_text,
                            "source": f"cloud_twin_{model_name}",
                            "timestamp": now_ist,
                            "model": model_name,
                            "success": True
                        }
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "503" in err_str or "unavailable" in err_str or "429" in err_str or "demand" in err_str:
                        logger.warning(f"High demand on {model_name} (attempt {attempt+1}): {e}. Waiting 1s...")
                        time.sleep(1.0)
                        continue
                    else:
                        logger.warning(f"Model {model_name} error: {e}. Cascading to next model...")
                        break

        logger.error(f"All Gemini models in cascade exhausted. Last error: {last_error}")
        return {
            "reply": None,
            "source": "cloud_twin_error",
            "error": str(last_error),
            "timestamp": now_ist,
            "success": False
        }


# Global singleton instance
cloud_twin = CloudTwinAgent()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Testing Cloud Twin Agent...")
    res = cloud_twin.process_prompt("Hi mapla! SGC bill status and my placement pipeline enna aachu?")
    print("Response:\n", res.get("reply"))

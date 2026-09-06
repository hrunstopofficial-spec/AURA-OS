import os
import json
from datetime import datetime
from typing import Any, Optional, Dict, List

MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage', 'memory')
CONTEXT_FILE = os.path.join(MEMORY_DIR, 'context.json')
PROFILE_FILE = os.path.join(MEMORY_DIR, 'user_profile.json')
TASK_LOG_FILE = os.path.join(MEMORY_DIR, 'task_log.json')
CUSTOM_FACTS_FILE = os.path.join(MEMORY_DIR, 'custom_facts.json')
PROJECTS_MEMORY_FILE = os.path.join(MEMORY_DIR, 'projects_memory.json')
SERVER_AGENT_MEMORY_FILE = os.path.join(MEMORY_DIR, 'server_agent_memory.json')

class MemoryManager:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)

    def get_context(self) -> dict:
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_profile(self) -> dict:
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def update_context(self, updates: dict):
        current = self.get_context()
        current.update(updates)
        current['last_updated'] = datetime.now().isoformat()
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2)

    def log_task(self, event: str, description: str, metadata: dict = None):
        logs = []
        if os.path.exists(TASK_LOG_FILE):
            try:
                with open(TASK_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'description': description,
            'metadata': metadata or {}
        }
        logs.append(entry)
        with open(TASK_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)

    def append_conversation(self, sender: str, text: str):
        convo_file = os.path.join(MEMORY_DIR, 'conversations_history.json')
        convos = []
        if os.path.exists(convo_file):
            try:
                with open(convo_file, 'r', encoding='utf-8') as f:
                    convos = json.load(f)
            except Exception:
                convos = []
        convos.append({
            'sender': sender,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })
        # Keep last 50
        if len(convos) > 50:
            convos = convos[-50:]
        with open(convo_file, 'w', encoding='utf-8') as f:
            json.dump(convos, f, indent=2)

    def get_recent_conversations(self, limit: int = 6) -> list:
        convo_file = os.path.join(MEMORY_DIR, 'conversations_history.json')
        if os.path.exists(convo_file):
            try:
                with open(convo_file, 'r', encoding='utf-8') as f:
                    convos = json.load(f)
                    return convos[-limit:]
            except Exception:
                pass
        return []

    def save_fact(self, key: str, value: Any, category: str = "general") -> dict:
        facts = {}
        if os.path.exists(CUSTOM_FACTS_FILE):
            try:
                with open(CUSTOM_FACTS_FILE, 'r', encoding='utf-8') as f:
                    facts = json.load(f)
            except Exception:
                facts = {}
        facts[key] = {
            "value": value,
            "category": category,
            "updated_at": datetime.now().isoformat()
        }
        with open(CUSTOM_FACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(facts, f, indent=2, ensure_ascii=False)
        return facts[key]

    def get_facts(self, category: str = None) -> dict:
        if os.path.exists(CUSTOM_FACTS_FILE):
            try:
                with open(CUSTOM_FACTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if category:
                        return {k: v for k, v in data.items() if v.get('category') == category}
                    return data
            except Exception:
                pass
        return {}

    def allocate_project_memory(self, project_name: str, tech_stack: list = None, details: dict = None) -> dict:
        projects = {}
        if os.path.exists(PROJECTS_MEMORY_FILE):
            try:
                with open(PROJECTS_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
            except Exception:
                projects = {}
        entry = {
            "project_name": project_name,
            "tech_stack": tech_stack or [],
            "status": "ACTIVE_ALLOCATED",
            "allocated_drive_node": "Node 02 (Project Codebases & Git Repos: 1rXA02dZn0palLwBl0hyTmUV9_-brkpKZ)",
            "allocated_at": datetime.now().isoformat(),
            "details": details or {}
        }
        projects[project_name] = entry
        with open(PROJECTS_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        return entry

    def get_projects_memory(self) -> dict:
        if os.path.exists(PROJECTS_MEMORY_FILE):
            try:
                with open(PROJECTS_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_server_agent_memory(self) -> dict:
        if os.path.exists(SERVER_AGENT_MEMORY_FILE):
            try:
                with open(SERVER_AGENT_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_all_memory_allocations(self) -> dict:
        facts = self.get_facts()
        projects = self.get_projects_memory()
        server_mem = self.get_server_agent_memory()
        return {
            "partition_1_core_profile": "storage/memory/user_profile.json (Active Profile, Karur, VSB, Skills)",
            "partition_2_system_context": "storage/memory/context.json (Active Phase, Drive Vaults, Endpoints)",
            "partition_3_task_ledger": "storage/memory/task_log.json (Living Task Ledger, Audit Trail)",
            "partition_4_conversations": "storage/memory/conversations_history.json (Rolling cross-device history)",
            "partition_5_custom_facts": f"storage/memory/custom_facts.json ({len(facts)} active custom user memories)",
            "partition_6_projects_memory": f"storage/memory/projects_memory.json ({len(projects)} active projects allocated)",
            "partition_7_server_agent": f"storage/memory/server_agent_memory.json (24/7 Cloud Production Engine: {server_mem.get('cloud_endpoints', {}).get('render_production', 'https://aura-os-n6n3.onrender.com')}, 75GB Mesh across Nodes 01, 09, 10)",
            "partition_8_sgc_billing": "AppData/Roaming/sgc-billing/sgc-billing-data.json (Live SGC Yarn Dyeing Ledger)",
            "partition_9_drive_mesh": "250GB Distributed Google Drive Mesh (10 Dedicated Cloud Nodes)",
            "total_local_partitions": 8,
            "cloud_mesh_nodes": 10,
            "status": "100% OPERATIONAL & PERSISTENT"
        }

    def get_system_prompt_context(self) -> str:
        ctx = self.get_context()
        prof = self.get_profile()
        user_name = prof.get('personal_details', {}).get('name', 'Mukilarasu S')
        phone = prof.get('personal_details', {}).get('phone', '9080030538')
        location = prof.get('personal_details', {}).get('location', 'Karur, Tamil Nadu')
        college = prof.get('personal_details', {}).get('college', 'VSB Engineering College, Karur')
        phase = ctx.get('active_phase', 'AURA-OS Autonomous Swarm Active')
        drive_url = ctx.get('drive_vault', {}).get('backup_vault_id', '1nGZG5-eIcxmkgQxBtZ7tjGTUoWWNY4m1')
        curr_task = ctx.get('current_task', 'Autonomous Partner Active')
        facts = self.get_facts()
        facts_summary = "\n".join([f"  - {k}: {v.get('value')}" for k, v in list(facts.items())[:10]]) if facts else "  - None yet."
        projects = self.get_projects_memory()
        projects_summary = ", ".join(list(projects.keys())[:5]) if projects else "None"

        return (
            "=== PERSISTENT MEMORY & USER CORE CONTEXT ===\n"
            f"• User: {user_name} (Phone: {phone}, Location: {location}, College: {college})\n"
            "• Family Business: Sri Ganapathi Colours (SGC) - Yarn Dyeing & Textile Sizing located in Karur, Tamil Nadu.\n"
            "• SGC Invoicing & Bills: Handled via 'sgc-billing' desktop app. Active Bills Drive Vault ID: 11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9. Total 6 bills recorded (Latest is Bill #6: GAIA SUSTAINABLE SOLUTION, ₹956).\n"
            "• When Mukil mentions 'business bills', 'bills', 'kadai bills', or 'invoices', he is ALWAYS referring to Sri Ganapathi Colours (SGC).\n"
            "• COLLOQUIAL TANGLISH INSTRUCTION: 'Onu ella' or 'Onnum illa' means 'Nothing much / never mind / no worries' in Tanglish. It is NOT a company name!\n"
            "• PERMANENT MEMORY DIRECTIVE: You have FULL MULTI-DEVICE PERSISTENT MEMORY (PC, Phone/Telegram, and 250GB Google Drive mesh). NEVER tell Mukil that you don't have permanent memory or that memory doesn't carry over! You remember everything Mukil says.\n"
            f"• Dynamically Stored User Facts & Knowledge:\n{facts_summary}\n"
            f"• Allocated Project Memory Workspaces: {projects_summary}\n"
            f"• Active Phase: {phase}\n"
            f"• 250GB Mesh & Master Vault: {drive_url}\n"
            f"• Current Focus: {curr_task}\n"
            "============================================="
        )

if __name__ == '__main__':
    mem = MemoryManager()
    print(mem.get_system_prompt_context())

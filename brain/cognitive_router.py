"""Cognitive Dual-Brain Front-Door Router for AURA-OS / JARVIS.
Dispatches incoming inputs into one of 4 specialized cognitive tracks:
  1. FAST_CONVERSATION: Sub-500ms streaming LLM (No tools, pure Tanglish brotherly banter, tech doubts)
  2. STATUS_OR_MEMORY_QUERY: Instant lookup in Living Task Ledger, Drive RAG, or Context (<1s)
  3. DEVICE_PRESENTATION: "Open panni kaatu" / "Show me" -> Checks is_pc_online() for screen vs mobile
  4. AUTONOMOUS_HEAVY_TASK: Triggers Multi-Agent Swarm + Dynamic CodeAct Runner + Verification
"""
import re
import json
import logging
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from groq import Groq

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import GROQ_API_KEY

logger = logging.getLogger("CognitiveRouter")


class CognitiveRoute(BaseModel):
    track: Literal[
        "FAST_CONVERSATION",       # ⚡ System 1: Greetings, chit-chat, tech explanations, Java/Python doubts (<0.5s)
        "STATUS_OR_MEMORY_QUERY",  # 🔍 System 2: "Andha task enna aachu?", "Show today's log", "SGC bill amount"
        "DEVICE_PRESENTATION",     # 📡 "Open panni kaatu", "Show me on screen", "Display proof"
        "AUTONOMOUS_HEAVY_TASK"    # 🛠️ System 3: Scraping, file creation, job apply, code execution
    ]
    target_swarm_agent: Optional[str] = Field(
        default=None,
        description="Target agent: 'PlacementHunter', 'SGCExecutive', 'CodeMaster', 'WebScout', 'PCPilot', 'MemoryVault'"
    )
    confidence: float = Field(default=0.95, description="Confidence score 0.0 - 1.0")
    goal_summary: str = Field(description="Short distilled objective of what user expects")
    requires_pc: bool = Field(default=False, description="True if requires physical Windows PC execution")


class CognitiveRouter:
    """
    Sub-50ms Front-Door Cognitive Router ensuring zero latency for chat,
    and structured delegation for heavy tasks.
    """

    def __init__(self, groq_api_key: Optional[str] = None):
        self.client = Groq(api_key=groq_api_key or GROQ_API_KEY)
        self.fast_model = "openai/gpt-oss-20b"

    def route(self, user_text: str) -> CognitiveRoute:
        text = (user_text or "").strip()
        lower_text = text.lower()

        # ── TRACK 3: FAST-PATH DEVICE PRESENTATION & PHYSICAL PC ACTION ────────
        presentation_patterns = [
            r"(open.*panni.*kaatu|open.*pannu.*screen|screen.*la.*open|screen.*la.*kaatu)",
            r"(show.*on.*screen|display.*on.*pc|open.*on.*pc|open.*in.*browser|open.*on.*lap|open.*lap)",
            r"(open.*this.*file|open.*excel|open.*invoice|show.*proof)",
            r"(open.*notepad|open.*chrome|open.*browser|open.*youtube|open.*whatsapp|open.*calc|open.*code)",
            r"(play.*youtube|play.*song|play.*video|play.*pannu|lap.*la.*play|play.*vj.*siddhu|vj.*siddhu)",
            r"(close.*notepad|close.*app|close.*window|take.*screenshot|screen.*shot)",
            r"(battery.*status|battery.*evalo|charge.*evalo|battery.*percentage|battery.*level)",
            r"(lock.*pc|lock.*laptop|lock.*workstation|sleep.*pc)",
            r"(volume.*yethu|volume.*kora|sound.*yethu|sound.*kora|mute|unmute|set.*volume)",
            r"(brightness.*yethu|brightness.*kora|set.*brightness)"
        ]
        for pat in presentation_patterns:
            if re.search(pat, lower_text):
                return CognitiveRoute(
                    track="DEVICE_PRESENTATION",
                    target_swarm_agent="PCPilot",
                    confidence=0.98,
                    goal_summary="User requested to display/open file, application, or media on physical PC screen",
                    requires_pc=True
                )

        # ── TRACK 2: FAST-PATH STATUS / MEMORY QUERY ────────────────────────
        status_patterns = [
            r"(task.*enna.*aachu|status.*enna|enna.*nadandhadhu|update.*sollu)",
            r"(what.*is.*the.*status|how.*is.*the.*task|did.*you.*finish)",
            r"(sgc|bill|invoice|overdue|balance|ledger|party)",
            r"(list.*files|changed.*files|show.*logs?|task.*ledger)",
            r"(memory.*eruka|memory.*irukka|store.*panni|remember|unaku.*memory|save.*data|store.*pannu|allocate|allocation|note.*pannu|note.*panniko|save.*pannu)",
            r"(server.*agent|cloud.*server|server.*status|render.*status|cloud.*memory|server.*memory|server.*health|server.*allocate)"
        ]
        for pat in status_patterns:
            if re.search(pat, lower_text):
                if any(k in lower_text for k in ["server agent", "cloud server", "render", "server health", "server status", "server memory", "server ku"]):
                    agent = "ServerAgent"
                elif any(k in lower_text for k in ["sgc", "bill", "invoice", "overdue", "balance", "ledger", "msk", "sowbhagiya", "laxmi", "gaia"]):
                    agent = "SGCExecutive"
                else:
                    agent = "MemoryVault"
                return CognitiveRoute(
                    track="STATUS_OR_MEMORY_QUERY",
                    target_swarm_agent=agent,
                    confidence=0.96,
                    goal_summary="User is querying status of a previous task, business bills, server agent, or persistent memory",
                    requires_pc=False
                )

        # ── TRACK 1: FAST-PATH CONVERSATIONAL BANTER / DOUBTS ────────────────
        convo_greetings = [
            r"^(hi|hello|vanakkam|hey|mapla|maapla|machi|bro|boss|yo)\b",
            r"(epdi.*irukka|how.*are.*you|what'?s.*up|enna.*panra|saukyama)",
            r"^(thanks|nandri|super|mass|semma|ok|done|seri|got it)\b",
            r"(what.*is|explain|difference.*between|teach.*me|interview.*doubt)",
            r"(oops|polymorphism|hashset|treeset|sliding.*window|prefix.*sum|dsa)"
        ]
        is_greeting_or_study = any(re.search(pat, lower_text) for pat in convo_greetings)
        has_heavy_keywords = any(k in lower_text for k in [
            "scrape", "create", "build", "apply", "run", "download", "generate", "install",
            "podu", "eduthu", "anupu", "excel", "drive", "write", "code", "file"
        ])

        if is_greeting_or_study and not has_heavy_keywords:
            return CognitiveRoute(
                track="FAST_CONVERSATION",
                target_swarm_agent=None,
                confidence=0.99,
                goal_summary="Casual conversation, greeting, or technical explanation",
                requires_pc=False
            )

        # ── TRACK 4: OBVIOUS HEAVY AUTONOMOUS TASKS ──────────────────────────
        if any(k in lower_text for k in [
            "antigravity", "build project", "create project", "scaffold", "refactor",
            "run command", "terminal command", "fix bug", "new project", "build app",
            "write code", "codebase", "make project", "develop app"
        ]):
            return CognitiveRoute(
                track="AUTONOMOUS_HEAVY_TASK",
                target_swarm_agent="Antigravity",
                confidence=0.98,
                goal_summary="Autonomous software engineering, project scaffolding, terminal execution or code refactoring via Antigravity Agent",
                requires_pc=False
            )

        if any(k in lower_text for k in ["scrape", "crawl", "spinning.*mills?", "b2b", "leads?", "export"]):
            return CognitiveRoute(
                track="AUTONOMOUS_HEAVY_TASK",
                target_swarm_agent="WebScout",
                confidence=0.95,
                goal_summary="B2B web scraping and data extraction",
                requires_pc=False
            )

        if any(k in lower_text for k in ["resume", "apply", "ats", "zoho", "indeed", "naukri", "placement"]):
            return CognitiveRoute(
                track="AUTONOMOUS_HEAVY_TASK",
                target_swarm_agent="PlacementHunter",
                confidence=0.95,
                goal_summary="Placement application or ATS resume tailoring",
                requires_pc=False
            )

        # ── LLM SEMANTIC FALLBACK (For nuanced or hybrid inputs) ─────────────
        try:
            prompt = (
                "Classify the following user message into exactly ONE track:\n"
                "1. 'FAST_CONVERSATION': Chit-chat, greetings, casual doubts (Needs direct text reply only)\n"
                "2. 'STATUS_OR_MEMORY_QUERY': Asking what happened with a task, checking memory, or bills\n"
                "3. 'DEVICE_PRESENTATION': Asking to open/show something on screen or in an app\n"
                "4. 'AUTONOMOUS_HEAVY_TASK': Asking to create files, scrape websites, write code, or execute workflows\n\n"
                f"User Message: \"{text}\"\n\n"
                "Return valid JSON strictly matching:\n"
                "{\"track\": \"FAST_CONVERSATION\"|\"STATUS_OR_MEMORY_QUERY\"|\"DEVICE_PRESENTATION\"|\"AUTONOMOUS_HEAVY_TASK\", "
                "\"target_swarm_agent\": \"Antigravity\"|\"WebScout\"|\"PlacementHunter\"|\"SGCExecutive\"|\"CodeMaster\"|\"PCPilot\"|\"MemoryVault\"|null, "
                "\"confidence\": 0.95, \"goal_summary\": \"...\", \"requires_pc\": true|false}"
            )
            resp = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a classifier that strictly returns JSON matching the required schema."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            raw_json = json.loads(resp.choices[0].message.content or "{}")
            return CognitiveRoute(**raw_json)
        except Exception as e:
            logger.warning(f"Semantic routing fallback error: {e}. Defaulting to FAST_CONVERSATION.")
            return CognitiveRoute(
                track="FAST_CONVERSATION",
                target_swarm_agent=None,
                confidence=0.70,
                goal_summary=text[:50],
                requires_pc=False
            )

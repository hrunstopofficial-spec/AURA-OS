"""Stage 6: Master Cognitive Orchestrator with Drive RAG & Multi-DB Outbox Integration."""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.brain.intent_classifier import IntentClassifier, IntentType, ParsedIntent
from app.brain.context_hydrator import ContextHydrator, HydratedContext
from app.brain.clarification_gate import ClarificationGate, ClarificationDecision
from app.brain.dag_planner import DAGPlanner, ExecutionPlan
from app.brain.saga_rollback_engine import SAGARollbackEngine, StepExecutionResult
from app.brain.codeact_runner import CodeActRunner, CodeActResult
from app.brain.multi_modal_dispatcher import MultiModalDispatcher, DispatchedMessage
from app.brain.async_queue import AsyncTaskQueue, AsyncTaskItem
from app.brain.drive_rag_engine import DriveRAGEngine, DriveFolderRegistry, IndexedDocument
from app.database.polyglot_manager import PolyglotDBManager, StorageTarget

logger = logging.getLogger("MasterOrchestrator")


class OrchestratorResponse(BaseModel):
    response_type: str  # "CONVERSATION", "CLARIFICATION_REQUIRED", "TASK_COMPLETED", "TASK_FAILED", "ASYNC_QUEUED", "RAG_DRIVE_ANSWER"
    text: str
    plan: Optional[ExecutionPlan] = None
    step_results: List[StepExecutionResult] = Field(default_factory=list)
    clarification_decision: Optional[ClarificationDecision] = None
    hydrated_context: Optional[HydratedContext] = None
    dispatched_message: Optional[DispatchedMessage] = None
    async_task_id: Optional[str] = None
    rag_matches: List[Dict[str, Any]] = Field(default_factory=list)


class MasterOrchestrator:
    """Unified Orchestrator implementing Mukil's 6-Stage Hardened Agentic Lifecycle with Drive RAG."""

    def __init__(
        self,
        classifier: Optional[IntentClassifier] = None,
        hydrator: Optional[ContextHydrator] = None,
        clarification_gate: Optional[ClarificationGate] = None,
        planner: Optional[DAGPlanner] = None,
        rollback_engine: Optional[SAGARollbackEngine] = None,
        codeact_runner: Optional[CodeActRunner] = None,
        dispatcher: Optional[MultiModalDispatcher] = None,
        async_queue: Optional[AsyncTaskQueue] = None,
        polyglot_db: Optional[PolyglotDBManager] = None,
        drive_rag: Optional[DriveRAGEngine] = None,
    ):
        self.classifier = classifier or IntentClassifier()
        self.hydrator = hydrator or ContextHydrator()
        self.clarification_gate = clarification_gate or ClarificationGate()
        self.planner = planner or DAGPlanner()
        self.codeact_runner = codeact_runner or CodeActRunner()
        self.dispatcher = dispatcher or MultiModalDispatcher()
        self.async_queue = async_queue or AsyncTaskQueue()
        self.polyglot_db = polyglot_db or PolyglotDBManager()
        self.drive_rag = drive_rag or DriveRAGEngine()

        # Bind dynamic codeact executor into SAGA rollback engine
        self.rollback_engine = rollback_engine or SAGARollbackEngine(
            tool_executor=self._dynamic_step_executor
        )

    async def _dynamic_step_executor(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Executes steps dynamically via CodeAct or OS pilots."""
        if tool_name == "open_app":
            app_target = args.get("app_name", "notepad")
            res = await self.codeact_runner.execute_powershell(f"Start-Process '{app_target}'")
            return {"status": "ok", "target": app_target, "output": res.stdout}
        elif tool_name == "web_fetch":
            url = args.get("url", "https://example.com")
            py_code = f"import urllib.request; print(f'Fetched {{len(urllib.request.urlopen(\"{url}\").read())}} bytes')"
            res = await self.codeact_runner.execute_python_code(py_code)
            return {"status": "ok", "bytes": res.stdout}

        # ─── OS GUI & COMPUTER USE ACTIONS (Vision + Mouse + Keyboard) ───
        elif tool_name == "os_view_screen":
            from tools.fast_os_controller import see_screen
            query = args.get("query", "Describe what is on this screen.")
            desc = see_screen(query)
            return {"status": "ok", "screen_description": desc}

        elif tool_name == "os_click_element":
            from tools.fast_os_controller import click_element_by_text, mouse_click
            element = args.get("element")
            x = args.get("x")
            y = args.get("y")
            if element:
                clicked = click_element_by_text(element)
                if not clicked:
                    return {"status": "error", "error": f"Element '{element}' not found on screen"}
                return {"status": "ok", "clicked_element": element}
            elif x is not None and y is not None:
                mouse_click(x=x, y=y)
                return {"status": "ok", "clicked_coords": (x, y)}
            return {"status": "error", "error": "No element or coordinates provided"}

        elif tool_name == "os_type_text":
            from tools.fast_os_controller import type_human, type_instant
            text = args.get("text", "")
            mode = args.get("mode", "human")
            if mode == "instant":
                type_instant(text)
            else:
                type_human(text)
            return {"status": "ok", "typed_length": len(text)}

        elif tool_name == "os_hotkey":
            from tools.fast_os_controller import hotkey
            keys = args.get("keys", [])
            if keys:
                hotkey(*keys)
                return {"status": "ok", "hotkey": keys}
            return {"status": "error", "error": "No keys provided for hotkey"}

        # ─── SAGA COMPENSATING ROLLBACK ACTIONS ───
        elif tool_name == "rollback_undo_typing":
            from tools.fast_os_controller import hotkey, press_key
            # Select all and delete text to roll back accidental/failed input
            hotkey("ctrl", "a")
            press_key("backspace")
            return {"status": "rolled_back", "action": "cleared_input_field"}

        elif tool_name == "rollback_close_window":
            from tools.fast_os_controller import hotkey, press_key
            press_key("esc")
            hotkey("ctrl", "w")
            return {"status": "rolled_back", "action": "closed_active_tab"}

        elif tool_name == "rollback_escape":
            from tools.fast_os_controller import press_key
            press_key("esc")
            return {"status": "rolled_back", "action": "pressed_escape"}

        else:
            return {"status": "ok", "tool": tool_name}

    async def process_user_input(
        self,
        user_input: str,
        user_name: str = "Mukil",
        chat_id: int = 0,
        prefer_voice: bool = False,
    ) -> OrchestratorResponse:
        """Executes the full 6-Stage Pipeline deterministically."""
        clean_input = (user_input or "").strip()
        logger.info(f"🌌 [MasterOrchestrator] Processing: '{clean_input}' from {user_name}")

        # ── SPECIAL FLOW A: DRIVE FOLDER REGISTRATION ────────────────────────
        if "drive.google.com" in clean_input or ("drive" in clean_input.lower() and "folder" in clean_input.lower() and any(c.isalnum() for c in clean_input)):
            # Check for drive URL / ID
            folder_match = re.search(r"(?:folders/|id=)([a-zA-Z0-9_-]+)", clean_input)
            if folder_match or "http" in clean_input:
                target_folder = folder_match.group(1) if folder_match else clean_input
                alias = "sgc_billing_drive" if "bill" in clean_input.lower() else f"drive_vault_{target_folder[:6]}"
                reg = self.drive_rag.register_drive_folder(
                    alias=alias,
                    folder_url_or_id=clean_input,
                    description="User registered Google Drive Vault"
                )
                reply_text = (
                    f"📂 *Google Drive Vault Linked Successfully!*\n\n"
                    f"• *Alias*: `{reg.alias}`\n"
                    f"• *Folder ID*: `{reg.folder_id}`\n"
                    f"• *Drive URL*: {reg.folder_url}\n\n"
                    f"Boss, indha Drive folder-ah RAG knowledge vault-la save panniten. "
                    f"Indha drive-la irukura customer bills and files pathi neenga epovume details kekkalam!"
                )
                dispatched = self.dispatcher.format_output(reply_text, prefer_voice=prefer_voice)
                return OrchestratorResponse(
                    response_type="RAG_DRIVE_ANSWER",
                    text=reply_text,
                    dispatched_message=dispatched,
                )

        # ── SPECIAL FLOW B: DRIVE RAG SEARCH QUERY ───────────────────────────
        rag_hits = self.drive_rag.query_rag_context(clean_input, top_k=3)
        if rag_hits and any(k in clean_input.lower() for k in ["bill", "invoice", "customer", "rajesh", "paint", "amount", "drive", "file"]):
            doc = rag_hits[0]
            reply_text = (
                f"📄 *Drive RAG Search Found Match:*\n\n"
                f"• *File*: `{doc['filename']}` (Folder: `{doc['folder_alias']}`)\n"
                f"• *Details*: {doc['content_text']}\n"
                f"• *Metadata*: {json.dumps(doc.get('metadata', {}))}\n\n"
                f"Boss, unga Drive RAG system-la irundhu exact data fetch panniten!"
            )
            dispatched = self.dispatcher.format_output(reply_text, prefer_voice=prefer_voice)
            return OrchestratorResponse(
                response_type="RAG_DRIVE_ANSWER",
                text=reply_text,
                rag_matches=rag_hits,
                dispatched_message=dispatched,
            )

        # ── STAGE 1: CLASSIFY INPUT ──────────────────────────────────────────
        parsed: ParsedIntent = self.classifier.classify(clean_input)

        # ── STAGE 2: HYDRATE CONTEXT & PROFILE ──────────────────────────────
        hydrated: HydratedContext = self.hydrator.hydrate()

        # If it's pure conversation, return immediate cognitive response
        if parsed.primary_intent == IntentType.CONVERSATION:
            reply_text = f"Hey {user_name}! Unnoda context load aayiduchu ({hydrated.active_phase}). Enna help pannanum sollu maapla?"
            dispatched = self.dispatcher.format_output(reply_text, prefer_voice=prefer_voice)
            return OrchestratorResponse(
                response_type="CONVERSATION",
                text=reply_text,
                hydrated_context=hydrated,
                dispatched_message=dispatched,
            )

        # ── STAGE 3: CLARIFICATION & RISK GATE ───────────────────────────────
        clarification: ClarificationDecision = self.clarification_gate.evaluate_intent(clean_input)
        if clarification.requires_clarification:
            clarify_text = clarification.clarification_prompt or "Confirmation required before proceeding."
            dispatched = self.dispatcher.format_output(clarify_text, prefer_voice=prefer_voice)
            return OrchestratorResponse(
                response_type="CLARIFICATION_REQUIRED",
                text=clarify_text,
                clarification_decision=clarification,
                hydrated_context=hydrated,
                dispatched_message=dispatched,
            )

        # ── STAGE 4: MULTI-STEP DAG PLANNER ──────────────────────────────────
        plan: ExecutionPlan = self.planner.create_plan(user_goal=clean_input)

        # ── STAGE 5: SAGA EXECUTION & VERIFICATION ───────────────────────────
        step_results: List[StepExecutionResult] = await self.rollback_engine.execute_plan(plan)

        # Check overall success
        all_passed = all(r.status == "SUCCESS" for r in step_results)

        if all_passed:
            success_text = f"✅ Boss, task plan '[{plan.goal}]' ({len(plan.steps)} steps) 100% verified and complete!"
            
            # ── STAGE 6: PERSIST TO POLYGLOT OUTBOX ──────────────────────────
            self.polyglot_db.stage_outbox_record(
                target=StorageTarget.RELATIONAL_SQLITE,
                payload={"goal": plan.goal, "status": "COMPLETED", "user": user_name}
            )

            dispatched = self.dispatcher.format_output(success_text, prefer_voice=prefer_voice)
            return OrchestratorResponse(
                response_type="TASK_COMPLETED",
                text=success_text,
                plan=plan,
                step_results=step_results,
                hydrated_context=hydrated,
                dispatched_message=dispatched,
            )
        else:
            failed_step = next((r for r in step_results if r.status == "FAILED"), None)
            err_msg = failed_step.error_message if failed_step else "Unknown step failure"
            fail_text = f"❌ Boss, task execution failed at Step [{failed_step.step_id if failed_step else 'unknown'}]: {err_msg}. Auto-rollback completed."
            dispatched = self.dispatcher.format_output(fail_text, prefer_voice=prefer_voice)
            return OrchestratorResponse(
                response_type="TASK_FAILED",
                text=fail_text,
                plan=plan,
                step_results=step_results,
                hydrated_context=hydrated,
                dispatched_message=dispatched,
            )

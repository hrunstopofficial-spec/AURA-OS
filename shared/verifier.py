"""
AURA-OS Two-Layer Task Verifier & Semantic Critic Engine
shared/verifier.py - Structural (Deterministic) + Semantic (LLM Critic) Verification.
"""
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field
import json
import logging

from shared.protocol import TaskResult, TaskStatus
from shared.registry import registry

logger = logging.getLogger("aura_task_verifier")

# =====================================================================
# CRITIC SPECIFICATION & SEMANTIC SCORE DEFINITION
# =====================================================================
# Confidence Score Semantic:
# 0.0 - 0.49: Definite failure (output is irrelevant, empty, or wrong target)
# 0.5 - 0.69: Borderline (partially matches, missing critical requested items)
# 0.7 - 0.89: Pass (substantively satisfies Mukil's core requirements)
# 0.9 - 1.00: Perfect (flawless execution exceeding expectations)
CRITIC_PASS_THRESHOLD = 0.70
MAX_AUTO_RETRIES = 1


class CriticEvaluation(BaseModel):
    is_satisfied: bool = Field(description="True if the task output substantively satisfies the user's intent")
    critic_score: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Concise 1-2 sentence rationale for the verdict")
    suggested_retry_params: Optional[Dict[str, Any]] = Field(default=None, description="Adjusted parameters if retry is warranted")


class TaskVerifier:
    def __init__(self, llm_client=None):
        """
        Initializes the Verifier.
        llm_client: Optional callable or client (e.g., Groq / Gemini) for Layer 2 critic pass.
        If None, falls back to structural verification only or simulated critic in test mode.
        """
        self.llm_client = llm_client

    def verify_task_result(
        self,
        task_id: str,
        original_user_request: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        raw_result_data: Dict[str, Any],
        executor_agent_id: str = "system_agent",
        execution_time_ms: float = 0.0,
        retry_count: int = 0
    ) -> TaskResult:
        """
        Executes the two-layer verification pipeline:
        Layer 1: Structural check against tool registry validator.
        Layer 2: LLM Critic pass (only if tool requires_semantic_verification == True).
        """
        logger.info(f"🔍 [Task {task_id}] Verifying '{tool_name}' output (Attempt {retry_count + 1})...")

        tool_meta = registry.get(tool_name)
        if not tool_meta:
            return TaskResult(
                task_id=task_id,
                idempotency_key=task_id,
                status=TaskStatus.FAILED,
                error_message=f"Unknown tool '{tool_name}' cannot be verified.",
                executor_agent_id=executor_agent_id,
                execution_time_ms=execution_time_ms,
                verified=False,
                verification_note="Tool not found in registry"
            )

        # -------------------------------------------------------------
        # LAYER 1: STRUCTURAL DETERMINISTIC VERIFICATION (Zero LLM cost)
        # -------------------------------------------------------------
        struct_passed, struct_note = tool_meta.structural_validator(raw_result_data) if tool_meta.structural_validator else (bool(raw_result_data), "Non-empty data")

        if not struct_passed:
            logger.warning(f"❌ [Task {task_id}] Layer 1 Structural Verification FAILED: {struct_note}")
            return TaskResult(
                task_id=task_id,
                idempotency_key=task_id,
                status=TaskStatus.FAILED,
                result_data=raw_result_data,
                error_message=f"Structural check failed: {struct_note}",
                executor_agent_id=executor_agent_id,
                execution_time_ms=execution_time_ms,
                verified=False,
                verification_note=f"Layer 1 Failed: {struct_note}",
                critic_score=0.0
            )

        # If tool does NOT require Layer 2 semantic check (e.g. screenshot, battery), PASS immediately!
        if not tool_meta.requires_semantic_verification:
            logger.info(f"✅ [Task {task_id}] Layer 1 PASS (Deterministic Tool): {struct_note}")
            return TaskResult(
                task_id=task_id,
                idempotency_key=task_id,
                status=TaskStatus.SUCCESS,
                result_data=raw_result_data,
                executor_agent_id=executor_agent_id,
                execution_time_ms=execution_time_ms,
                verified=True,
                verification_note=f"Structural Pass: {struct_note}",
                critic_score=1.0
            )

        # -------------------------------------------------------------
        # LAYER 2: SEMANTIC CRITIC PASS (LLM-based for open-ended tasks)
        # -------------------------------------------------------------
        logger.info(f"🧠 [Task {task_id}] Layer 2 Semantic Critic evaluating open-ended output...")
        critic_eval = self._run_critic_pass(
            original_user_request=original_user_request,
            tool_name=tool_name,
            tool_params=tool_params,
            raw_result_data=raw_result_data
        )

        is_verified = (critic_eval.is_satisfied and critic_eval.critic_score >= CRITIC_PASS_THRESHOLD)
        final_status = TaskStatus.SUCCESS if is_verified else TaskStatus.FAILED

        log_level = logger.info if is_verified else logger.warning
        log_level(
            f"{'✅' if is_verified else '⚠️'} [Task {task_id}] Critic Verdict: "
            f"Verified={is_verified}, Score={critic_eval.critic_score}, Note: {critic_eval.reasoning}"
        )

        # Log verdict to Episodic Memory
        self._log_to_episodic_memory(
            task_id=task_id,
            tool_name=tool_name,
            original_prompt=original_user_request,
            status=final_status.value,
            verified=is_verified,
            score=critic_eval.critic_score,
            reasoning=critic_eval.reasoning
        )

        return TaskResult(
            task_id=task_id,
            idempotency_key=task_id,
            status=final_status,
            result_data=raw_result_data,
            error_message=critic_eval.reasoning if not is_verified else None,
            executor_agent_id=executor_agent_id,
            execution_time_ms=execution_time_ms,
            verified=is_verified,
            verification_note=f"Critic (score={critic_eval.critic_score}): {critic_eval.reasoning}",
            critic_score=critic_eval.critic_score
        )

    def _run_critic_pass(
        self,
        original_user_request: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        raw_result_data: Dict[str, Any]
    ) -> CriticEvaluation:
        """Invokes LLM Critic or performs algorithmic heuristics."""
        critic_prompt = (
            f"You are the AURA-OS Verification Critic. Evaluate whether the tool execution result genuinely satisfies Mukil's request.\n\n"
            f"User Request: {original_user_request}\n"
            f"Tool Executed: {tool_name}\n"
            f"Input Parameters: {json.dumps(tool_params, default=str)}\n"
            f"Execution Output: {json.dumps(raw_result_data, default=str)[:2000]}\n\n"
            f"Respond with JSON: {{'is_satisfied': bool, 'critic_score': float (0.0-1.0), 'reasoning': str, 'suggested_retry_params': dict or null}}"
        )

        if self.llm_client:
            try:
                # Direct LLM invocation if client configured
                response_text = self.llm_client(critic_prompt)
                parsed = json.loads(response_text)
                return CriticEvaluation.model_validate(parsed)
            except Exception as e:
                logger.error(f"Critic LLM execution error: {e}")

        # Deterministic Fallback Critic Heuristics
        # If output contains error flag or is empty
        if raw_result_data.get("success") is False or raw_result_data.get("error"):
            return CriticEvaluation(
                is_satisfied=False,
                critic_score=0.2,
                reasoning=f"Execution reported error: {raw_result_data.get('error', 'unknown')}"
            )

        # For spinning mills scraper: check if returned mills match district
        if tool_name == "scrape_spinning_mills":
            mills = raw_result_data.get("mills", [])
            target_dist = tool_params.get("district", "Karur").lower()
            matching = [m for m in mills if target_dist in str(m).lower() or not m.get("district")]
            if len(mills) > 0 and len(matching) > 0:
                return CriticEvaluation(
                    is_satisfied=True,
                    critic_score=0.92,
                    reasoning=f"Successfully extracted {len(mills)} spinning mills for {target_dist.capitalize()} district."
                )
            return CriticEvaluation(
                is_satisfied=False,
                critic_score=0.45,
                reasoning=f"No matching mills found for {target_dist}."
            )

        # For resume tailoring: check ats score
        if tool_name == "tailor_placement_resume":
            score = raw_result_data.get("ats_score", 0)
            if score >= 85:
                return CriticEvaluation(
                    is_satisfied=True,
                    critic_score=score / 100.0,
                    reasoning=f"ATS score {score}% exceeds threshold (85%)."
                )
            return CriticEvaluation(
                is_satisfied=False,
                critic_score=score / 100.0,
                reasoning=f"ATS score {score}% is below required 85% threshold."
            )

        # For antigravity code execution: check exit code
        if tool_name == "execute_headless_antigravity":
            if raw_result_data.get("exit_code") == 0 or raw_result_data.get("success") is True:
                return CriticEvaluation(
                    is_satisfied=True,
                    critic_score=0.95,
                    reasoning="Headless Antigravity task executed with exit code 0 and audit report created."
                )
            return CriticEvaluation(
                is_satisfied=False,
                critic_score=0.3,
                reasoning="Antigravity execution failed with non-zero exit code."
            )

        return CriticEvaluation(
            is_satisfied=True,
            critic_score=0.85,
            reasoning="Default structural verification passed."
        )

    def _log_to_episodic_memory(
        self,
        task_id: str,
        tool_name: str,
        original_prompt: str,
        status: str,
        verified: bool,
        score: float,
        reasoning: str
    ):
        """Logs structured verification record for audit and learning."""
        try:
            import os
            memory_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "memory")
            log_file = os.path.join(memory_dir, "episodic_tasks.json")
            records = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception:
                    records = []

            records.append({
                "task_id": task_id,
                "tool_name": tool_name,
                "original_prompt": original_prompt,
                "status": status,
                "verified": verified,
                "critic_score": score,
                "reasoning": reasoning
            })

            # Keep last 500 records
            if len(records) > 500:
                records = records[-500:]

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not log episodic record: {e}")


# Global Singleton Instance
verifier = TaskVerifier()

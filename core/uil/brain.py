"""Unified Intelligence Layer — orchestrator only.

Orchestrates the UIL pipeline:
  1. Analyze (classify user input)
  2. Route (select mode + filter tools)
  3. Plan (optional cognitive enhancer)
  4. Execute (delegate to executor via ExecutionContext)
  5. Verify (post-execution quality checks — Phase VERIFY)
  6. Feedback (wrap result in ExecutionResult)
  7. Knowledge (record execution outcome)

Contains NO classification logic.
Contains NO tool selection logic.
Pure orchestration — delegates everything.
"""

import time
import logging
from typing import Any

logger = logging.getLogger("widdx.uil.brain")

from .analyzer import TaskAnalyzer
from .router import DecisionRouter
from .planner import TaskPlanner
from .contract import (ExecutionMode, ExecutionPlan, RoutingDecision,
                       DecisionStep, ExecutionContext, ExecutionResult,
                       StepResult, ExecutionMetrics, VerificationSeverity)
from .knowledge import KnowledgeBase
from .verifier import get_verifier


# -------------------------------------------------------------------
# Execution Mode Executor Map — imported lazily to avoid circular
# dependency issues at module-load time.
# -------------------------------------------------------------------

_EXECUTOR_MAP: dict[ExecutionMode, callable] | None = None


def _get_executor_map() -> dict[ExecutionMode, callable]:
    """Lazy-load EXECUTOR_MAP from executor_adapter on first call.

    Returns an empty dict (with a logged warning) if the import fails,
    keeping ``_resolve_executor``'s error message clear.
    """
    global _EXECUTOR_MAP
    if _EXECUTOR_MAP is not None:
        return _EXECUTOR_MAP

    try:
        from ..agents.executor_adapter import EXECUTOR_MAP as _MAP
        _EXECUTOR_MAP = _MAP
    except ImportError as exc:
        logger.warning("Could not load EXECUTOR_MAP from executor_adapter: %s", exc)
        _EXECUTOR_MAP = {}
    return _EXECUTOR_MAP


# -------------------------------------------------------------------
# UIL — Main Orchestrator
# -------------------------------------------------------------------

class UnifiedIntelligenceLayer:
    """Central orchestrator for the WIDDX AI system.

    Pipeline:
      process(user_input)
        → analyzer.analyze()    [classification]
        → router.route()        [decision]
        → executor()            [execution]

    The executor function is injected as a dependency (executors dict).
    This keeps brain.py testable without importing main.py or system modules.
    """

    def __init__(self, analyzer: TaskAnalyzer | None = None,
                 router: DecisionRouter | None = None,
                 planner: TaskPlanner | None = None,
                 tool_defs: list[dict] | None = None,
                 provider=None):
        # Pass provider to TaskAnalyzer for LLM-based classification fallback
        self.analyzer = analyzer or TaskAnalyzer(provider=provider)
        self.router = router or DecisionRouter()
        # Phase 2.1: Planner is ALWAYS active — dead code removal
        self.planner = planner or TaskPlanner()
        self._tool_defs = tool_defs or []
        self.knowledge = KnowledgeBase()
        self.provider = provider

    def process(self, user_input: str,
                messages: list | None = None,
                executors: dict[ExecutionMode, callable] | None = None,
                cfg: dict | None = None,
                state: dict | None = None,
                project_card: Any | None = None,
                ) -> tuple[ExecutionResult, RoutingDecision]:
        """Full UIL pipeline: analyze → route → plan → execute → feedback.

        Args:
            user_input: Raw text from the user.
            messages: Current conversation messages (optional context).
            executors: Execution mode → callable mapping.
                       If None, uses ``EXECUTOR_MAP`` from
                       ``core.agents.executor_adapter`` (real agents).
            cfg: User configuration dict (passed to executors via ctx).
            state: Mutable run state dict (cost, turns, model).
                   Mutations by the executor are visible to the caller.
            project_card: Optional ``ProjectCard`` from ``ProjectScanner``.
                          Injected into the analyzer context so classifiers
                          can make project-aware decisions.

        Returns:
            (execution_result, routing_decision_with_full_trace)
            ExecutionResult carries plan-vs-execution delta for Phase 2.
        """
        # Step 1: Analyze — classify the user input
        ctx_analyzer: dict = {}
        if messages:
            ctx_analyzer["messages"] = messages
        if project_card is not None:
            ctx_analyzer["project_card"] = project_card
        classification = self.analyzer.analyze(
            user_input,
            context=ctx_analyzer or None,
        )

        # Step 2: Route — decide how to execute
        decision = self.router.route(classification, self._tool_defs,
                                        knowledge=self.knowledge)

        # Step 2.5: Plan — ALWAYS runs (Phase 2.1: dead-code removal)
        plan = self.planner.plan(classification, user_input)
        decision.plan.decomposed = plan
        decision.decision_path.append(DecisionStep(
            component="TaskPlanner",
            input_summary=f"type={classification.task_type.value}",
            output=f"{'minimal' if plan.is_minimal else 'decomposed'}: "
                   f"{len(plan.steps)} step(s)",
            score=1.0,
            detail=("Minimal (simple task)" if plan.is_minimal
                    else "Full decomposition with dependency graph"),
        ))

        # Step 3: Build ExecutionContext with per-step telemetry
        step_results = []
        if plan and plan.steps:
            for s in plan.steps:
                step_results.append(StepResult(
                    step_id=s.id,
                    status="pending",
                    tools_used=[],
                ))
        ctx = ExecutionContext(
            decision=decision,
            task_plan=plan,
            current_step=plan.steps[0] if plan and plan.steps else None,
            step_results=step_results,
            # Execution resources — injected for real executors.
            # tool_defs comes from the RoutingDecision (filtered by router),
            # not from self._tool_defs (full unfiltered list).
            provider=getattr(self, "provider", None),
            tool_defs=decision.tool_defs,
            cfg=cfg or {},
            state=state or {},
        )

        # Step 4: Execute — delegate via ExecutionContext, measure time
        executor = self._resolve_executor(decision, executors)
        t0 = time.perf_counter()
        err_msg: str | None = None
        try:
            raw = executor(ctx, user_input, messages)
        except Exception as exc:
            err_msg = str(exc)
            raw = ExecutionResult(
                success=False,
                summary=f"Executor failed: {exc}",
                mode=decision.plan.mode if decision.plan else None,
                error=err_msg,
            )
        elapsed = time.perf_counter() - t0

        # Step 4.5: Verify — post-execution quality checks (Phase VERIFY)
        # Runs on the raw output before wrapping it in ExecutionResult.
        # Non-blocking: findings are attached, but execution continues.
        # Critical findings set result.success = False later.
        verify_t0 = time.perf_counter()
        verifier = get_verifier(classification)

        # Extract verifier context from whatever form raw is in
        raw_text = raw.summary if isinstance(raw, ExecutionResult) else str(raw)
        verifier_context = {}
        if raw_text.strip().startswith("<!DOCTYPE html") or raw_text.strip().startswith("<html"):
            verifier_context["html_content"] = raw_text
        elif "rm " in raw_text or "chmod " in raw_text or "wget " in raw_text:
            verifier_context["bash_commands"] = raw_text
        elif raw_text:
            verifier_context["code_content"] = raw_text

        verification_report = verifier.verify(
            result=raw if isinstance(raw, ExecutionResult) else ExecutionResult(
                success=True,
                summary=raw_text,
                error=err_msg,
            ),
            classification=classification,
            context=verifier_context if verifier_context else None,
        )
        verification_report.execution_time = round(time.perf_counter() - verify_t0, 4)

        # Log verification findings
        if verification_report.findings:
            logger.info(
                "Verification (%s): %s",
                verification_report.verifier_name,
                verification_report.summarize(),
            )
            for f in verification_report.findings:
                if not f.passed:
                    level = (logging.ERROR if f.severity == VerificationSeverity.CRITICAL
                             else logging.WARNING)
                    logger.log(level, "  [%s] %s — %s", f.severity.value, f.check_name, f.message)

        # Auto-retry on critical verification failures (max once)
        _retried = False
        if verification_report.criticals and not _retried:
            _retried = True
            logger.warning(
                "Verification CRITICAL — retrying execution with error context. "
                "(%d criticals)", len(verification_report.criticals)
            )
            error_hint = "VERIFICATION FAILED:\n" + "\n".join(
                f"  - {f.message}" for f in verification_report.criticals
            )
            try:
                raw = executor(ctx, user_input + "\n\n" + error_hint, messages)
                elapsed = time.perf_counter() - t0
                # Re-run verification on the retry output
                raw_text = raw.summary if isinstance(raw, ExecutionResult) else str(raw)
                verifier_context = {}
                if raw_text.strip().startswith("<!DOCTYPE html") or raw_text.strip().startswith("<html"):
                    verifier_context["html_content"] = raw_text
                elif "rm " in raw_text or "chmod " in raw_text or "wget " in raw_text:
                    verifier_context["bash_commands"] = raw_text
                elif raw_text:
                    verifier_context["code_content"] = raw_text
                verification_report = verifier.verify(
                    result=raw if isinstance(raw, ExecutionResult) else ExecutionResult(
                        success=True,
                        summary=raw_text,
                    ),
                    classification=classification,
                    context=verifier_context if verifier_context else None,
                )
                verification_report.execution_time = round(time.perf_counter() - verify_t0, 4)
                logger.info("Retry verification: %s", verification_report.summarize())
            except Exception as retry_err:
                logger.warning("Retry also failed: %s", retry_err)

        # Step 5: Feedback — build ExecutionResult + populate telemetry
        steps_count = len(plan.steps) if plan and plan.steps else 0
        if isinstance(raw, tuple) and len(raw) >= 3:
            summary, completed, failed = raw[:3]
            tools_used = raw[3] if len(raw) >= 4 else []
            result = ExecutionResult(
                success=failed == 0,
                summary=summary,
                mode=decision.plan.mode,
                steps_planned=steps_count,
                steps_completed=completed,
                steps_failed=failed,
                tools_used=tools_used,
                error=err_msg,
                plan_decomposed=plan,
            )
        elif isinstance(raw, ExecutionResult):
            result = raw
            result.steps_planned = steps_count
            if err_msg:
                result.error = err_msg
        else:
            result = ExecutionResult(
                success=True,
                summary=str(raw),
                mode=decision.plan.mode,
                steps_planned=steps_count,
                plan_decomposed=plan,
                error=err_msg,
            )
        result.execution_time = round(elapsed, 3)

        # Attach verification report to result
        result.verification = verification_report
        # If verification found critical issues, mark execution as failed
        if verification_report.criticals and result.success:
            result.success = False
            result.error = (
                f"Verification failed: {len(verification_report.criticals)} critical "
                f"issue(s). Run with /debug or check logs for details."
            )

        # Mark step_results as completed/failed based on execution outcome
        if ctx.step_results:
            for sr in ctx.step_results:
                if result.steps_failed > 0:
                    sr.status = "failed"
                    sr.error = result.error or "step failed"
                else:
                    sr.status = "completed"
                sr.start_time = t0
                sr.end_time = t0 + elapsed
                sr.duration = round(elapsed, 3)
                sr.tools_used = list(result.tools_used)

        # Populate execution_metrics
        ctx.execution_metrics = ExecutionMetrics(
            total_execution_time=round(elapsed, 3),
            total_steps=steps_count,
            completed_steps=result.steps_completed,
            failed_steps=result.steps_failed,
            tools_used_count=len(result.tools_used),
        )

        # Step 6: Knowledge — record execution outcome
        self.knowledge.record(
            classification=classification,
            result=result,
            decision=decision,
        )

        return result, decision

    def set_tool_defs(self, tool_defs: list[dict]):
        """Update the tool definitions (called when tools change)."""
        self._tool_defs = tool_defs

    # ------------------------------------------------------------------
    # Internal: executor resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_executor(
        decision: RoutingDecision,
        executors: dict[ExecutionMode, callable] | None,
    ) -> callable:
        """Find the right executor for this decision."""
        mode = decision.plan.mode
        if executors and mode in executors:
            return executors[mode]
        # Fallback to real executors from executor_adapter
        executor_map = _get_executor_map()
        if mode in executor_map:
            return executor_map[mode]
        # Last resort — raise a clear error instead of returning a stub
        raise RuntimeError(
            f"No executor registered for {mode.value}. "
            "Ensure EXECUTOR_MAP covers this mode "
            "or pass an explicit executors dict to process()."
        )

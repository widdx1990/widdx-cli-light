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
from typing import Any, Callable

logger = logging.getLogger("widdx.uil.brain")

from .analyzer import TaskAnalyzer
from .router import DecisionRouter
from .planner import TaskPlanner
from .contract import (ExecutionMode, ExecutionPlan, RoutingDecision,
                       DecisionStep, ExecutionContext, ExecutionResult,
                       StepResult, ExecutionMetrics, VerificationSeverity)
from .knowledge import KnowledgeBase
from .verifier import get_verifier

# ── v4.0 Engine adapters (feature-flagged, safe by default) ──
try:
    from core.engine_adapters import (
        engine_enabled, engine_flags_summary,
        adapt_classification, adapt_plan, adapt_validation,
    )
    _ENGINES_AVAILABLE = True
except ImportError:
    _ENGINES_AVAILABLE = False


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
                on_event: Callable | None = None,
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

        # ── v4.0: Intelligence Engine parallel classification ──
        if _ENGINES_AVAILABLE and engine_enabled(cfg or {}, "intelligence"):
            try:
                from core.intelligence.classifier import classify_input
                new_cr = classify_input(user_input)
                adapted = adapt_classification(new_cr)
                logger.info(
                    "IntelligenceEngine: %s (%.2f) vs Analyzer: %s (%.2f)",
                    adapted.task_type.value, adapted.confidence,
                    classification.task_type.value, classification.confidence,
                )
                if adapted.task_type != classification.task_type:
                    if adapted.confidence >= 0.6:
                        logger.info(
                            "IntelligenceEngine wins (confidence=%.2f): %s → %s",
                            adapted.confidence,
                            classification.task_type.value,
                            adapted.task_type.value,
                        )
                        classification = adapted
                    elif adapted.confidence >= 0.4 and classification.confidence < 0.3:
                        logger.info(
                            "IntelligenceEngine overrides low-confidence analyzer: %s (%.2f) → %s (%.2f)",
                            classification.task_type.value, classification.confidence,
                            adapted.task_type.value, adapted.confidence,
                        )
                        classification = adapted
                    else:
                        logger.warning(
                            "Engine DISAGREE: intelligence=%s(%.2f) analyzer=%s(%.2f) → using analyzer",
                            adapted.task_type.value, adapted.confidence,
                            classification.task_type.value, classification.confidence,
                        )
            except Exception as e:
                logger.debug("IntelligenceEngine unavailable: %s", e)

        # Step 1.5: Validate — check classification confidence
        # Correction boundary: if fallback + very low confidence → force CHAT
        if getattr(classification, 'is_fallback', False) and classification.confidence < 0.4:
            logger.warning(
                "Fallback classification with very low confidence (%.2f) — "
                "forcing CHAT to prevent cascading errors.",
                classification.confidence,
            )
            classification.task_type = classification.task_type.__class__.CHAT \
                if hasattr(classification.task_type, '__class__') else TaskType.CHAT
            try:
                from core.uil.contract import TaskType as _TT
                classification.task_type = _TT.CHAT
                classification.confidence = 0.3
            except Exception:
                pass

        if classification.confidence < 0.4:
            logger.warning(
                "Low classification confidence (%.2f) for '%s' — "
                "classified as %s. Execution may produce poor results.",
                classification.confidence, user_input[:60],
                classification.task_type.value,
            )
        elif classification.confidence < 0.6:
            logger.info(
                "Moderate confidence (%.2f) for '%s' → %s",
                classification.confidence, user_input[:60],
                classification.task_type.value,
            )

        # Step 2: Route — decide how to execute
        decision = self.router.route(classification, self._tool_defs,
                                        knowledge=self.knowledge)

        # Correction boundary: low-confidence → never run AUTONOMOUS or EXPERT_TEAM
        if classification.confidence < 0.5:
            if decision.plan.mode in (ExecutionMode.AUTONOMOUS, ExecutionMode.EXPERT_TEAM):
                logger.warning(
                    "Low confidence (%.2f) — downgrading %s → SIMPLE_CHAT with full tools",
                    classification.confidence, decision.plan.mode.value,
                )
                decision.plan.mode = ExecutionMode.SIMPLE_CHAT
                decision.tool_defs = self._tool_defs  # give all tools so LLM can still help

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

        # Inject plan steps into executor input so LLM-guided executors follow the plan
        enriched_input = user_input
        if plan and plan.steps and not plan.is_minimal:
            plan_text = "\n".join(
                f"  [{s.id}] {s.description}"
                for s in plan.steps
            )
            enriched_input = (
                f"{user_input}\n\n"
                f"Execution Plan ({len(plan.steps)} steps):\n{plan_text}\n\n"
                f"Follow this plan step by step."
            )

        try:
            if on_event:
                try:
                    raw = executor(ctx, enriched_input, messages, on_event=on_event)
                except TypeError:
                    # Executor doesn't support streaming — fall back to synchronous
                    raw = executor(ctx, enriched_input, messages)
            else:
                raw = executor(ctx, enriched_input, messages)
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

        # ── v4.0: Validation Engine parallel check ──
        if _ENGINES_AVAILABLE and engine_enabled(cfg or {}, "validation"):
            try:
                from core.validation.reporter import validate_result
                val_report = validate_result(
                    raw if isinstance(raw, ExecutionResult) else ExecutionResult(
                        success=True, summary=raw_text, error=err_msg,
                    ),
                    classification,
                    context=verifier_context,
                )
                logger.info(
                    "ValidationEngine: score=%.2f (syntax=%.2f runtime=%.2f quality=%.2f) "
                    "vs old verifier: %s",
                    val_report.overall,
                    val_report.syntax_score, val_report.runtime_score,
                    val_report.quality_score,
                    verification_report.summarize(),
                )
                # Attach adapted report for comparison
                adapted_val = adapt_validation(val_report)
                if adapted_val.passed_all != verification_report.passed_all:
                    logger.warning(
                        "Validation DISAGREE: new=%s old=%s → merging findings",
                        "PASS" if adapted_val.passed_all else "FAIL",
                        "PASS" if verification_report.passed_all else "FAIL",
                    )
                # Merge validation findings into verification report
                for f in adapted_val.findings:
                    if f.severity == VerificationSeverity.CRITICAL:
                        verification_report.findings.insert(0, f)
                    else:
                        verification_report.findings.append(f)
                verification_report.recompute()
            except Exception as e:
                logger.debug("ValidationEngine unavailable: %s", e)

        # Auto-retry on critical verification failures (up to 3 retries)
        MAX_RETRIES = 3
        for retry_attempt in range(1, MAX_RETRIES + 1):
            if not verification_report.criticals:
                break

            logger.warning(
                "Verification CRITICAL — retry %d/%d with re-analysis. "
                "(%d criticals)",
                retry_attempt, MAX_RETRIES, len(verification_report.criticals),
            )
            error_hint = "VERIFICATION FAILED:\n" + "\n".join(
                f"  - {f.message}" for f in verification_report.criticals
            )
            # Re-analyze with error context — may change task type
            retry_input = user_input + "\n\n[PREVIOUS OUTPUT HAD BUGS]\n" + error_hint
            retry_classification = self.analyzer.analyze(
                retry_input,
                context=ctx_analyzer or None,
            )
            # Only re-route if confidence dropped or task type changed
            if (retry_classification.task_type != classification.task_type
                    or retry_classification.confidence < classification.confidence):
                retry_decision = self.router.route(
                    retry_classification, self._tool_defs,
                    knowledge=self.knowledge,
                )
                retry_plan = self.planner.plan(retry_classification, retry_input)
                retry_decision.plan.decomposed = retry_plan
                retry_ctx = ExecutionContext(
                    decision=retry_decision,
                    task_plan=retry_plan,
                    provider=getattr(self, "provider", None),
                    tool_defs=retry_decision.tool_defs,
                    cfg=cfg or {},
                    state=state or {},
                )
                retry_executor = self._resolve_executor(retry_decision, executors)
            else:
                retry_ctx = ctx
                retry_executor = executor

            try:
                raw = retry_executor(retry_ctx, retry_input, messages)
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
                    classification=retry_classification,
                    context=verifier_context if verifier_context else None,
                )
                verification_report.execution_time = round(time.perf_counter() - verify_t0, 4)
                logger.info(
                    "Retry %d/%d verification: %s",
                    retry_attempt, MAX_RETRIES, verification_report.summarize(),
                )
                if not verification_report.criticals:
                    logger.info("Retry %d succeeded — criticals resolved.", retry_attempt)
            except Exception as retry_err:
                logger.warning(
                    "Retry %d/%d failed with exception: %s",
                    retry_attempt, MAX_RETRIES, retry_err,
                )
        else:
            # Loop completed all retries without breaking (still has criticals)
            if verification_report.criticals:
                logger.warning(
                    "All %d retries exhausted. %d critical(s) remain unresolved. "
                    "Delivering best-effort result.",
                    MAX_RETRIES, len(verification_report.criticals),
                )

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

        # ── Quality score: multi-signal metric beyond "no exception" ──
        score = 1.0
        score -= 0.3 * len(verification_report.criticals)
        score -= 0.1 * len([f for f in verification_report.findings if not f.passed])
        if result.summary and len(result.summary) < 50:
            score -= 0.2  # suspiciously short output
        if hasattr(result, 'steps_completed') and result.steps_completed > 0:
            tool_failures = sum(
                1 for sr in (ctx.step_results or [])
                if getattr(sr, 'status', '') == 'failed'
            )
            if tool_failures > 0:
                score -= 0.1 * (tool_failures / result.steps_completed)
        result.quality_score = round(max(0.0, min(1.0, score)), 2)

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

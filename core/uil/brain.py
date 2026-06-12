"""Unified Intelligence Layer — orchestrator only.

Orchestrates the UIL pipeline:
  1. Analyze (classify user input)
  2. Route (select mode + filter tools)
  3. Plan (optional cognitive enhancer)
  4. Execute (delegate to executor via ExecutionContext)
  5. Feedback (wrap result in ExecutionResult)

Contains NO classification logic.
Contains NO tool selection logic.
Pure orchestration — delegates everything.
"""

import time

from .analyzer import TaskAnalyzer
from .router import DecisionRouter
from .planner import TaskPlanner
from .contract import (ExecutionMode, ExecutionPlan, RoutingDecision,
                       DecisionStep, ExecutionContext, ExecutionResult,
                       StepResult, ExecutionMetrics)
from .knowledge import KnowledgeBase


# -------------------------------------------------------------------
# Default executors (Phase 1.2 placeholder)
# -------------------------------------------------------------------

def _default_executor(decision: RoutingDecision,
                      user_input: str,
                      messages: list | None = None) -> str:
    """Phase 1.2 stub: return summary without system execution."""
    parts = [
        f"[UIL] {decision.summarize()}",
        f"  Analysis: {decision.classification.summarize()}",
        f"  Tools: {len(decision.tool_defs)} total",
    ]
    # Show decision path
    for step in decision.decision_path:
        parts.append(
            f"  ├─ {step.component}: {step.output} "
            f"(score={step.score:.2f})"
        )
    # Show classification path
    for step in decision.classification.decision_path:
        parts.append(
            f"  ├─ [{step.component}] {step.detail[:70]}"
        )
    parts.append(f"  └─ Ready to execute with mode={decision.plan.mode.value}")
    return "\n".join(parts)


# -------------------------------------------------------------------
# Execution Mode Executor Map
# -------------------------------------------------------------------

_DEFAULT_EXECUTORS: dict[ExecutionMode, callable] = {
    ExecutionMode.SIMPLE_CHAT: _default_executor,
    ExecutionMode.AUTONOMOUS: _default_executor,
    ExecutionMode.EXPERT_TEAM: _default_executor,
    ExecutionMode.DIRECT_TOOL: _default_executor,
}


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

    def process(self, user_input: str,
                messages: list | None = None,
                executors: dict[ExecutionMode, callable] | None = None
                ) -> tuple[ExecutionResult, RoutingDecision]:
        """Full UIL pipeline: analyze → route → plan → execute → feedback.

        Args:
            user_input: Raw text from the user.
            messages: Current conversation messages (optional context).
            executors: Execution mode → callable mapping.
                       If None, uses default stubs (Phase 1.2 mode).

        Returns:
            (execution_result, routing_decision_with_full_trace)
            ExecutionResult carries plan-vs-execution delta for Phase 2.
        """
        # Step 1: Analyze — classify the user input
        classification = self.analyzer.analyze(
            user_input,
            context={"messages": messages} if messages else None,
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
        # Fallback to default stubs
        return _DEFAULT_EXECUTORS.get(mode, _default_executor)

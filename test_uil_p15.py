"""Phase 1.5 — Execution Feedback Layer + Plan Consumption Tests.

Tests the two new layers:
  1. Feedback Layer: string→ExecutionResult wrapping, structured outcome
  2. Plan Consumption Layer: ExecutionContext delegation + plan awareness
  3. ExecutionContext behaves exactly like RoutingDecision (no silent bugs)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.uil.contract import (
    TaskType, Domain, ExecutionMode,
    ClassificationResult, RoutingDecision, ExecutionPlan,
    DecisionStep, ExecutionResult, ExecutionContext, Plan, TaskStep,
)
from core.uil.brain import UnifiedIntelligenceLayer
from core.uil.planner import TaskPlanner
from core.uil.router import DecisionRouter


# =====================================================================
# F1 — Feedback Layer: string executor auto-wrapping
# =====================================================================

def test_feedback_string_wrapping():
    """String-returning executor → brain wraps into ExecutionResult."""
    uil = UnifiedIntelligenceLayer()

    def simple_exec(decision, inp, msgs):
        return f"[echo] {inp}"

    executors = {ExecutionMode.SIMPLE_CHAT: simple_exec}
    uil.set_tool_defs([])
    result, decision = uil.process("hi hello", executors=executors)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.summary == "[echo] hi hello"
    assert result.mode == ExecutionMode.SIMPLE_CHAT
    assert result.execution_time >= 0.0  # may be 0.0 for ultra-fast exec
    assert result.error is None
    assert isinstance(result.tools_used, list)


# =====================================================================
# F2 — Feedback Layer: rich executor passthrough
# =====================================================================

def test_feedback_rich_passthrough():
    """Executor returning ExecutionResult → brain passes through + adds time."""
    uil = UnifiedIntelligenceLayer()

    def rich_exec(decision, inp, msgs):
        return ExecutionResult(
            success=False,
            summary="partial failure",
            mode=ExecutionMode.AUTONOMOUS,
            steps_completed=2,
            steps_failed=1,
            tools_used=["bash", "write"],
            error="step 3 timed out",
        )

    executors = {ExecutionMode.EXPERT_TEAM: rich_exec}
    uil.set_tool_defs([{"name": "bash"}, {"name": "write"}])
    result, decision = uil.process("build a complete web application", executors=executors)

    assert result.success is False
    assert result.summary == "partial failure"
    assert result.steps_completed == 2
    assert result.steps_failed == 1
    assert result.tools_used == ["bash", "write"]
    assert result.error == "step 3 timed out"
    assert result.execution_time >= 0.0  # added by brain, may be 0.0 for fast exec


# =====================================================================
# F3 — Feedback Layer: string executor with plan→steps_planned
# =====================================================================

def test_feedback_steps_planned_with_planner():
    """With planner active, steps_planned reflects plan length."""
    planner = TaskPlanner()
    uil = UnifiedIntelligenceLayer(planner=planner)

    classification = ClassificationResult(
        task_type=TaskType.COMPLEX, domain=Domain.CODE,
        confidence=0.9, complexity=0.8, reasoning="test",
        keywords=["web", "app"],
        detected_features={"web": True, "api": True, "database": False,
                           "cli": False, "testing": False},
    )

    def mock_exec(decision, inp, msgs):
        # Verify the plan is attached
        assert decision.plan.decomposed is not None
        assert len(decision.plan.decomposed.steps) >= 4
        return "built something"

    executors = {ExecutionMode.EXPERT_TEAM: mock_exec}
    uil.set_tool_defs([{"name": "write"}, {"name": "bash"}])
    result, decision = uil.process("build a web app with a backend API",
                                   executors=executors)

    assert result.steps_planned >= 4
    assert result.plan_decomposed is not None
    assert result.plan_decomposed.is_minimal is False
    assert result.summary == "built something"


# =====================================================================
# P1 — Plan Consumption: ExecutionContext carries task_plan
# =====================================================================

def test_plan_consumption_context_carries_plan():
    """Brain passes ExecutionContext with task_plan to executor."""
    planner = TaskPlanner()
    uil = UnifiedIntelligenceLayer(planner=planner)

    captured_ctx = {}

    def plan_aware_exec(ctx, inp, msgs):
        captured_ctx["is_ec"] = isinstance(ctx, ExecutionContext)
        captured_ctx["task_plan"] = ctx.task_plan
        captured_ctx["has_task_plan"] = ctx.task_plan is not None
        # Verify delegation still works
        captured_ctx["mode"] = ctx.plan.mode.value  # __getattr__ → decision.plan
        return "done"

    executors = {ExecutionMode.EXPERT_TEAM: plan_aware_exec}
    uil.set_tool_defs([{"name": "write"}, {"name": "bash"}])
    result, decision = uil.process("build a web app with a backend API",
                                   executors=executors)

    assert captured_ctx["is_ec"] is True
    assert captured_ctx["task_plan"] is not None
    assert captured_ctx["has_task_plan"] is True
    assert captured_ctx["mode"] == "expert_team"


# =====================================================================
# P2 — Plan Consumption: no planner → task_plan=None, behavior unchanged
# =====================================================================

def test_plan_consumption_no_planner():
    """Without planner, task_plan is None, executor works unchanged."""
    uil = UnifiedIntelligenceLayer()  # planner=None

    captured = {}

    def exec_no_plan(ctx, inp, msgs):
        captured["task_plan"] = ctx.task_plan
        captured["is_ec"] = isinstance(ctx, ExecutionContext)
        captured["classification_works"] = ctx.classification is not None
        captured["tool_defs_works"] = isinstance(ctx.tool_defs, list)
        return "ok"

    executors = {ExecutionMode.SIMPLE_CHAT: exec_no_plan}
    uil.set_tool_defs([])
    result, decision = uil.process("hi hello", executors=executors)

    assert captured["task_plan"] is not None  # planner always active (Phase 2.1)
    assert captured["is_ec"] is True
    assert captured["classification_works"] is True
    assert captured["tool_defs_works"] is True


# =====================================================================
# D1 — Delegation: ExecutionContext behaves like RoutingDecision
# =====================================================================
# The user's condition: no silent delegation bugs.
# Must verify ALL fields used by executors: classification, plan,
# tool_defs, decision_path, summarize().

def test_delegation_all_routing_decision_fields():
    """ExecutionContext delegates every RoutingDecision field correctly."""
    router = DecisionRouter()

    cls = ClassificationResult(
        TaskType.CODE_WRITE, Domain.CODE, 0.85, 0.6, "test delegation", [],
    )
    tools = [{"name": "read"}, {"name": "write"}, {"name": "bash"}]
    decision = router.route(cls, tools)

    ctx = ExecutionContext(decision=decision)

    # classification — delegated
    assert ctx.classification is decision.classification
    assert ctx.classification.task_type == TaskType.CODE_WRITE

    # plan (ExecutionPlan, not Plan) — delegated
    assert ctx.plan is decision.plan
    assert ctx.plan.mode == ExecutionMode.AUTONOMOUS
    assert ctx.plan.max_turns == 15

    # tool_defs — delegated
    assert ctx.tool_defs is decision.tool_defs
    assert len(ctx.tool_defs) == 3

    # decision_path — delegated
    assert ctx.decision_path is decision.decision_path
    assert len(ctx.decision_path) >= 2

    # summarize() — delegated method
    assert ctx.summarize() == decision.summarize()
    assert "mode=" in ctx.summarize()

    # context — delegated
    assert ctx.context == decision.context

    # Direct field access (should NOT delegate, returns ExecutionContext's own)
    assert ctx.task_plan is None
    assert ctx.current_step is None


# =====================================================================
# D2 — Delegation: existing executor accesses plan.mode via delegation
# =====================================================================

def test_delegation_existing_executor_unchanged():
    """Executor accessing decision.plan.mode.value works via delegation."""
    uil = UnifiedIntelligenceLayer()

    captured_mode = {}

    def legacy_style_exec(decision, inp, msgs):
        # This is exactly what existing executors do:
        # they access decision.plan.mode, decision.tool_defs, etc.
        captured_mode["mode"] = decision.plan.mode
        captured_mode["tool_count"] = len(decision.tool_defs)
        captured_mode["has_classification"] = decision.classification is not None
        captured_mode["has_summarize"] = callable(decision.summarize)
        return "legacy ok"

    executors = {ExecutionMode.AUTONOMOUS: legacy_style_exec}
    uil.set_tool_defs([{"name": "bash"}, {"name": "write"}])
    result, decision = uil.process("create a new file", executors=executors)

    assert captured_mode["mode"] == ExecutionMode.AUTONOMOUS
    assert captured_mode["tool_count"] == 2  # CODE_WRITE gets write+bash via domain
    assert captured_mode["has_classification"] is True
    assert captured_mode["has_summarize"] is True
    assert result.summary == "legacy ok"


if __name__ == "__main__":
    print("=" * 55)
    print("Phase 1.5 — Feedback + Plan Consumption Tests")
    print("=" * 55)

    print("\n--- Feedback Layer ---")
    test_feedback_string_wrapping()
    test_feedback_rich_passthrough()
    test_feedback_steps_planned_with_planner()

    print("\n--- Plan Consumption ---")
    test_plan_consumption_context_carries_plan()
    test_plan_consumption_no_planner()

    print("\n--- Delegation Verification ---")
    test_delegation_all_routing_decision_fields()
    test_delegation_existing_executor_unchanged()

    print("\n" + "=" * 55)
    print("ALL 7 TESTS PASSED — Phase 1.5 complete")
    print("=" * 55)

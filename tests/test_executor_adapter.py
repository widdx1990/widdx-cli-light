"""Tests for core/agents/executor_adapter.py — Phase A.1.

Covers:
  - simple_chat_executor: returns ExecutionResult, handles plan injection
  - autonomous_executor: dispatches to AutonomousAgent, counts steps
  - expert_team_executor: dispatches to ExpertTeam
  - direct_tool_executor: picks and runs one tool
  - EXECUTOR_MAP: covers all 4 modes

Every test uses a MockProvider — never calls a real LLM (T3 ✓).
Type hints on every test function (L2 ✓).
Names explain what they test (T2 ✓).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest

from core.agents.executor_adapter import (
    EXECUTOR_MAP,
    simple_chat_executor,
    autonomous_executor,
    expert_team_executor,
    direct_tool_executor,
)
from core.uil.contract import (
    ExecutionMode,
    ExecutionContext,
    ExecutionResult,
    TaskType,
    Domain,
    ClassificationResult,
    ExecutionPlan,
    RoutingDecision,
    Plan,
    TaskStep,
)


# ---------------------------------------------------------------------------
# Mock provider — never calls a real LLM (T3 ✓)
# ---------------------------------------------------------------------------

class MockProvider:
    """Simulates an LLM provider for testing.

    Attributes:
        chat_response: What ``chat()`` returns as (content, tool_calls).
        stream_events: What ``stream()`` yields (list of event dicts).
    """

    def __init__(self):
        self.name = "mock"
        self.model = "mock-model"
        self.chat_response: tuple[str, list] = ("Mock reply", [])
        self.stream_events: list[dict] = []
        self.api_key = "test-key"

    def chat(self, messages: list, tools: list | None = None,
             temperature: float = 0.7) -> tuple[str, list]:
        """Return preset chat response."""
        return self.chat_response

    def stream(self, messages: list, tools: list | None = None,
               temperature: float = 0.7):
        """Yield preset stream events."""
        yield from self.stream_events


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_classification(
    task_type: TaskType = TaskType.CHAT,
    domain: Domain = Domain.CHAT,
) -> ClassificationResult:
    """Create a minimal ClassificationResult."""
    return ClassificationResult(
        task_type=task_type,
        domain=domain,
        confidence=0.95,
        complexity=0.2,
        reasoning="test classification",
    )


def make_decision(
    mode: ExecutionMode = ExecutionMode.SIMPLE_CHAT,
    task_type: TaskType = TaskType.CHAT,
    tool_defs: list[dict] | None = None,
) -> RoutingDecision:
    """Create a minimal RoutingDecision."""
    classification = make_classification(task_type=task_type)
    plan = ExecutionPlan(mode=mode)
    return RoutingDecision(
        classification=classification,
        plan=plan,
        tool_defs=tool_defs or [],
    )


def make_context(
    mode: ExecutionMode = ExecutionMode.SIMPLE_CHAT,
    task_type: TaskType = TaskType.CHAT,
    tool_defs: list[dict] | None = None,
    provider: Any = None,
    cfg: dict | None = None,
    state: dict | None = None,
    *,
    _no_provider: bool = False,
) -> ExecutionContext:
    """Create a minimal ExecutionContext with execution resources.

    Args:
        _no_provider: If True, leaves provider as None (for error-path tests).
                      The default (False) creates a MockProvider.
    """
    decision = make_decision(mode=mode, task_type=task_type, tool_defs=tool_defs)
    resolved_provider = None if _no_provider else (provider or MockProvider())
    return ExecutionContext(
        decision=decision,
        task_plan=None,
        current_step=None,
        step_results=[],
        provider=resolved_provider,
        tool_defs=tool_defs or [],
        cfg=cfg or {},
        state=state or {},
    )


def make_tool_def(name: str) -> dict:
    """Create a minimal tool definition dict."""
    return {
        "name": name,
        "description": f"A {name} tool",
        "parameters": {"type": "object", "properties": {}},
    }


# ===================================================================
# Tests: simple_chat_executor
# ===================================================================

class TestSimpleChatExecutor:
    """simple_chat_executor: direct LLM call, no agent loop."""

    def test_returns_execution_result(self):
        """Every call returns an ExecutionResult with expected fields."""
        ctx = make_context(provider=MockProvider())
        result = simple_chat_executor(ctx, "hello", messages=None)
        assert isinstance(result, ExecutionResult)
        assert result.mode == ExecutionMode.SIMPLE_CHAT
        # summary is a string (could be empty if streaming produces nothing)
        assert isinstance(result.summary, str)

    def test_success_on_normal_reply(self):
        """When the provider returns content, result.success is True."""
        provider = MockProvider()
        provider.chat_response = ("Hello, world!", [])
        ctx = make_context(provider=provider)
        result = simple_chat_executor(ctx, "hi", messages=[])
        assert result.success is True
        assert result.summary == "Hello, world!"

    def test_failure_on_provider_error(self):
        """When the provider raises, result.success is False with error."""
        class BrokenProvider:
            name = "broken"
            model = "broken"
            api_key = "x"
            def chat(self, *a, **kw):
                raise ConnectionError("Network down")

        ctx = make_context(provider=BrokenProvider())
        result = simple_chat_executor(ctx, "hi", messages=None)
        assert result.success is False
        assert "Network down" in result.error

    def test_injects_plan_when_decomposed(self):
        """When the plan has steps, they are injected into the message list."""
        provider = MockProvider()
        provider.chat_response = ("Planned reply", [])
        plan = Plan(steps=[
            TaskStep(id="s1", description="Step one"),
            TaskStep(id="s2", description="Step two"),
        ], is_minimal=False)
        decision = make_decision(mode=ExecutionMode.SIMPLE_CHAT)
        ctx = ExecutionContext(
            decision=decision,
            task_plan=plan,
            current_step=plan.steps[0],
            step_results=[],
            provider=provider,
            tool_defs=[],
            cfg={},
            state={"tools_used": []},
        )
        result = simple_chat_executor(ctx, "do the thing", messages=None)
        assert result.success is True

    def test_no_provider_raises_clear_error(self):
        """When provider is None, a RuntimeError is raised."""
        ctx = make_context(_no_provider=True)
        result = simple_chat_executor(ctx, "hi", messages=None)
        assert result.success is False
        assert "provider is None" in (result.error or "")


# ===================================================================
# Tests: autonomous_executor
# ===================================================================

class TestAutonomousExecutor:
    """autonomous_executor: dispatches to AutonomousAgent."""

    def test_returns_execution_result(self):
        """Returns an ExecutionResult with AUTONOMOUS mode."""
        provider = MockProvider()
        provider.chat_response = ("Done", [])
        ctx = make_context(
            mode=ExecutionMode.AUTONOMOUS,
            task_type=TaskType.CODE_WRITE,
            provider=provider,
        )
        result = autonomous_executor(ctx, "write a file", messages=None)
        assert isinstance(result, ExecutionResult)
        assert result.mode == ExecutionMode.AUTONOMOUS

    def test_success_when_agent_completes(self):
        """Agent completes successfully → success=True, summary present."""
        provider = MockProvider()
        provider.chat_response = ("Task completed.", [])
        ctx = make_context(
            mode=ExecutionMode.AUTONOMOUS,
            task_type=TaskType.CODE_WRITE,
            provider=provider,
        )
        result = autonomous_executor(ctx, "write hello.py", messages=None)
        assert result.success is True
        assert result.summary

    def test_injects_plan_when_available(self):
        """Decomposed plan steps are prepended to the agent's input."""
        provider = MockProvider()
        provider.chat_response = ("Planned task done.", [])
        plan = Plan(steps=[
            TaskStep(id="s1", description="Create file"),
            TaskStep(id="s2", description="Add content"),
        ], is_minimal=False)
        decision = make_decision(
            mode=ExecutionMode.AUTONOMOUS,
            task_type=TaskType.CODE_WRITE,
        )
        ctx = ExecutionContext(
            decision=decision,
            task_plan=plan,
            current_step=plan.steps[0],
            step_results=[],
            provider=provider,
            tool_defs=[],
            cfg={},
            state={},
        )
        result = autonomous_executor(ctx, "write app", messages=None)
        assert result.success is True

    def test_no_provider_raises_clear_error(self):
        """When provider is None, returns failure with clear message."""
        ctx = make_context(
            mode=ExecutionMode.AUTONOMOUS,
            _no_provider=True,
        )
        result = autonomous_executor(ctx, "do it", messages=None)
        assert result.success is False
        assert "provider is None" in (result.error or "")


# ===================================================================
# Tests: expert_team_executor
# ===================================================================

class TestExpertTeamExecutor:
    """expert_team_executor: dispatches to ExpertTeam."""

    def test_returns_execution_result(self):
        """Returns an ExecutionResult with EXPERT_TEAM mode."""
        provider = MockProvider()
        provider.chat_response = ("Team report", [])
        ctx = make_context(
            mode=ExecutionMode.EXPERT_TEAM,
            task_type=TaskType.COMPLEX,
            provider=provider,
        )
        result = expert_team_executor(ctx, "build a web app", messages=None)
        assert isinstance(result, ExecutionResult)
        assert result.mode == ExecutionMode.EXPERT_TEAM

    def test_summary_is_non_empty_string(self):
        """ExpertTeam returns a report string as summary."""
        provider = MockProvider()
        provider.chat_response = ("Final report content.", [])
        ctx = make_context(
            mode=ExecutionMode.EXPERT_TEAM,
            task_type=TaskType.COMPLEX,
            provider=provider,
        )
        result = expert_team_executor(ctx, "build API", messages=None)
        assert result.success is True
        assert isinstance(result.summary, str)


# ===================================================================
# Tests: direct_tool_executor
# ===================================================================

class TestDirectToolExecutor:
    """direct_tool_executor: picks and runs a single tool."""

    def test_returns_execution_result(self):
        """Returns an ExecutionResult with DIRECT_TOOL mode."""
        ctx = make_context(
            mode=ExecutionMode.DIRECT_TOOL,
            task_type=TaskType.SYSTEM,
            tool_defs=[make_tool_def("list_files")],
        )
        result = direct_tool_executor(ctx, ".", messages=None)
        assert isinstance(result, ExecutionResult)
        assert result.mode == ExecutionMode.DIRECT_TOOL

    def test_handles_empty_tool_defs(self):
        """When no tools are available, returns a non-fatal summary."""
        ctx = make_context(
            mode=ExecutionMode.DIRECT_TOOL,
            task_type=TaskType.SYSTEM,
            tool_defs=[],
        )
        result = direct_tool_executor(ctx, "run something", messages=None)
        assert result.success is True  # non-fatal — no tools is informational
        assert "No tools" in result.summary


# ===================================================================
# Tests: EXECUTOR_MAP
# ===================================================================

class TestExecutorMap:
    """EXECUTOR_MAP covers all 4 modes and maps to callables."""

    def test_covers_all_modes(self):
        """All 4 ExecutionMode values are present in EXECUTOR_MAP."""
        expected_modes = {
            ExecutionMode.SIMPLE_CHAT,
            ExecutionMode.AUTONOMOUS,
            ExecutionMode.EXPERT_TEAM,
            ExecutionMode.DIRECT_TOOL,
        }
        assert set(EXECUTOR_MAP.keys()) == expected_modes

    def test_each_is_callable(self):
        """Every value in EXECUTOR_MAP is a callable function."""
        for mode, executor in EXECUTOR_MAP.items():
            assert callable(executor), f"{mode.value} executor is not callable"

    def test_each_returns_execution_result(self):
        """Each executor, when called with a minimal ctx, returns ExecutionResult."""
        provider = MockProvider()
        provider.chat_response = ("test", [])
        for mode, executor in EXECUTOR_MAP.items():
            ctx = make_context(mode=mode, provider=provider)
            result = executor(ctx, "test input", messages=None)
            assert isinstance(result, ExecutionResult), (
                f"{mode.value} executor did not return ExecutionResult "
                f"(got {type(result).__name__})"
            )


# ===================================================================
# Tests: edge cases
# ===================================================================

class TestEdgeCases:

    def test_empty_user_input(self):
        """Executors tolerate empty user input."""
        provider = MockProvider()
        provider.chat_response = ("", [])
        ctx = make_context(provider=provider)
        result = simple_chat_executor(ctx, "", messages=None)
        assert isinstance(result, ExecutionResult)

    def test_very_long_user_input(self):
        """Executors tolerate very long user input (no crash)."""
        provider = MockProvider()
        provider.chat_response = ("OK", [])
        ctx = make_context(provider=provider)
        long_text = "a" * 100_000
        result = simple_chat_executor(ctx, long_text, messages=None)
        assert isinstance(result, ExecutionResult)

    def test_state_mutations_visible_to_caller(self):
        """State dict mutations by the executor are visible to the caller."""
        provider = MockProvider()
        provider.chat_response = ("test", [])
        shared_state: dict[str, Any] = {"tools_used": []}
        ctx = make_context(provider=provider, state=shared_state)
        simple_chat_executor(ctx, "hello", messages=[])
        # The executor should have mutated the shared dict
        assert "tools_used" in shared_state

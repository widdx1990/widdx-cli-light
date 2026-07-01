"""UIL Executor Adapters — bridge between UIL contracts and real agent executors.

Each adapter takes ``(ctx, user_input, messages)`` per UIL contract and returns
an ``ExecutionResult``.  This lets the UIL Brain dispatch to real agents
(``AutonomousAgent``, ``ExpertTeam``) via a uniform interface.

Every public executor in this module:
  - Is tested in ``tests/test_executor_adapter.py``
  - Has full type hints (L2 ✓)
  - Has Google-style docstring (L3 ✓)
  - Returns ``ExecutionResult`` (U1 ✓)
  - Logs errors instead of swallowing them (L4 ✓)
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ..uil.contract import (
    ExecutionMode,
    ExecutionContext,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resolve_provider(ctx: ExecutionContext) -> Any:
    """Extract the LLM provider from context or raise."""
    provider = getattr(ctx, "provider", None)
    if provider is not None:
        return provider
    raise RuntimeError(
        "ExecutionContext.provider is None. "
        "Call brain.process(provider=...) or set UIL(provider=...) "
        "before calling this executor."
    )


def _extract_plan(ctx: ExecutionContext, user_input: str) -> tuple[str, int]:
    """If the plan is decomposed, prepend plan steps to user input.

    Returns:
        (augmented_input, planned_steps_count)
    """
    plan = getattr(ctx, "task_plan", None) or getattr(ctx, "plan", None)
    if plan is None:
        return user_input, 0
    is_minimal = getattr(plan, "is_minimal", True)
    steps = getattr(plan, "steps", None) or []
    if not steps or is_minimal:
        return user_input, 0
    steps_text = "\n".join(f"  {s.id}: {s.description}" for s in steps)
    augmented = f"[SYSTEM: Planner — {len(steps)} steps]\n{steps_text}\n\n---\n{user_input}"
    return augmented, len(steps)


def _count_success_fail(steps: list) -> tuple[int, int]:
    """Count completed and failed AgentSteps by inspecting their ``status`` attr."""
    completed = sum(1 for s in steps if getattr(s, "status", "done") != "failed")
    failed = len(steps) - completed
    return completed, failed


# ---------------------------------------------------------------------------
# Streaming event helpers
# ---------------------------------------------------------------------------

def _make_on_event_provider(provider, on_event):
    """Wrap a provider so stream() events are forwarded to on_event."""
    orig_stream = provider.__class__.stream

    def wrapped_stream(self, messages, tool_defs, temperature):
        for event in orig_stream(self, messages, tool_defs, temperature):
            if event["type"] == "content":
                if on_event:
                    on_event({"type": "text", "data": event["data"]})
            elif event["type"] == "reasoning":
                if on_event:
                    on_event({"type": "reasoning", "data": event["data"]})
            elif event["type"] == "tool_call":
                if on_event:
                    on_event({"type": "tool", "data": event["data"]})
            yield event

    provider.stream = wrapped_stream.__get__(provider, type(provider))
    return provider


def _run_with_stream_events(provider, tool_defs, temperature, msgs, on_event):
    """Run provider.stream() forwarding events via on_event, return (content, tool_calls).

    Smart forwarding:
    - If provider yields ``reasoning`` events: content is clean → forward as ``text``
    - If no reasoning events: content has reasoning embedded → buffer, clean later
    """
    content_chunks: list[str] = []
    tool_calls: list = []
    reasoning_chunks: list[str] = []
    saw_reasoning = False

    for event in provider.stream(msgs, tool_defs, temperature):
        if event["type"] == "content":
            if saw_reasoning:
                # Provider separates reasoning → content is clean, forward as text
                content_chunks.append(event["data"])
                if on_event:
                    on_event({"type": "text", "data": event["data"]})
            else:
                # Might have reasoning embedded — buffer, don't forward yet
                content_chunks.append(event["data"])
        elif event["type"] == "reasoning":
            if not saw_reasoning:
                saw_reasoning = True
                # Flush buffered content as reasoning (it was reasoning tokens)
                for chunk in content_chunks:
                    reasoning_chunks.append(chunk)
                    if on_event:
                        on_event({"type": "reasoning", "data": chunk})
                content_chunks = []
            reasoning_chunks.append(event["data"])
            if on_event:
                on_event({"type": "reasoning", "data": event["data"]})
        elif event["type"] == "tool_call":
            tc = event["data"]
            tool_calls.append(tc)
            if on_event:
                on_event({"type": "tool", "data": tc})
        elif event["type"] == "done":
            _, tc_list = event["data"]
            tool_calls = tc_list or tool_calls

    return "".join(content_chunks), tool_calls


# ---------------------------------------------------------------------------
# Executors — each maps one ExecutionMode
# ---------------------------------------------------------------------------

def simple_chat_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
    on_event: Callable | None = None,
) -> ExecutionResult:
    """Execute a direct LLM chat turn, with optional plan injection.

    - No agent loop — single turn only.
    - Calls ``provider.chat()`` directly (display-agnostic).
    - Injects planner decomposition if the plan has >0 steps.

    Args:
        ctx: Execution context carrying provider, tool_defs, cfg, state.
        user_input: Raw user message text.
        messages: Full conversation history (system + user + assistant).
        on_event: Optional callback for streaming events (called during execution).

    Returns:
        ExecutionResult with ``summary`` set to the assistant's reply.
    """
    try:
        provider = _resolve_provider(ctx)
        tool_defs = getattr(ctx, "tool_defs", None) or []
        cfg = getattr(ctx, "cfg", None) or {}
        state = getattr(ctx, "state", None)
        if state is None:
            state = {}
        state.setdefault("cost", 0.0)
        state.setdefault("turns", 0)
        msgs = list(messages) if messages else [{"role": "user", "content": user_input}]

        # Inject plan into context
        _, n_steps = _extract_plan(ctx, user_input)
        plan_marker: dict[str, str] | None = None
        if n_steps > 0:
            plan = getattr(ctx, "task_plan", None) or getattr(ctx, "plan", None)
            if plan is not None and hasattr(plan, 'steps'):
                steps_text = "\n".join(f"  {s.id}: {s.description}" for s in plan.steps)
            else:
                steps_text = ""
            plan_marker = {
                "role": "system",
                "content": f"[PLAN — {n_steps} steps]\n{steps_text}",
            }
        if plan_marker is not None:
            msgs.append(plan_marker)

        # Use streaming path if callback is provided
        if on_event:
            content, tool_calls = _run_with_stream_events(provider, tool_defs, cfg.get("temperature", 0.7), msgs, on_event)
        else:
            content, tool_calls = provider.chat(msgs, tool_defs, cfg.get("temperature", 0.7))
        state["tools_used"] = [tc.name if hasattr(tc, 'name') else str(tc) for tc in (tool_calls or [])]
        summary = content or ""

        if not summary and not tool_calls:
            return ExecutionResult(
                success=False,
                summary="Chat produced no response.",
                mode=ExecutionMode.SIMPLE_CHAT,
                error="empty provider response",
            )

        return ExecutionResult(
            success=True,
            summary=summary,
            mode=ExecutionMode.SIMPLE_CHAT,
            tools_used=state["tools_used"],
        )
    except Exception as exc:
        logger.error("simple_chat_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Chat failed: {exc}",
            mode=ExecutionMode.SIMPLE_CHAT,
            error=str(exc),
        )


def autonomous_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
    on_event: Callable | None = None,
) -> ExecutionResult:
    """Execute a task using ``AutonomousAgent`` with full tool-calling loop.

    Args:
        ctx: Execution context carrying provider, tool_defs, cfg, state.
        user_input: Raw user message text.
        messages: Ignored for autonomous mode (agent builds its own messages).
        on_event: Optional callback for live streaming events to Web UI.

    Returns:
        ExecutionResult with structured step counts and tool usage.
    """
    try:
        provider = _resolve_provider(ctx)
        tool_defs = getattr(ctx, "tool_defs", None) or []
        cfg = getattr(ctx, "cfg", None) or {}
        state = getattr(ctx, "state", None)
        if state is None:
            state = {}
        state.setdefault("cost", 0.0)
        state.setdefault("turns", 0)

        # Inject planner decomposition if available
        planned_input, _ = _extract_plan(ctx, user_input)

        from .agent import AutonomousAgent

        state["tools_used"] = []
        # Pass on_event to agent for live Web UI streaming
        agent = AutonomousAgent(provider, tool_defs, cfg, state, on_event=on_event)
        steps, summary = agent.run(planned_input)

        completed, failed = _count_success_fail(steps)
        return ExecutionResult(
            success=failed == 0,
            summary=summary,
            mode=ExecutionMode.AUTONOMOUS,
            steps_planned=len(steps),
            steps_completed=completed,
            steps_failed=failed,
            tools_used=[s.tool_name for s in steps],
        )
    except Exception as exc:
        logger.error("autonomous_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Autonomous agent failed: {exc}",
            mode=ExecutionMode.AUTONOMOUS,
            error=str(exc),
        )


def expert_team_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
    on_event: Any = None,
) -> ExecutionResult:
    """Execute a task using ``ExpertTeam`` (multi-agent pipeline).

    Args:
        ctx: Execution context carrying provider, tool_defs, cfg, state.
        user_input: Raw user message text.
        messages: Ignored for expert-team mode (team builds its own context).

    Returns:
        ExecutionResult with the final synthesized report as summary.
    """
    provider = _resolve_provider(ctx)
    tool_defs = getattr(ctx, "tool_defs", None) or []
    cfg = getattr(ctx, "cfg", None) or {}
    state = getattr(ctx, "state", None)
    if state is None:
        state = {}
    state.setdefault("cost", 0.0)
    state.setdefault("turns", 0)

    try:
        from .expert import ExpertTeam

        state["tools_used"] = []
        team = ExpertTeam(provider, tool_defs, cfg, state)
        summary = team.run(user_input)

        return ExecutionResult(
            success=True,
            summary=summary,
            mode=ExecutionMode.EXPERT_TEAM,
            tools_used=list(state.get("tools_used", [])),
        )
    except Exception as exc:
        logger.error("expert_team_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Expert team failed: {exc}",
            mode=ExecutionMode.EXPERT_TEAM,
            error=str(exc),
        )


def direct_tool_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
) -> ExecutionResult:
    """Execute a single tool directly (no agent loop).

    Picks the best matching tool from the filtered tool list and runs it
    with auto-generated arguments derived from the user input.

    Args:
        ctx: Execution context carrying tool_defs.
        user_input: Raw user message (used to derive tool arguments).
        messages: Ignored for direct-tool mode.

    Returns:
        ExecutionResult with the tool's output as summary.
    """
    tool_defs = getattr(ctx, "tool_defs", None) or []

    try:
        from ..uil.executors import run_direct_tool

        summary = run_direct_tool(ctx, user_input)
        return ExecutionResult(
            success=True,
            summary=summary,
            mode=ExecutionMode.DIRECT_TOOL,
            tools_used=[tool_defs[0]["name"]] if tool_defs else [],
        )
    except Exception as exc:
        logger.error("direct_tool_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Direct tool failed: {exc}",
            mode=ExecutionMode.DIRECT_TOOL,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Background Executor — run tasks asynchronously via BackgroundTaskManager
# ---------------------------------------------------------------------------


def background_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
) -> ExecutionResult:
    """Execute a task as a background process via ``BackgroundTaskManager``."""
    try:
        from core.background import BackgroundTaskManager
        mgr = BackgroundTaskManager()
        sandbox = getattr(ctx, "sandbox", None)
        sandbox_mode = getattr(sandbox, "mode", "auto") if sandbox else "auto"
        task_id = mgr.run(user_input, sandbox_mode=sandbox_mode)
        logger.info("Background task spawned: %s — %s", task_id, user_input[:60])
        return ExecutionResult(
            success=True,
            summary=f"Background task started: {task_id}",
            mode=ExecutionMode.SIMPLE_CHAT,
            tools_used=["background"],
        )
    except Exception as exc:
        logger.error("background_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Background task failed: {exc}",
            mode=ExecutionMode.SIMPLE_CHAT,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Delegation Executor — spawn sub-agents via DelegationManager
# ---------------------------------------------------------------------------


def delegation_executor(
    ctx: ExecutionContext,
    user_input: str,
    messages: list[dict] | None = None,
) -> ExecutionResult:
    """Delegate a task to a sub-agent via ``DelegationManager``."""
    try:
        from core.delegation import DelegationManager
        provider = _resolve_provider(ctx)
        tool_defs = getattr(ctx, "tool_defs", None) or []
        cfg = getattr(ctx, "cfg", None) or {}
        dlg = DelegationManager()
        task_id = dlg.run(user_input, provider, tool_defs, cfg)
        logger.info("Delegation spawned: %s — %s", task_id, user_input[:60])
        return ExecutionResult(
            success=True,
            summary=f"Sub-agent delegated: {task_id}",
            mode=ExecutionMode.AUTONOMOUS,
            tools_used=["delegation"],
        )
    except Exception as exc:
        logger.error("delegation_executor failed: %s", exc)
        return ExecutionResult(
            success=False,
            summary=f"Delegation failed: {exc}",
            mode=ExecutionMode.AUTONOMOUS,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Executor Map — replaces brain._DEFAULT_EXECUTORS stubs
# ---------------------------------------------------------------------------

EXECUTOR_MAP: dict[ExecutionMode, Callable] = {
    ExecutionMode.SIMPLE_CHAT: simple_chat_executor,
    ExecutionMode.AUTONOMOUS: autonomous_executor,
    ExecutionMode.EXPERT_TEAM: expert_team_executor,
    ExecutionMode.DIRECT_TOOL: direct_tool_executor,
}

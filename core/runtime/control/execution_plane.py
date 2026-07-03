"""Execution Control Plane — thin orchestrator over decomposed modules.

This is the SINGLE AUTHORITY for all control decisions.
Internally delegates to:
  - control/types.py       — data structures
  - control/evaluation.py  — signal→decision mapping
  - control/policy.py      — stabilization guards

All sensors (Guard, EI, ESC) feed signals here. Only ECP produces actions.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .types import (
    ControlAction, ControlActionType, ExecutionSignal, SignalType,
)
from .evaluation import evaluate_signals
from .policy import apply_stabilizers, MAX_TOTAL_CONTROL_ACTIONS
from .adaptive_policy import get_adaptive_policy

logger = logging.getLogger("widdx.ecp")

SIGNAL_DECAY_WINDOW_SECONDS = 15.0
SIGNAL_COALESCE_WINDOW_SECONDS = 3.0


class ExecutionControlPlane:
    """Sole decision authority for runtime execution control.

    Collects signals from sensors, evaluates them, applies stabilization
    policy, and returns a single control action per step.
    """

    def __init__(self):
        self._signals: list[ExecutionSignal] = []
        self._step_count: int = 0
        self._start_time: float = 0.0
        self._tool_failures: list[bool] = []
        self._previous_decisions: list[ControlAction] = []
        self._current_model: str = ""
        self._escalated: bool = False
        self._model_switch_count: int = 0
        self._max_model_switches: int = 3
        self._action_cooldown: int = 0
        self._total_control_actions: int = 0
        self._oscillation_pattern: list[ControlActionType] = []
        self._oscillation_warning_count: int = 0

    def start_task(self, current_model: str = "", plan_steps: int = 0):
        """Reset all state for a new task."""
        self._signals.clear()
        self._step_count = 0
        self._start_time = time.time()
        self._tool_failures.clear()
        self._previous_decisions.clear()
        self._current_model = current_model
        self._escalated = False
        self._model_switch_count = 0
        self._max_model_switches = 3
        self._action_cooldown = 0
        self._total_control_actions = 0
        self._oscillation_pattern.clear()
        self._oscillation_warning_count = 0
        logger.info("ECP: task started — model=%s", current_model)

    # ── Sensor interface ────────────────────────────────

    def collect_signal(self, signal: ExecutionSignal):
        """Feed a signal with coalescing — duplicates merged, stale dropped."""
        now = time.time()
        self._signals = [
            s for s in self._signals
            if now - s.timestamp < SIGNAL_DECAY_WINDOW_SECONDS
        ]
        for existing in self._signals:
            if (existing.signal_type == signal.signal_type
                    and now - existing.timestamp < SIGNAL_COALESCE_WINDOW_SECONDS):
                existing.value = max(existing.value, signal.value)
                existing.detail = existing.detail + "; " + signal.detail
                existing.timestamp = now
                return
        self._signals.append(signal)

    def collect_ei_feedback(self, step_quality: float, plan_adherence: float, step_num: int):
        """Record ExecutionIntelligence quality feedback."""
        if step_quality < 0.4:
            self._signals.append(ExecutionSignal(
                signal_type=SignalType.QUALITY_DEGRADATION,
                value=1.0 - step_quality,
                source="ExecutionIntelligence",
                detail=f"Low step quality ({step_quality:.2f}) at step {step_num}",
            ))

    def note_tool_result(self, success: bool, content: str = ""):
        self._step_count += 1
        self._tool_failures.append(not success)

    def note_model(self, model: str):
        self._current_model = model

    def set_plan(self, total_steps: int):
        pass

    # ── Control interface ───────────────────────────────

    def before_step(self, step: int, context: Any = None,
                    messages: list | None = None,
                    current_model: str = "") -> ControlAction:
        """Called BEFORE each LLM call. Returns single control action."""
        self._current_model = current_model or self._current_model
        self._step_count = max(self._step_count, step)

        signals = self._signals.copy()
        self._signals.clear()

        decision = self._decide(signals[-20:], step)
        self._previous_decisions.append(decision)

        if decision.action != ControlActionType.CONTINUE:
            logger.warning("ECP before_step: %s — %s (%.2f)",
                           decision.action.name, decision.reason, decision.confidence)
        return decision

    def after_step(self, step: int, tool_results: Any = None,
                   messages: list | None = None,
                   success: bool = True) -> ControlAction:
        """Called AFTER each tool execution."""
        self.note_tool_result(success)

        signals = self._signals.copy()
        self._signals.clear()

        decision = self._decide(signals, step)
        self._previous_decisions.append(decision)

        if decision.action != ControlActionType.CONTINUE:
            logger.warning("ECP after_step: %s — %s (%.2f)",
                           decision.action.name, decision.reason, decision.confidence)
        return decision

    def _decide(self, signals: list[ExecutionSignal], step: int) -> ControlAction:
        """Internal decision pipeline: cooldown → cap → evaluate → stabilize → trace."""
        t0 = time.time()

        # Cooldown
        cooldown_active = self._action_cooldown > 0
        if cooldown_active:
            self._action_cooldown -= 1
            return ControlAction(action=ControlActionType.CONTINUE, confidence=0.5)

        # Action cap
        cap_active = self._total_control_actions >= MAX_TOTAL_CONTROL_ACTIONS
        if cap_active:
            logger.warning("ECP: action cap exhausted (%d), ABORT",
                           self._total_control_actions)
            return ControlAction(
                action=ControlActionType.ABORT,
                reason=f"Control action cap reached ({MAX_TOTAL_CONTROL_ACTIONS})",
                confidence=0.95,
            )

        # Evaluate
        raw = evaluate_signals(
            signals=signals,
            step=step,
            current_model=self._current_model,
            model_switch_count=self._model_switch_count,
            max_model_switches=self._max_model_switches,
            escalated=self._escalated,
            tool_failures=self._tool_failures,
            previous_decisions=self._previous_decisions,
        )

        if raw.action == ControlActionType.SWITCH_MODEL:
            self._model_switch_count += 1

        # Stabilize
        decision, self._oscillation_pattern, self._total_control_actions, \
            self._escalated, self._action_cooldown, self._oscillation_warning_count, \
            _cooldown = apply_stabilizers(
                decision=raw,
                oscillation_pattern=self._oscillation_pattern,
                escalated=self._escalated,
                total_control_actions=self._total_control_actions,
                action_cooldown=self._action_cooldown,
                oscillation_warning_count=self._oscillation_warning_count,
            )

        # ── Trace every decision ──
        try:
            from ..benchmarks.tracer import get_tracer
            oscillation_fired = (raw.action != decision.action
                                 and decision.action != ControlActionType.CONTINUE)
            get_tracer().trace(
                step=step,
                phase="",
                signals=signals,
                raw=raw,
                stabilized=decision,
                cooldown=cooldown_active,
                cap_active=cap_active,
                oscillation=oscillation_fired,
            )
        except Exception:
            pass

        return decision

    @property
    def status(self) -> dict:
        failures = self._tool_failures[-10:] if self._tool_failures else []
        rate = sum(failures) / len(failures) if failures else 0.0
        return {
            "step_count": self._step_count,
            "model_switches": self._model_switch_count,
            "escalated": self._escalated,
            "tool_failure_rate": rate,
            "signals_pending": len(self._signals),
            "control_actions_used": self._total_control_actions,
            "control_actions_remaining": max(0, MAX_TOTAL_CONTROL_ACTIONS - self._total_control_actions),
            "cooldown_remaining": self._action_cooldown,
            "oscillation_warnings": self._oscillation_warning_count,
            "previous_decisions": [
                {"action": d.action.name, "reason": d.reason}
                for d in self._previous_decisions[-5:]
            ],
        }


_ecp: ExecutionControlPlane | None = None


def get_control_plane() -> ExecutionControlPlane:
    global _ecp
    if _ecp is None:
        _ecp = ExecutionControlPlane()
    return _ecp

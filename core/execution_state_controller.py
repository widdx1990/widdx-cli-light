"""Execution State Controller (ESC) — Deterministic layer transition engine.

The CONTROL PLANE that sits ABOVE all 5 autonomy layers. The LLM operates
INSIDE the current layer — the ESC decides which layer is active based on
deterministic signals, not LLM inference.

State transitions:
  L1 (EXECUTE)   → default start
  L2 (RETRY)     ← L1 + error detected
  L3 (ADAPT)     ← L2 + repeated failure OR stuck detection
  L4 (PREDICT)   ← L3 + risk detected BEFORE execution
  L5 (CREATE)    ← L4 + all known strategies exhausted

The ESC NEVER delegates layer selection to the LLM. It uses only:
  - Error counts
  - Stuck detector signals
  - PreFailureSim risk scores
  - Pattern availability

This is the difference between:
  "agent with layers" (LLM-driven transitions)
  "engineered cognition loop" (deterministic state machine)

Usage:
    from core.execution_state_controller import ExecutionStateController
    esc = ExecutionStateController()
    esc.signal_error("write failed")
    current_layer = esc.current_layer  # → L2
    action = esc.get_action()  # → {"layer": "L2", "action": "retry_with_backoff"}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("widdx.esc")


class AutonomyLayer(Enum):
    """Deterministic autonomy levels — controlled by ESC, not LLM."""
    L1_EXECUTE = auto()   # Normal execution
    L2_RETRY = auto()     # Error recovery with backoff
    L3_ADAPT = auto()     # Stuck → web learning, hot-reload
    L4_PREDICT = auto()   # Pre-failure simulation, strategy shift
    L5_CREATE = auto()    # All strategies exhausted → creative mode


@dataclass
class LayerAction:
    """What to do in the current layer."""
    layer: AutonomyLayer = AutonomyLayer.L1_EXECUTE
    action: str = "execute"          # "execute" | "retry" | "learn" | "predict" | "create"
    transition_reason: str = ""
    escalation_count: int = 0        # How many times we've escalated
    max_iterations: int = 25         # Max iterations in this layer
    current_iteration: int = 0


class ExecutionStateController:
    """Deterministic controller for L1→L5 transitions.

    The CONTROL PLANE. LLM operates inside layers — ESC decides the layer.
    """

    def __init__(self):
        self._current_layer = AutonomyLayer.L1_EXECUTE
        self._error_count: int = 0
        self._consecutive_errors: int = 0
        self._escalation_count: int = 0
        self._max_escalations: int = 5
        self._iteration_in_layer: int = 0
        self._stuck_signals: list[str] = []
        self._risk_score: float = 0.0
        self._alternatives_available: bool = True
        self._transition_log: list[dict] = []

    # ── Signal Inputs (called by external components) ──────

    def signal_error(self, error_msg: str = ""):
        """An error occurred in execution. ESC may escalate to L2."""
        self._error_count += 1
        self._consecutive_errors += 1
        if self._consecutive_errors >= 1:
            self._maybe_transition(AutonomyLayer.L2_RETRY, f"Error: {error_msg[:80]}")

    def signal_recovery(self):
        """Error was recovered. ESC resets to L1."""
        self._consecutive_errors = 0
        self._maybe_transition(AutonomyLayer.L1_EXECUTE, "Error recovered")

    def signal_stuck(self, reasons: list[str]):
        """StuckDetector found the agent is stuck. ESC may escalate to L3."""
        self._stuck_signals = reasons
        if len(reasons) >= 2:  # Multi-signal confirmation
            self._maybe_transition(AutonomyLayer.L3_ADAPT, f"Stuck: {reasons[0][:80]}")

    def signal_risk(self, risk_score: float, alternatives: int):
        """PreFailureSim evaluated the plan. ESC may escalate to L4."""
        self._risk_score = risk_score
        self._alternatives_available = alternatives > 0
        if risk_score >= 0.6 and not self._alternatives_available:
            self._maybe_transition(AutonomyLayer.L4_PREDICT,
                                  f"High risk ({risk_score:.2f}), no alternatives")

    def signal_exhausted(self):
        """All strategies failed. ESC escalates to L5."""
        self._maybe_transition(AutonomyLayer.L5_CREATE,
                              "All known strategies exhausted")

    def signal_complete(self):
        """Task completed successfully. ESC resets to L1."""
        self._current_layer = AutonomyLayer.L1_EXECUTE
        self._error_count = 0
        self._consecutive_errors = 0
        self._escalation_count = 0
        self._iteration_in_layer = 0

    # ── Internal Transition Logic ─────────────────────────

    def _maybe_transition(self, target: AutonomyLayer, reason: str):
        """Transition to target layer if it's an escalation."""
        if target.value > self._current_layer.value:
            # Escalation: only go UP
            old = self._current_layer
            self._current_layer = target
            self._escalation_count += 1
            self._iteration_in_layer = 0
            entry = {
                "from": old.name, "to": target.name,
                "reason": reason, "escalation": self._escalation_count,
            }
            self._transition_log.append(entry)
            logger.warning("ESC: %s → %s (escalation #%d: %s)",
                          old.name, target.name, self._escalation_count, reason[:100])
        elif target.value < self._current_layer.value:
            # De-escalation: go DOWN (recovery)
            old = self._current_layer
            self._current_layer = target
            self._iteration_in_layer = 0
            logger.info("ESC: %s → %s (de-escalation: %s)",
                       old.name, target.name, reason[:100])

    # ── Public API ─────────────────────────────────────────

    @property
    def current_layer(self) -> AutonomyLayer:
        return self._current_layer

    @property
    def layer_name(self) -> str:
        return self._current_layer.name

    def tick(self) -> LayerAction:
        """Called each iteration. Returns what to do now."""
        self._iteration_in_layer += 1

        # Safety: max escalations
        if self._escalation_count > self._max_escalations:
            return LayerAction(
                layer=AutonomyLayer.L5_CREATE,
                action="create",
                transition_reason="Max escalations reached — creative mode only",
                escalation_count=self._escalation_count,
                current_iteration=self._iteration_in_layer,
            )

        if self._current_layer == AutonomyLayer.L1_EXECUTE:
            return LayerAction(layer=self._current_layer, action="execute",
                              escalation_count=self._escalation_count,
                              current_iteration=self._iteration_in_layer)
        elif self._current_layer == AutonomyLayer.L2_RETRY:
            return LayerAction(layer=self._current_layer, action="retry",
                              transition_reason=f"Error count: {self._error_count}",
                              escalation_count=self._escalation_count,
                              current_iteration=self._iteration_in_layer)
        elif self._current_layer == AutonomyLayer.L3_ADAPT:
            return LayerAction(layer=self._current_layer, action="learn",
                              transition_reason="; ".join(self._stuck_signals[:2]),
                              escalation_count=self._escalation_count,
                              current_iteration=self._iteration_in_layer)
        elif self._current_layer == AutonomyLayer.L4_PREDICT:
            return LayerAction(layer=self._current_layer, action="predict",
                              transition_reason=f"Risk: {self._risk_score:.2f}",
                              escalation_count=self._escalation_count,
                              current_iteration=self._iteration_in_layer)
        else:  # L5_CREATE
            return LayerAction(layer=self._current_layer, action="create",
                              transition_reason="All strategies exhausted",
                              escalation_count=self._escalation_count,
                              current_iteration=self._iteration_in_layer)

    def get_action(self) -> dict:
        """Get the current layer action as a dict for external use."""
        la = self.tick()
        return {
            "layer": la.layer.name,
            "action": la.action,
            "escalation": la.escalation_count,
            "iteration": la.current_iteration,
            "reason": la.transition_reason,
        }

    @property
    def transition_history(self) -> list[dict]:
        return list(self._transition_log)

    @property
    def is_at_max_escalation(self) -> bool:
        return self._escalation_count >= self._max_escalations


# Singleton
_esc: ExecutionStateController | None = None


def get_execution_state_controller() -> ExecutionStateController:
    global _esc
    if _esc is None:
        _esc = ExecutionStateController()
    return _esc

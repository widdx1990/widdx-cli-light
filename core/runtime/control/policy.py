"""Stabilization policy — oscillation guards, cooldowns, action caps.

Pure functions that receive a raw decision + pattern history and return
a stabilized decision. No evaluation logic, no signal parsing.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ControlAction, ControlActionType

from .types import ControlAction, ControlActionType

logger = logging.getLogger("widdx.ecp.policy")

MAX_TOTAL_CONTROL_ACTIONS = 8
ACTION_COOLDOWN_STEPS = 2
OSCILLATION_DETECTION_WINDOW = 4


def apply_stabilizers(
    decision: ControlAction,
    oscillation_pattern: list[ControlActionType],
    escalated: bool,
    total_control_actions: int,
    action_cooldown: int,
    oscillation_warning_count: int,
) -> tuple[ControlAction, list[ControlActionType], int, bool, int, int, int]:
    """Apply oscillation guard, cooldown, and action caps to a decision.

    Returns:
        (stabilized_decision, updated_pattern, updated_total_actions,
         updated_escalated, updated_cooldown, updated_warning_count, cooldown_steps_to_set)

    Stabilizers (in order):
      1. Rapid SWITCH_MODEL (2 consecutive) → force REPLAN
      2. Repeated REPLAN (2 consecutive) → force ESCALATE or ABORT
      3. Oscillation detection (4-window REPLAN↔SWITCH_MODEL) → ESCALATE or ABORT
    """
    if decision.action == ControlActionType.CONTINUE:
        return (decision, oscillation_pattern, total_control_actions,
                escalated, action_cooldown, oscillation_warning_count, 0)

    # Track the decision pattern
    pattern = list(oscillation_pattern)
    pattern.append(decision.action)
    if len(pattern) > OSCILLATION_DETECTION_WINDOW:
        pattern.pop(0)

    new_escalated = escalated
    new_warnings = oscillation_warning_count
    new_total = total_control_actions

    # ── Guard 1: Rapid SWITCH_MODEL (2 consecutive) ──
    if (len(pattern) >= 2
            and pattern[-2] == ControlActionType.SWITCH_MODEL
            and pattern[-1] == ControlActionType.SWITCH_MODEL):
        logger.warning("ECP policy: rapid SWITCH_MODEL pattern — locking to REPLAN")
        return (
            ControlAction(action=ControlActionType.REPLAN,
                          reason="Rapid model switching detected — consolidating to replan",
                          confidence=0.6),
            pattern, new_total, new_escalated, action_cooldown, new_warnings,
            ACTION_COOLDOWN_STEPS,
        )

    # ── Guard 2: Repeated REPLAN (2 consecutive) ──
    if (len(pattern) >= 2
            and pattern[-2] == ControlActionType.REPLAN
            and pattern[-1] == ControlActionType.REPLAN):
        if not new_escalated:
            new_escalated = True
            return (
                ControlAction(action=ControlActionType.ESCALATE_TO_EXPERT,
                              reason="Repeated replanning without progress — escalating",
                              confidence=0.75),
                pattern, new_total, new_escalated, action_cooldown, new_warnings,
                ACTION_COOLDOWN_STEPS,
            )
        return (
            ControlAction(action=ControlActionType.ABORT,
                          reason="Repeated replanning after escalation — aborting",
                          confidence=0.9),
            pattern, new_total, new_escalated, action_cooldown, new_warnings,
            ACTION_COOLDOWN_STEPS,
        )

    # ── Guard 3: Oscillation detection (4-window) ──
    if len(pattern) >= OSCILLATION_DETECTION_WINDOW:
        actions = pattern[-OSCILLATION_DETECTION_WINDOW:]
        is_oscillating = (
            all(a in (ControlActionType.REPLAN, ControlActionType.SWITCH_MODEL)
                for a in actions)
            and actions.count(ControlActionType.REPLAN) >= 2
            and actions.count(ControlActionType.SWITCH_MODEL) >= 2
        )
        if is_oscillating:
            new_warnings += 1
            logger.critical(
                "ECP policy: OSCILLATION REPLAN↔SWITCH_MODEL detected "
                "(warning #%d)", new_warnings,
            )
            if new_warnings >= 2:
                return (
                    ControlAction(action=ControlActionType.ABORT,
                                  reason="Oscillation loop detected twice — aborting",
                                  confidence=0.95),
                    pattern, new_total, new_escalated, action_cooldown, new_warnings,
                    ACTION_COOLDOWN_STEPS,
                )
            if not new_escalated:
                new_escalated = True
                return (
                    ControlAction(action=ControlActionType.ESCALATE_TO_EXPERT,
                                  reason="REPLAN↔SWITCH_MODEL oscillation — escalating",
                                  confidence=0.85),
                    pattern, new_total, new_escalated, action_cooldown, new_warnings,
                    ACTION_COOLDOWN_STEPS,
                )
            return (
                ControlAction(action=ControlActionType.CONTINUE, confidence=0.3),
                pattern, new_total, new_escalated, action_cooldown, new_warnings,
                ACTION_COOLDOWN_STEPS,
            )

    # No stabilizer fired — apply cooldown tracking
    new_total += 1
    return (decision, pattern, new_total, new_escalated,
            ACTION_COOLDOWN_STEPS, new_warnings, ACTION_COOLDOWN_STEPS)

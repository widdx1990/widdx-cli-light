"""Pre-Decision Memory Force — learning that actively constrains future decisions.

This module solves the critical gap: learning that happens AFTER execution
must feed back into decision weights BEFORE the next execution.

It modifies Planner, Router, and DecisionLayer weights based on:
  - Pattern success/failure history
  - Deprecated patterns (block immediately)
  - Low-confidence patterns (penalize in routing)
  - High-confidence patterns (prefer in planning)

Usage:
    from core.learning.pre_decision_force import PreDecisionForce
    pdf = PreDecisionForce()

    # Before planning:
    constraints = pdf.get_planner_constraints(task_type)
    # → {"preferred_tools": [...], "avoided_patterns": [...], "suggested_steps": [...]}

    # Before routing:
    mode_weights = pdf.get_router_weights(task_type)
    # → {"autonomous": 0.9, "expert_team": 0.3, ...}  ← modified by learning

    # Before any decision:
    blocked = pdf.get_blocked_suggestions()
    # → ["Use WebSocket directly", "Raw SQL without ORM", ...]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("widdx.pre_decision")


class PreDecisionForce:
    """Learning that actively constrains future decisions."""

    def __init__(self):
        self._blocked_patterns: set[str] = set()       # Never suggest these
        self._penalized_tools: dict[str, float] = {}    # tool → penalty multiplier
        self._preferred_patterns: dict[str, float] = {} # pattern → preference weight
        self._mode_success_rates: dict[str, dict] = {}  # task_type → {mode: success_rate}
        self._refresh()

    def _refresh(self):
        """Reload all constraints from PatternLibrary."""
        try:
            from core.learning.pattern_library import UnifiedPatternStore
            store = UnifiedPatternStore()

            # ── Block deprecated patterns ──
            all_patterns = store.local.list_all() + store.global_.list_all()
            for p in all_patterns:
                if p.status == "deprecated":
                    self._blocked_patterns.add(p.name)
                    self._blocked_patterns.add(p.solution[:60].lower())
                elif p.status == "active":
                    if p.confidence < 0.3:
                        self._penalized_tools[p.name] = p.confidence
                    elif p.confidence > 0.7:
                        self._preferred_patterns[p.name] = p.confidence

            logger.debug("PreDecisionForce refreshed: %d blocked, %d penalized, %d preferred",
                        len(self._blocked_patterns), len(self._penalized_tools),
                        len(self._preferred_patterns))
        except Exception as e:
            logger.debug("PreDecisionForce refresh failed: %s", e)

    # ── Planner Constraints ───────────────────────────────

    def get_planner_constraints(self, task_type: str = "") -> dict:
        """Return constraints that modify the Planner's step generation.

        The Planner SHOULD use these to prefer proven patterns and
        avoid deprecated/low-confidence approaches.
        """
        self._refresh()
        try:
            from core.learning.pattern_library import UnifiedPatternStore
            store = UnifiedPatternStore()

            constraints = {
                "preferred_patterns": [],
                "avoided_patterns": list(self._blocked_patterns)[:10],
                "suggested_steps": [],
            }

            # Find high-confidence planning patterns for this task type
            planning_patterns = store.search(category="planning", min_confidence=0.6, limit=5)
            for p in planning_patterns:
                constraints["preferred_patterns"].append({
                    "name": p.name,
                    "confidence": p.confidence,
                    "solution": p.solution,
                })
                # Extract step suggestions from the solution
                steps = [s.strip() for s in p.solution.split("→")]
                if len(steps) >= 2:
                    constraints["suggested_steps"].extend(steps)

            # Find debugging patterns to actively avoid
            failed_patterns = store.search(category="debugging", tags=["failure"], min_confidence=0.3, limit=5)
            for p in failed_patterns:
                if p.solution.lower() not in [a.lower() for a in constraints["avoided_patterns"]]:
                    constraints["avoided_patterns"].append(p.solution[:100])

            return constraints
        except Exception:
            return {"preferred_patterns": [], "avoided_patterns": [], "suggested_steps": []}

    # ── Router Weight Modification ─────────────────────────

    def get_router_weights(self, task_type: str = "") -> dict[str, float]:
        """Return modified mode weights based on learning history.

        Default weights are modified by pattern success rates.
        Lower weight = less likely to be chosen.
        """
        self._refresh()
        from core.uil.contract import ExecutionMode
        weights = {
            ExecutionMode.SIMPLE_CHAT.value: 1.0,
            ExecutionMode.AUTONOMOUS.value: 1.0,
            ExecutionMode.EXPERT_TEAM.value: 0.5,
            ExecutionMode.DIRECT_TOOL.value: 0.8,
        }

        try:
            from core.learning.pattern_library import UnifiedPatternStore
            store = UnifiedPatternStore()

            # Penalize modes that have high failure patterns
            for mode_key in weights:
                failure_patterns = store.search(
                    query=mode_key, tags=["failure"], min_confidence=0.3, limit=5,
                )
                if failure_patterns:
                    # Each failure reduces mode weight by 10%
                    penalty = min(0.5, len(failure_patterns) * 0.1)
                    weights[mode_key] = max(0.1, weights[mode_key] - penalty)
                    logger.debug("Router weight: %s penalized from %.1f to %.1f (%d failures)",
                                mode_key, weights[mode_key] + penalty, weights[mode_key],
                                len(failure_patterns))

            # Boost modes with high success patterns
            for mode_key in weights:
                success_patterns = store.search(
                    query=mode_key, tags=["success"], min_confidence=0.6, limit=5,
                )
                if success_patterns:
                    boost = min(0.3, len(success_patterns) * 0.05)
                    weights[mode_key] = min(1.0, weights[mode_key] + boost)

        except Exception:
            pass

        return weights

    # ── DecisionLayer Blocking ─────────────────────────────

    def is_suggestion_blocked(self, suggestion: str) -> tuple[bool, str]:
        """Check if a suggestion should be blocked based on learning.

        Returns (blocked: bool, reason: str).
        """
        self._refresh()
        s = suggestion.lower()

        for blocked in self._blocked_patterns:
            if blocked.lower() in s or s in blocked.lower():
                return True, f"Pattern '{blocked}' was deprecated — blocked by PreDecisionForce"

        for penalized, confidence in self._penalized_tools.items():
            if penalized.lower() in s and confidence < 0.3:
                return True, f"Pattern '{penalized}' has low confidence ({confidence:.2f})"

        return False, ""

    def get_blocked_suggestions(self) -> list[str]:
        """Return all suggestions that should never be made."""
        self._refresh()
        return list(self._blocked_patterns)

    # ── Expert Selection ───────────────────────────────────

    def get_preferred_experts(self) -> list[str]:
        """Return experts with proven success, ordered by preference."""
        self._refresh()
        try:
            from core.learning.pattern_library import UnifiedPatternStore
            store = UnifiedPatternStore()
            expert_patterns = store.search(category="architectural", tags=["success"], min_confidence=0.6, limit=10)
            preferred = []
            for p in expert_patterns:
                if "orchestrator" in p.solution.lower(): preferred.append("orchestrator")
                if "coder" in p.solution.lower(): preferred.append("coder")
                if "reviewer" in p.solution.lower(): preferred.append("reviewer")
                if "researcher" in p.solution.lower(): preferred.append("researcher")
                if "debugger" in p.solution.lower(): preferred.append("debugger")
            return list(dict.fromkeys(preferred))  # unique, preserve order
        except Exception:
            return []


# Singleton
_pdf: PreDecisionForce | None = None


def get_pre_decision_force() -> PreDecisionForce:
    global _pdf
    if _pdf is None:
        _pdf = PreDecisionForce()
    return _pdf

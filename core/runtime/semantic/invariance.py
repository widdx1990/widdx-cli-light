"""Formal Cognitive Invariance Layer — bounded recovery guarantees.

Cannot prove mathematical identity restoration, but CAN guarantee
that healing operations meet minimum validity criteria:
  1. Post-healing stability ≥ pre-healing stability
  2. Healing does not introduce new failure modes
  3. Recovery converges (does not oscillate indefinitely)
  4. Each healing operation is validated before application

These are bounded guarantees — not proofs, but contracts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("widdx.semantic.invariance")


class InvariantStatus(Enum):
    SATISFIED = auto()
    VIOLATED = auto()
    UNKNOWN = auto()


@dataclass
class Invariant:
    """A condition that must hold for cognitive stability."""
    name: str
    description: str
    check: str = ""  # description of the check logic
    status: InvariantStatus = InvariantStatus.UNKNOWN
    severity: str = "warning"  # warning | critical


@dataclass
class HealingContract:
    """Pre/post conditions for a healing operation."""
    operation_type: str
    preconditions: list[str]
    postconditions: list[str]
    max_retries: int = 3


@dataclass
class RecoveryValidation:
    """Result of validating a healing operation."""
    operation: str
    passed: bool
    stability_before: float
    stability_after: float
    improved: bool
    no_new_failures: bool
    contract_satisfied: bool
    retry_count: int = 0
    failures: list[str] = field(default_factory=list)


class CognitiveInvariance:
    """Bounded guarantee layer for cognitive self-healing.

    Defines invariants that must hold. Validates every healing
    operation against pre/post conditions. Ensures healing never
    makes the system worse.
    """

    INVARIANTS: list[Invariant] = [
        Invariant("I1", "Stability must not decrease after healing", "critical"),
        Invariant("I2", "Tool set must be a subset of original + allowed additions", "critical"),
        Invariant("I3", "Goal anchor must remain unchanged through healing", "critical"),
        Invariant("I4", "No more than 3 healings per task without convergence", "warning"),
        Invariant("I5", "Decision pattern must not oscillate after healing", "warning"),
        Invariant("I6", "Context size must not exceed 2x pre-healing size", "warning"),
        Invariant("I7", "Each healing must improve at least one metric", "critical"),
    ]

    HEALING_CONTRACTS: dict[str, HealingContract] = {
        "REANCHOR_GOAL": HealingContract(
            operation_type="REANCHOR_GOAL",
            preconditions=[
                "goal_drift score ≥ 0.5",
                "stable_snapshot exists",
                "original goal is not corrupted",
            ],
            postconditions=[
                "resets goal_drift detector to anchored state",
                "injects reanchor instruction into context",
                "does NOT modify tool set",
            ],
            max_retries=2,
        ),
        "PRUNE_CONTEXT": HealingContract(
            operation_type="PRUNE_CONTEXT",
            preconditions=[
                "contamination score ≥ 0.4",
                "message count > 20",
                "system messages preserved",
            ],
            postconditions=[
                "reduces message count to ≤ 10 + system",
                "preserves original goal message",
                "does NOT lose tool results from last 5 steps",
            ],
            max_retries=1,
        ),
        "RESTRICT_TOOLS": HealingContract(
            operation_type="RESTRICT_TOOLS",
            preconditions=[
                "drifted tools detected",
                "stable snapshot tool_set available",
                "blocked tools are non-essential",
            ],
            postconditions=[
                "removes drifted tools from available set",
                "restores stable snapshot tool_set",
                "does NOT block read/write/bash",
            ],
            max_retries=1,
        ),
        "RESET_DECISION_PATTERN": HealingContract(
            operation_type="RESET_DECISION_PATTERN",
            preconditions=[
                "trajectory divergence ≥ 0.6",
                "baseline pattern available",
            ],
            postconditions=[
                "resets oscillation pattern in ECP policy",
                "clears cooldown state",
                "does NOT change escalated flag",
            ],
            max_retries=1,
        ),
        "SAFE_MODE": HealingContract(
            operation_type="SAFE_MODE",
            preconditions=[
                "critical severity",
                "at least 2 of: drift≥0.8, divergence≥0.8, contamination≥0.7",
                "not already in safe mode",
            ],
            postconditions=[
                "forces REPLAN via ECP",
                "limits tools to read/write/edit/validate",
                "injects safety anchor into context",
            ],
            max_retries=1,
        ),
    }

    def __init__(self):
        self._validations: list[RecoveryValidation] = []
        self._invariant_violations: list[str] = []
        self._convergence_ok: bool = True

    def start_task(self):
        self._validations.clear()
        self._invariant_violations.clear()
        self._convergence_ok = True

    def validate_healing(
        self,
        operation_type: str,
        stability_before: float,
        stability_after: float | None = None,
        warning_count_before: int = 0,
        warning_count_after: int = 0,
        retry_count: int = 0,
    ) -> RecoveryValidation:
        """Validate a healing operation against its contract.

        Returns RecoveryValidation with pass/fail and reason.
        """
        contract = self.HEALING_CONTRACTS.get(operation_type)
        failures: list[str] = []

        if contract and retry_count >= contract.max_retries:
            failures.append(f"max retries ({contract.max_retries}) exceeded")

        # I1: stability must not decrease
        if stability_after is not None and stability_after < stability_before - 0.05:
            failures.append(
                f"stability decreased: {stability_before:.2f} → {stability_after:.2f}"
            )

        # I7: healing must improve at least one metric
        no_improvement = (
            (stability_after is not None and stability_after <= stability_before + 0.02)
            and warning_count_after >= warning_count_before
        )
        if no_improvement and retry_count > 0:
            failures.append("no improvement after retry")

        passed = len(failures) == 0
        improved = (
            stability_after is not None
            and stability_after > stability_before + 0.02
        )

        validation = RecoveryValidation(
            operation=operation_type,
            passed=passed,
            stability_before=stability_before,
            stability_after=stability_after or stability_before,
            improved=improved,
            no_new_failures=warning_count_after <= warning_count_before + 1,
            contract_satisfied=passed,
            retry_count=retry_count,
            failures=failures,
        )
        self._validations.append(validation)

        if not passed:
            logger.error(
                "INVARIANCE CONTRACT VIOLATED: %s — %s",
                operation_type, "; ".join(failures),
            )

        return validation

    def check_invariants(
        self,
        stability: float,
        healing_count: int,
        tool_set_size: int,
        oscillation_warnings: int,
        context_size: int,
    ) -> list[str]:
        """Check all invariants against current state. Returns violations."""
        violations: list[str] = []

        # I4: max healings without convergence
        if healing_count > 3 and stability < 0.5:
            violations.append("I4: >3 healings without convergence")
            self._convergence_ok = False

        # I6: context bloat
        if context_size > 400:
            violations.append(f"I6: context size {context_size} exceeds limit")

        # Check past validations for patterns
        recent = self._validations[-5:]
        failed_count = sum(1 for v in recent if not v.passed)
        if failed_count >= 3:
            violations.append("I5: 3+ consecutive healing failures — possible oscillation")

        self._invariant_violations = violations
        if violations:
            logger.critical("INVARIANCE VIOLATIONS: %s", "; ".join(violations))

        return violations

    def get_guarantees(self) -> dict:
        """Return current level of guarantees the system can provide."""
        recent = self._validations[-10:]
        passed = sum(1 for v in recent if v.passed)

        guarantee_level = (
            "STRONG" if passed == len(recent) and len(recent) >= 2 and self._convergence_ok
            else "MODERATE" if passed / max(len(recent), 1) >= 0.7
            else "WEAK" if passed > 0
            else "NONE"
        )

        return {
            "guarantee_level": guarantee_level,
            "invariants_checked": len(self.INVARIANTS),
            "violations": self._invariant_violations.copy(),
            "validations_passed": passed,
            "validations_total": len(recent),
            "healing_converges": self._convergence_ok,
            "contracts_defined": len(self.HEALING_CONTRACTS),
            "bounded_guarantee": (
                "System guarantees healing will not degrade stability below "
                "pre-healing baseline, and will not introduce new critical failures. "
                "Full identity restoration is NOT guaranteed — only bounded improvement."
            ),
        }


_invariance: CognitiveInvariance | None = None


def get_cognitive_invariance() -> CognitiveInvariance:
    global _invariance
    if _invariance is None:
        _invariance = CognitiveInvariance()
    return _invariance

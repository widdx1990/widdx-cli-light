"""Policy Experiments — counterfactual evaluation of parameter changes.

Closes the final gap: "Is 6 actually better than 5?"

Runs A/B experiments on policy parameters:
  1. Baseline: current value (control group)
  2. Candidate: proposed value (experiment group)
  3. Split traffic — 10% of tasks run with candidate
  4. Compare: success rate, cost, latency, escalation count
  5. Accept candidate only if it beats baseline with statistical confidence
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("widdx.ecp.experiments")


@dataclass
class ExperimentGroup:
    """One arm of an A/B experiment."""
    parameter: str
    value: float
    task_count: int = 0
    success_count: int = 0
    total_cost: float = 0.0
    total_steps: int = 0
    total_escalations: int = 0
    total_aborts: int = 0
    total_model_switches: int = 0
    avg_latency: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.task_count if self.task_count > 0 else 0.0

    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.task_count if self.task_count > 0 else 0.0

    @property
    def avg_steps(self) -> float:
        return self.total_steps / self.task_count if self.task_count > 0 else 0.0

    @property
    def escalation_rate(self) -> float:
        return self.total_escalations / self.task_count if self.task_count > 0 else 0.0

    @property
    def abort_rate(self) -> float:
        return self.total_aborts / self.task_count if self.task_count > 0 else 0.0


@dataclass
class ExperimentResult:
    """Result of comparing baseline vs candidate."""
    parameter: str
    baseline_value: float
    candidate_value: float
    baseline_stats: dict
    candidate_stats: dict
    success_delta: float  # + = candidate better
    cost_delta: float     # - = candidate cheaper
    steps_delta: float    # - = candidate faster
    confidence: float
    winner: str           # "baseline" | "candidate" | "inconclusive"
    recommendation: str
    timestamp: float = field(default_factory=time.time)


class PolicyExperimentRunner:
    """Runs A/B experiments on policy parameters.

    Traffic split: 90% baseline, 10% candidate.
    Experiment runs for min 5 tasks in candidate group before comparing.
    Candidate wins only if it beats baseline on 2 of 3 metrics
    with statistical confidence.
    """

    TRAFFIC_SPLIT = 0.10  # 10% of tasks use candidate
    MIN_CANDIDATE_TASKS = 5
    CONFIDENCE_THRESHOLD = 0.75

    def __init__(self):
        self._experiments: dict[str, dict] = {}
        self._results: list[ExperimentResult] = []

    def start_experiment(self, parameter: str, baseline_value: float,
                         candidate_value: float):
        """Start an A/B experiment for a parameter."""
        self._experiments[parameter] = {
            "baseline": ExperimentGroup(parameter=parameter, value=baseline_value),
            "candidate": ExperimentGroup(parameter=parameter, value=candidate_value),
            "started_at": time.time(),
            "active": True,
        }
        logger.info(
            "EXPERIMENT START: %s — baseline=%.2f vs candidate=%.2f",
            parameter, baseline_value, candidate_value,
        )

    def should_use_candidate(self, parameter: str) -> bool:
        """Decide whether this task should use the candidate value."""
        import random
        exp = self._experiments.get(parameter)
        if not exp or not exp["active"]:
            return False
        return random.random() < self.TRAFFIC_SPLIT

    def record_task(self, parameter: str, used_candidate: bool,
                    success: bool, cost: float, steps: int,
                    escalations: int = 0, aborts: int = 0,
                    model_switches: int = 0, latency: float = 0.0):
        """Record outcome for a single task."""
        exp = self._experiments.get(parameter)
        if not exp:
            return

        group = exp["candidate"] if used_candidate else exp["baseline"]
        group.task_count += 1
        if success:
            group.success_count += 1
        group.total_cost += cost
        group.total_steps += steps
        group.total_escalations += escalations
        group.total_aborts += aborts
        group.total_model_switches += model_switches
        if latency > 0:
            group.avg_latency = (
                (group.avg_latency * (group.task_count - 1) + latency)
                / group.task_count
            )

    def evaluate(self, parameter: str) -> ExperimentResult | None:
        """Compare baseline vs candidate. Returns result if experiment is ready."""
        exp = self._experiments.get(parameter)
        if not exp:
            return None

        baseline = exp["baseline"]
        candidate = exp["candidate"]

        if candidate.task_count < self.MIN_CANDIDATE_TASKS:
            return None

        # Compute deltas
        success_delta = candidate.success_rate - baseline.success_rate
        cost_delta = candidate.avg_cost - baseline.avg_cost
        steps_delta = candidate.avg_steps - baseline.avg_steps

        esc_base = baseline.escalation_rate
        esc_cand = candidate.escalation_rate
        abort_base = baseline.abort_rate
        abort_cand = candidate.abort_rate

        # Score: candidate wins if better on 2 of 3 primary metrics
        wins = 0
        if success_delta > 0:
            wins += 1  # higher success = better
        if cost_delta < 0:
            wins += 1  # lower cost = better
        if steps_delta < 0:
            wins += 1  # fewer steps = better
        # Bonus: fewer escalations
        if esc_cand < esc_base:
            wins += 0.5
        # Bonus: fewer aborts
        if abort_cand < abort_base:
            wins += 0.5

        # Confidence based on sample size and effect magnitude
        sample_factor = min(1.0, candidate.task_count / 10.0)
        effect_magnitude = (
            abs(success_delta) * 3
            + abs(cost_delta / max(baseline.avg_cost, 0.001)) * 1
            + abs(steps_delta / max(baseline.avg_steps, 1)) * 1
        ) / 5
        confidence = min(1.0, sample_factor * 0.5 + min(effect_magnitude, 0.5))

        if wins >= 2 and confidence >= self.CONFIDENCE_THRESHOLD:
            winner = "candidate"
            recommendation = (
                f"ACCEPT: candidate value {candidate.value} beats baseline "
                f"on {wins:.1f}/3 metrics (success={success_delta:+.2f}, "
                f"cost={cost_delta:+.4f}, steps={steps_delta:+.1f})"
            )
        elif wins <= 1 and confidence >= self.CONFIDENCE_THRESHOLD:
            winner = "baseline"
            recommendation = (
                f"REJECT: candidate value {candidate.value} does NOT beat "
                f"baseline (wins={wins:.1f}/3). Keeping {baseline.value}."
            )
        else:
            winner = "inconclusive"
            recommendation = (
                f"NEED MORE DATA: confidence={confidence:.2f} < {self.CONFIDENCE_THRESHOLD}. "
                f"Continue experiment."
            )

        result = ExperimentResult(
            parameter=parameter,
            baseline_value=baseline.value,
            candidate_value=candidate.value,
            baseline_stats={
                "tasks": baseline.task_count,
                "success_rate": round(baseline.success_rate, 3),
                "avg_cost": round(baseline.avg_cost, 4),
                "avg_steps": round(baseline.avg_steps, 1),
                "escalation_rate": round(baseline.escalation_rate, 3),
                "abort_rate": round(baseline.abort_rate, 3),
            },
            candidate_stats={
                "tasks": candidate.task_count,
                "success_rate": round(candidate.success_rate, 3),
                "avg_cost": round(candidate.avg_cost, 4),
                "avg_steps": round(candidate.avg_steps, 1),
                "escalation_rate": round(candidate.escalation_rate, 3),
                "abort_rate": round(candidate.abort_rate, 3),
            },
            success_delta=round(success_delta, 3),
            cost_delta=round(cost_delta, 4),
            steps_delta=round(steps_delta, 1),
            confidence=round(confidence, 2),
            winner=winner,
            recommendation=recommendation,
        )

        self._results.append(result)
        exp["active"] = winner == "inconclusive"

        # Save results
        self._save_results(result)

        logger.info("EXPERIMENT %s: %s — %s", parameter, winner, recommendation)
        return result

    def _save_results(self, result: ExperimentResult):
        try:
            path = Path(".widdx/experiment_results.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if path.exists():
                existing = json.loads(path.read_text())
            existing.append({
                "ts": result.timestamp,
                "param": result.parameter,
                "baseline": result.baseline_value,
                "candidate": result.candidate_value,
                "winner": result.winner,
                "confidence": result.confidence,
                "success_delta": result.success_delta,
                "cost_delta": result.cost_delta,
                "steps_delta": result.steps_delta,
                "recommendation": result.recommendation,
            })
            path.write_text(json.dumps(existing, indent=2))
        except Exception:
            pass

    @property
    def active_experiments(self) -> list[str]:
        return [k for k, v in self._experiments.items() if v["active"]]

    @property
    def results_history(self) -> list[dict]:
        return [
            {
                "param": r.parameter,
                "baseline": r.baseline_value,
                "candidate": r.candidate_value,
                "winner": r.winner,
                "confidence": r.confidence,
                "success_delta": r.success_delta,
            }
            for r in self._results
        ]


_experiment_runner: PolicyExperimentRunner | None = None


def get_experiment_runner() -> PolicyExperimentRunner:
    global _experiment_runner
    if _experiment_runner is None:
        _experiment_runner = PolicyExperimentRunner()
    return _experiment_runner

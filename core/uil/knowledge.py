"""Knowledge — Execution Record Keeper.

In-memory store for execution outcomes.
Phase 2 foundation — pure Python stdlib, no LLM, no MCP, no external deps.
"""

import time
import statistics
from dataclasses import dataclass
from typing import Any, Optional

from .contract import ExecutionMode


# -------------------------------------------------------------------
# Execution Record
# -------------------------------------------------------------------

@dataclass
class ExecutionRecord:
    """Immutable record of a single execution outcome."""
    task_type: str
    execution_mode: str
    steps_planned: int
    steps_completed: int
    execution_time: float
    success: bool
    timestamp: float
    steps_failed: int = 0


# -------------------------------------------------------------------
# Knowledge Base
# -------------------------------------------------------------------

class KnowledgeBase:
    """In-memory execution knowledge store.

    Indexes records by task_type.value for O(1) lookup.
    Pure dict-based — no database, no LLM, no external storage.
    Phase 2 will add persistent storage and semantic indexing.
    """

    def __init__(self):
        self._records: dict[str, list[ExecutionRecord]] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, classification: Any, result: Any,
               decision: Any) -> None:
        """Store an execution outcome.

        Extracts structured data from ClassificationResult, ExecutionResult,
        and RoutingDecision without touching internal contracts.

        Args:
            classification: ClassificationResult with task_type, domain.
            result: ExecutionResult with mode, steps, success, time.
            decision: RoutingDecision with plan.mode.
        """
        record = ExecutionRecord(
            task_type=classification.task_type.value,
            execution_mode=result.mode.value if result.mode else "",
            steps_planned=result.steps_planned,
            steps_completed=result.steps_completed,
            steps_failed=result.steps_failed,
            execution_time=result.execution_time,
            success=result.success,
            timestamp=time.time(),
        )

        key = record.task_type
        if key not in self._records:
            self._records[key] = []
        self._records[key].append(record)

    # ------------------------------------------------------------------
    # Read — Similar Records
    # ------------------------------------------------------------------

    def get_similar(self, task_type: str) -> list[ExecutionRecord]:
        """Return all records with the same task type.

        Args:
            task_type: Value string from TaskType enum (e.g. "code_write").

        Returns:
            List of matching ExecutionRecord objects, oldest first.
            Empty list if no records exist for this type.
        """
        return list(self._records.get(task_type, []))

    # ------------------------------------------------------------------
    # Read — Performance Statistics
    # ------------------------------------------------------------------

    def get_stats(self, task_type: str) -> dict[str, Any]:
        """Compute aggregate performance statistics for a task type.

        Args:
            task_type: Value string from TaskType enum.

        Returns:
            Dict with keys:
              - count: int — number of records
              - avg_execution_time: float | None
              - min_time: float | None
              - max_time: float | None
              - success_rate: float | None (0.0-1.0)
              - avg_steps_planned: float | None
              - avg_steps_completed: float | None
        """
        records = self._records.get(task_type, [])
        if not records:
            return {
                "count": 0,
                "avg_execution_time": None,
                "min_time": None,
                "max_time": None,
                "success_rate": None,
                "avg_steps_planned": None,
                "avg_steps_completed": None,
            }

        times = [r.execution_time for r in records]
        successes = [1 if r.success else 0 for r in records]
        planned = [r.steps_planned for r in records]
        completed = [r.steps_completed for r in records]

        return {
            "count": len(records),
            "avg_execution_time": round(statistics.mean(times), 4),
            "min_time": min(times),
            "max_time": max(times),
            "success_rate": round(statistics.mean(successes), 4),
            "avg_steps_planned": round(statistics.mean(planned), 2),
            "avg_steps_completed": round(statistics.mean(completed), 2),
        }

    # ------------------------------------------------------------------
    # Read — Knowledge-Informed Routing
    # ------------------------------------------------------------------

    def suggest_mode(self, task_type: str) -> Optional[ExecutionMode]:
        """Suggest an ExecutionMode override based on historical stats.

        Args:
            task_type: Value string from TaskType enum (e.g. "code_write").

        Returns:
            ExecutionMode override or None if:
              - fewer than 3 records (insufficient data)
              - historical success rate is acceptable
              - no performance degradation detected
        """
        stats = self.get_stats(task_type)
        if stats["count"] < 3:
            return None

        # Condition 1: Low success rate → escalate to ExpertTeam
        if stats["success_rate"] < 0.5:
            return ExecutionMode.EXPERT_TEAM

        # Condition 2: Slow + incomplete → downgrade to more
        # autonomous (single-agent, cheaper retry)
        avg_time = stats["avg_execution_time"]
        avg_planned = stats["avg_steps_planned"]
        avg_completed = stats["avg_steps_completed"]
        if (avg_time is not None and avg_time > 30.0
                and avg_planned is not None
                and avg_completed is not None
                and avg_completed < avg_planned):
            return ExecutionMode.AUTONOMOUS

        return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def total_records(self) -> int:
        """Total number of records across all task types."""
        return sum(len(v) for v in self._records.values())

    @property
    def task_types(self) -> list[str]:
        """List of task types that have records."""
        return list(self._records.keys())

    def clear(self) -> None:
        """Reset all records (for testing)."""
        self._records.clear()

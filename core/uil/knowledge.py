"""Knowledge — Execution Record Keeper with persistence.

Phase 2.3: Persistent KnowledgeBase that saves/loads from .widdx/knowledge.json.
Provides historical execution stats for knowledge-informed routing.
"""

import json, time, statistics
from dataclasses import dataclass, asdict
from pathlib import Path
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
    tools_used: list[str] | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionRecord":
        return cls(**d)


# -------------------------------------------------------------------
# Knowledge Base
# -------------------------------------------------------------------

class KnowledgeBase:
    """Persistent execution knowledge store.

    Indexes records by task_type.value for O(1) lookup.
    Persists to .widdx/knowledge.json in the project directory.
    """

    def __init__(self, project_dir: str | Path | None = None):
        self._records: dict[str, list[ExecutionRecord]] = {}
        self._dirty: bool = False
        self._project_dir = Path(project_dir).resolve() if project_dir else Path.cwd().resolve()
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _get_path(self) -> Path:
        """Path to the knowledge store file."""
        return self._project_dir / ".widdx" / "knowledge.json"

    def _load(self):
        """Load records from disk."""
        path = self._get_path()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for task_type, records_raw in raw.items():
                self._records[task_type] = [
                    ExecutionRecord.from_dict(r) for r in records_raw
                ]
        except Exception:
            self._records = {}

    def _save(self):
        """Persist records to disk."""
        path = self._get_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = {}
            for task_type, records in self._records.items():
                raw[task_type] = [r.to_dict() for r in records]
            path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
            self._dirty = False
        except Exception:
            pass  # non-critical

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, classification: Any, result: Any,
               decision: Any) -> None:
        """Store an execution outcome and persist to disk."""
        record = ExecutionRecord(
            task_type=classification.task_type.value if hasattr(classification, 'task_type') else str(classification),
            execution_mode=result.mode.value if hasattr(result, 'mode') and result.mode else "",
            steps_planned=result.steps_planned if hasattr(result, 'steps_planned') else 0,
            steps_completed=result.steps_completed if hasattr(result, 'steps_completed') else 0,
            steps_failed=result.steps_failed if hasattr(result, 'steps_failed') else 0,
            execution_time=result.execution_time if hasattr(result, 'execution_time') else 0.0,
            success=result.success if hasattr(result, 'success') else False,
            timestamp=time.time(),
            tools_used=list(result.tools_used) if hasattr(result, 'tools_used') and result.tools_used else None,
        )

        key = record.task_type
        if key not in self._records:
            self._records[key] = []
        self._records[key].append(record)
        self._dirty = True

        # Auto-save every 3 records or always (simple approach: save every time)
        self._save()

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
              - fewer than 2 records (insufficient data)
              - historical success rate is acceptable
              - no performance degradation detected
        """
        stats = self.get_stats(task_type)
        if stats["count"] < 2:  # lowered from 3 to 2 for practical use
            return None

        # Condition 1: Low success rate → escalate to ExpertTeam
        if stats["success_rate"] is not None and stats["success_rate"] < 0.5:
            return ExecutionMode.EXPERT_TEAM

        # Condition 2: Slow + incomplete → more autonomous
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
        """Reset all records and delete the persisted file."""
        self._records.clear()
        path = self._get_path()
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

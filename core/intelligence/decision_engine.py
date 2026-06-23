"""Learning decision tree for routing — upgrades router.py from static to adaptive.

The DecisionEngine learns from execution history (knowledge.json):
- Which execution mode succeeded best for which task type + features?
- If AUTONOMOUS failed 3x for database tasks → learn to use DIRECT_TOOL
- If EXPERT_TEAM succeeded for complex web apps → prefer it next time

Decision tree is persisted to .widdx/decisions.json and updated after each execution.
Pure Python — zero LLM calls, zero network I/O.
"""

from __future__ import annotations
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("widdx.intelligence.decision")


@dataclass
class DecisionStats:
    """Statistics for a specific (task_type, mode) combination."""
    task_type: str
    mode: str
    successes: int = 0
    failures: int = 0
    total_quality: float = 0.0  # sum of quality scores
    last_used: str = ""  # ISO timestamp

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.successes / self.total

    @property
    def avg_quality(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_quality / self.total


# Default mode mapping (mirrors router.py static table)
DEFAULT_MODE_MAP: dict[str, str] = {
    "chat": "simple_chat",
    "code_read": "simple_chat",
    "file_ops": "simple_chat",
    "code_write": "autonomous",
    "code_modify": "autonomous",
    "code_review": "autonomous",
    "browser": "autonomous",
    "database": "autonomous",
    "research": "autonomous",
    "reasoning": "autonomous",
    "complex": "expert_team",
    "system": "direct_tool",
    "unknown": "simple_chat",
}


class DecisionEngine:
    """Learned decision tree for task routing.

    Routes (task_type, features, complexity) → best execution mode.
    Learns from execution history: if AUTONOMOUS keeps failing
    for a task type, it promotes SIMPLE_CHAT or DIRECT_TOOL.
    """

    def __init__(self, knowledge_path: Path | str = None):
        """Initialize decision engine.

        Args:
            knowledge_path: Path to knowledge.json for learning.
                           If not provided, uses default static mapping.
        """
        self._knowledge_path = Path(knowledge_path) if knowledge_path else None
        self._stats: dict[str, DecisionStats] = {}
        self._overrides: dict[str, str] = {}  # learned mode overrides
        self._load()

    def _load(self):
        """Load learned decisions from disk."""
        if not self._knowledge_path:
            return
        decisions_path = self._knowledge_path.parent / "decisions.json"
        if not decisions_path.exists():
            return
        try:
            data = json.loads(decisions_path.read_text(encoding="utf-8"))
            for key, override in data.get("overrides", {}).items():
                self._overrides[key] = override
            for key, stats_dict in data.get("stats", {}).items():
                self._stats[key] = DecisionStats(**stats_dict)
            logger.debug("Loaded %d overrides, %d stat entries",
                         len(self._overrides), len(self._stats))
        except (json.JSONDecodeError, OSError, TypeError) as e:
            logger.warning("Failed to load decisions: %s", e)

    def _save(self):
        """Persist learned decisions to disk."""
        if not self._knowledge_path:
            return
        decisions_path = self._knowledge_path.parent / "decisions.json"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "overrides": self._overrides,
            "stats": {k: {
                "task_type": v.task_type,
                "mode": v.mode,
                "successes": v.successes,
                "failures": v.failures,
                "total_quality": v.total_quality,
                "last_used": v.last_used,
            } for k, v in self._stats.items()},
        }
        decisions_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def route(self, task_type: str, features: list[str] = None,
              confidence: float = 0.5, complexity: int = 1) -> str:
        """Route a task to the best execution mode.

        Args:
            task_type: Task type string ('code_write', 'research', etc.)
            features: Detected features like ['api', 'database', 'web']
            confidence: Classification confidence (0.0-1.0)
            complexity: Task complexity (1=simple, 2=medium, 3=complex)

        Returns:
            Execution mode string: 'simple_chat', 'autonomous',
            'expert_team', or 'direct_tool'
        """
        features = features or []

        # ── Low confidence → always simple_chat (safety) ──
        if confidence < 0.4:
            return "simple_chat"

        # ── Check learned overrides ──
        feature_key = self._make_key(task_type, features, complexity)
        if feature_key in self._overrides:
            learned_mode = self._overrides[feature_key]
            logger.debug("Learned override: %s → %s", feature_key, learned_mode)
            return learned_mode

        # ── Check stats for best performing mode ──
        best_mode = self._best_mode_by_stats(task_type, features)
        if best_mode and confidence >= 0.5:
            return best_mode

        # ── Fallback to default static mapping ──
        return DEFAULT_MODE_MAP.get(task_type, "simple_chat")

    def _make_key(self, task_type: str, features: list[str], complexity: int) -> str:
        """Create a stable key for this task profile."""
        feat_str = "+".join(sorted(features)) if features else "none"
        return f"{task_type}:{feat_str}:c{complexity}"

    def _best_mode_by_stats(self, task_type: str, features: list[str]) -> str | None:
        """Find the statistically best mode for this task profile."""
        candidates: list[tuple[float, str]] = []

        for key, stats in self._stats.items():
            if stats.task_type != task_type:
                continue
            if stats.total < 3:
                continue  # not enough data
            # Weight: success_rate * 0.6 + avg_quality * 0.4
            score = stats.success_rate * 0.6 + stats.avg_quality * 0.4
            candidates.append((score, stats.mode))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_mode = candidates[0]

        # Only override if the best mode is significantly better than default
        default_mode = DEFAULT_MODE_MAP.get(task_type, "simple_chat")
        if best_mode != default_mode and best_score >= 0.5:
            return best_mode
        return None

    def record(self, task_type: str, mode: str, features: list[str],
               success: bool, quality_score: float = 0.0,
               complexity: int = 1):
        """Record an execution outcome for learning.

        Args:
            task_type: Task type that was used
            mode: Execution mode that was used
            features: Task features
            success: Whether the execution succeeded
            quality_score: Quality score from validation (0.0-1.0)
            complexity: Task complexity level
        """
        from datetime import datetime, timezone

        key = self._make_key(task_type, features, complexity)
        if key not in self._stats:
            self._stats[key] = DecisionStats(
                task_type=task_type, mode=mode,
            )

        stats = self._stats[key]
        if success:
            stats.successes += 1
        else:
            stats.failures += 1
        stats.total_quality += quality_score
        stats.last_used = datetime.now(timezone.utc).isoformat()

        # ── Automatically learn from failures ──
        if stats.failures >= 3 and stats.success_rate < 0.4:
            # This mode is failing too much → try alternatives
            alternatives = {
                "expert_team": "autonomous",
                "autonomous": "simple_chat",
            }
            if mode in alternatives:
                new_mode = alternatives[mode]
                self._overrides[key] = new_mode
                logger.info(
                    "Learned: %s (mode=%s) failed %d/%d times → "
                    "downgrading to %s",
                    key, mode, stats.failures, stats.total, new_mode,
                )

        # ── Promote good alternatives ──
        if stats.successes >= 5 and stats.success_rate >= 0.8:
            # This mode is working well → could try escalating
            escalations = {
                "simple_chat": "autonomous",
            }
            if mode in escalations and key not in self._overrides:
                # Don't auto-escalate; just remove any downgrade override
                if self._overrides.get(key) == "simple_chat":
                    del self._overrides[key]
                    logger.info("Unblocked: %s → restoring default routing", key)

        self._save()

    def get_stats(self, task_type: str = None) -> dict[str, DecisionStats]:
        """Get decision statistics, optionally filtered by task_type."""
        if task_type:
            return {k: v for k, v in self._stats.items()
                    if v.task_type == task_type}
        return dict(self._stats)

    def reset(self):
        """Clear all learned decisions. Start fresh."""
        self._stats.clear()
        self._overrides.clear()
        self._save()


# Module-level singleton
_engine: DecisionEngine | None = None


def get_decision_engine(knowledge_path: Path | str = None) -> DecisionEngine:
    """Get or create the decision engine."""
    global _engine
    if _engine is None:
        _engine = DecisionEngine(knowledge_path)
    return _engine

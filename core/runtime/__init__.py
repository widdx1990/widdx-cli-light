"""Runtime Execution Control Plane + Semantic Stability — continuous adaptive execution.

Architecture (5 layers):
  control/types.py              — data structures
  control/evaluation.py         — signal-to-action engine
  control/policy.py             — stabilization guards
  control/execution_plane.py    — thin orchestrator
  benchmarks/tracer.py          — decision tracing
  benchmarks/scorer.py          — performance grading
  semantic/monitor.py           — cognitive stability measurement
  semantic/state_snapshot.py    — identity snapshots
  semantic/rollback.py          — semantic restoration
  semantic/healer.py            — self-healing orchestration
"""

from .execution_control_plane import (
    ExecutionControlPlane, ControlAction, ControlActionType,
    ExecutionSignal, SignalType, get_control_plane,
    evaluate_signals, apply_stabilizers,
)
from .benchmarks import (
    DecisionTracer, DecisionTrace, get_tracer,
    score_session, BenchmarkScore,
)
from .semantic import (
    SemanticStabilityMonitor, SemanticStabilityReport, get_semantic_monitor,
    StateSnapshotManager, CognitiveSnapshot, get_snapshot_manager,
    SemanticRollback, get_semantic_rollback,
    SelfHealingMonitor, get_self_healing_monitor,
)

__all__ = [
    "ExecutionControlPlane", "ControlAction", "ControlActionType",
    "ExecutionSignal", "SignalType", "get_control_plane",
    "evaluate_signals", "apply_stabilizers",
    "DecisionTracer", "DecisionTrace", "get_tracer",
    "score_session", "BenchmarkScore",
    "SemanticStabilityMonitor", "SemanticStabilityReport", "get_semantic_monitor",
    "StateSnapshotManager", "CognitiveSnapshot", "get_snapshot_manager",
    "SemanticRollback", "get_semantic_rollback",
    "SelfHealingMonitor", "get_self_healing_monitor",
]

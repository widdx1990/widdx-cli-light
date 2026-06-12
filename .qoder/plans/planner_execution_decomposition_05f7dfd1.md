# Execution Decomposition Layer (planner.py)

## Objective
Build the missing link between intelligence (analyze/route) and execution (executors) by decomposing classified tasks into structured, ordered, dependency-aware step plans.

## Core Policy
- Planner is **optional cognitive enhancer**, NOT a mandatory pipeline stage
- Only triggered for: `COMPLEX`, `CODE_WRITE`, `CODE_MODIFY`
- Simple tasks (CHAT, FILE_OPS, CODE_READ, RESEARCH, etc.) get **minimal 1-step plan**
- `brain.process()` decides when to invoke planner based on TaskType

## Files to Modify
1. `core/uil/contract.py` — add `TaskStep` + `Plan` dataclasses
2. `core/uil/planner.py` — NEW: `TaskPlanner` class (pure logic, rule-based)
3. `core/uil/brain.py` — add planner as constructor-injected optional, brain calls it selectively
4. `core/uil/__init__.py` — export `TaskPlanner`

## Test File
`test_uil_planner.py` — 13 tests

---

## 1. Contract Changes (contract.py)

### Add `TaskStep` dataclass
```python
@dataclass
class TaskStep:
    id: str
    description: str
    dependencies: list[str]
    tool_hints: list[str] | None
    estimated_difficulty: float
    status: str = "pending"
```

### Add `Plan` dataclass
```python
@dataclass
class Plan:
    steps: list[TaskStep]
    dependencies: dict[str, list[str]]
    estimated_complexity: float
    is_minimal: bool = False
    decision_path: list[DecisionStep] = field(default_factory=list)
```

### Update `ExecutionPlan` — add optional `decomposed: Plan | None = None`
No changes to existing fields.

---

## 2. Planner Module (planner.py) — NEW

### Class: `TaskPlanner`
Pure logic. Zero LLM. Zero MCP. Zero imports beyond contract.py.

### Method: `plan(classification, user_input, context=None) -> Plan`
Single entry point. Internally splits:
- COMPLEX / CODE_WRITE / CODE_MODIFY → `_decompose()` (full dependency graph)
- All others → `_minimal_plan()` (1 step, `is_minimal=True`)

### Full decomposition rules:

| TaskType | Steps | Pattern |
|----------|-------|---------|
| COMPLEX | 4-6 steps | setup → backend/db → frontend → integration → test |
| CODE_WRITE | 3 steps | create file → implement → test |
| CODE_MODIFY | 4 steps | read → analyze → modify → verify |

### Minimal plan rules (all other types):
Single step: "handle {task_type_description}"

### Example (COMPLEX, "build a web app"):
```
Step 1: create project structure     [deps: none]
Step 2: implement backend API        [deps: step-1]
Step 3: create database schema       [deps: step-1]
Step 4: build frontend               [deps: step-1]
Step 5: connect frontend to backend  [deps: step-2,step-3,step-4]
Step 6: test the full application    [deps: step-5]
```

### Traceability
Every decomposition decision records a `DecisionStep` — why created, what triggers fired, full vs minimal.

---

## 3. Brain Integration (brain.py)

### Constructor — add `planner` parameter (defaults to None, fully optional)
```python
def __init__(self, analyzer=None, router=None, planner=None, tool_defs=None):
    self.analyzer = analyzer or TaskAnalyzer()
    self.router = router or DecisionRouter()
    self.planner = planner  # None = no planner, pipeline unchanged
    self._tool_defs = tool_defs or []
```

### process() — selective planner invocation after routing
```python
# Step 2.5: Plan — optional cognitive enhancer
if self.planner is not None:
    plan = self.planner.plan(classification, user_input)
    decision.plan.decomposed = plan

    decision.decision_path.append(DecisionStep(
        component="TaskPlanner",
        input_summary=f"type={classification.task_type.value}",
        output=f"{'minimal' if plan.is_minimal else 'decomposed'}: {len(plan.steps)} step(s)",
        score=1.0,
        detail=f"Plan type: {'minimal' if plan.is_minimal else 'full decomposition'}",
    ))
```

The planner internally decides full vs minimal. When `planner=None`, the pipeline is identical to Phase 1.2.

---

## 4. Exports (__init__.py)

Add `from .planner import TaskPlanner` to `__all__`.

---

## 5. Tests (test_uil_planner.py) — 13 tests

1. `test_planner_complex` — COMPLEX produces 4-6 steps with dependencies
2. `test_planner_code_write` — CODE_WRITE produces 3 steps
3. `test_planner_code_modify` — CODE_MODIFY produces 4 steps with read→modify pattern
4. `test_planner_minimal_code_review` — CODE_REVIEW produces 1 step, is_minimal=True
5. `test_planner_minimal_chat` — CHAT produces 1 step, is_minimal=True
6. `test_planner_minimal_research` — RESEARCH produces 1 step, is_minimal=True
7. `test_planner_minimal_browser` — BROWSER produces 1 step, is_minimal=True
8. `test_planner_minimal_database` — DATABASE produces 1 step, is_minimal=True
9. `test_planner_minimal_file_ops` — FILE_OPS produces 1 step, is_minimal=True
10. `test_planner_minimal_unknown` — UNKNOWN produces 1 step, is_minimal=True
11. `test_planner_traceability` — Plan contains DecisionSteps with component="TaskPlanner"
12. `test_planner_optional_in_brain` — brain with planner=None works identically to before
13. `test_planner_selective_in_brain` — COMPLEX triggers full plan; CHAT triggers minimal plan

---

## 6. Verification

- `python -m pytest test_uil_planner.py -v` — all 13 pass
- `python -m pytest test_uil_p12.py test_uil_p13.py test_uil_planner.py -v` — all 31 pass
- No existing tests break (zero changes to existing function signatures)
- brain.py with planner=None is identical to pre-planner behavior

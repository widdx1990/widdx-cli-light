# WIDDX Nexus — Dead Code & Unused Files Analysis

> Identification of dead code, unused files, unreachable imports, and orphaned modules.

## Dead/Unused Modules

### Completely Unreachable from Production Code

| File | Lines | Reason | Status |
|------|-------|--------|--------|
| `core/auto_commit.py` | 137 | Only imported in `tests/test_auto_commit.py` | **DEAD in production** |
| `core/project_context.py` | 286 | Only imported in `tests/test_project_context.py` | **DEAD in production** |
| `core/project_structure.py` | 184 | Only imported in `tests/test_project_context.py` | **DEAD in production** |
| `core/self_reflection.py` | ~200 | Not imported anywhere | **DEAD** |
| `core/web_launcher.py` | ~50 | Not imported anywhere | **DEAD** |
| `core/_path.py` | ~30 | Only used by scripts/web/ | **LOW priority** |
| `_debug_brain.py` | ~30 | Debug script, not part of package | **DEBUG artifact** |
| `_run_tests.py` | ~80 | Manual test runner, not part of test suite | **DEBUG artifact** |

### Orphaned Test Files (tests with no matching production code)

| Test File | Tests What | Production Code Exists? |
|-----------|-----------|------------------------|
| `test_project_context.py` | `project_context.py`, `project_structure.py` | Yes, but both are dead code |
| `test_project_validate.py` | `tools._project_validate()` | Yes, in tools/__init__.py |
| `test_auto_commit.py` | `auto_commit.py` | Yes, but module is dead code |
| `test_benchmark.py` | `BenchmarkRunner` (test-only class) | No (test-only) |

## Unused Functions & Classes

### In `core/` modules

| Function/Class | File | Reason Unused |
|---------------|------|--------------|
| `AutoCommitManager` | `auto_commit.py` | Never instantiated in production |
| `ProjectContextManager` | `project_context.py` | Only used in tests |
| `ProjectStructureAnalyzer` | `project_structure.py` | Only used in tests |
| `ErrorPatternLearner.get_recurring_errors()` | `self_improve.py` | Called but results never displayed |
| `self_improve.get_improver()` | `self_improve.py` | Singleton created but never used by any consumer |
| `WorkflowEngine.pipeline()` | `workflow.py` | Defined but never called by any code path |
| `WorkflowEngine.create()` | `workflow.py` | Defined but workflows aren't used by AI |
| `WorkflowEngine.run()` | `workflow.py` | Defined but never triggered from main flow |
| `BackgroundTaskManager.clean_old()` | `background.py` | Defined but never called (cleanup never triggered) |
| `get_extra_file_tools()` | `tools/__init__.py` | Called but `_EXTRA_FILE_TOOLS` is always empty |
| `set_extra_file_tools()` | `tools/__init__.py` | Never called by any code |
| `get_bash_tool_def()` | `tools/__init__.py` | Never called |
| `get_write_tool_def()` | `tools/__init__.py` | Never called |
| `get_read_tool_def()` | `tools/__init__.py` | Never called |

### In `core/intelligence/` (v4 engine, partially wired)

| Function/Class | File | Status |
|---------------|------|--------|
| `PatternLearner` | `learner.py` | Created but never called from main flow |
| `PatternAwarePlanner` | `planner.py` | Created but only used by `get_planner()` singleton |
| `SoftwarePattern` | `patterns.py` | Defined but patterns never matched in production |
| `PatternStep` | `patterns.py` | Defined but unused |
| `get_pattern()` | `patterns.py` | Defined but never called |
| `get_planner()` | `planner.py` | Singleton created but never used |
| `get_learner()` | `learner.py` | Singleton created but never used |
| `get_decision_engine()` | `decision_engine.py` | Singleton created but never used |

### In `core/isolation/` (feature-flagged, partially dead)

| Function/Class | File | Status |
|---------------|------|--------|
| `ContainerManager` | `container.py` | Only used if engine flag enabled |
| `IsolationPolicy` | `policy.py` | Only used if engine flag enabled |
| `IsolationProfile` | `profiles.py` | Only used if engine flag enabled |

### In `core/validation/` (v4 engine, partially wired)

| Function/Class | File | Status |
|---------------|------|--------|
| `CodeRunner` | `runner.py` | Used only by brain.py when engine enabled |
| `ValidationReporter` | `reporter.py` | Used only by brain.py when engine enabled |
| `get_runner()` | `runner.py` | Singleton created but only called from brain.py |
| `get_reporter()` | `reporter.py` | Singleton created but only called from brain.py |

## Unused Imports (potential dead references)

| File | Unused Import | Reason |
|------|--------------|--------|
| `core/__init__.py` | `VisionMode` | Exported but never imported by consumers |
| `core/__init__.py` | `describe_image` | Exported but never imported by consumers |
| `core/__init__.py` | `process_user_input_with_vision` | Exported but never imported by consumers |
| `core/__init__.py` | `execute_with_skills` | Exported from core but imported directly from core.tools |

## Dead Configuration

| Config Key | File | Status |
|-----------|------|--------|
| `mcp_servers[5]` (sqlite) | `config.json` | Hardcoded absolute Windows path — breaks on other machines |

## Unreferenced Files in File Tree

| File | Purpose | Referenced? |
|------|---------|-------------|
| `vscode-extension/widdx-cortex-1.0.0.vsix` | Pre-built VS Code extension | No (artifact) |
| `scripts/web/.widdx/knowledge.json` | Web dashboard knowledge cache | Runtime only |
| `api_server.py` (root) | Alias for scripts/api_server.py | Entry point only |
| `run_textual.py` (root) | Alias for scripts/run_textual.py | Entry point only |

## Summary Statistics

| Category | Count |
|----------|-------|
| Completely dead modules | 8 |
| Orphaned test files | 4 |
| Unused functions/methods | ~20 |
| Unused singletons | 6 |
| Feature-flagged dead code (engines) | ~15 classes/functions |
| Unused exports | 3 |
| Debug artifacts | 2 |

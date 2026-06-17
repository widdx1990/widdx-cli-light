# WIDDX Cortex — Phase 11: Production Grade

> **Rule:** Zero tolerance for errors, breakage, or regressions.
> **Gate:** Every layer must pass `python -m pytest tests/ -q` before next layer.

---

## L1: Dangerous Command Guard (`core/guard.py`)

**Problem:** Agent can execute destructive commands blindly.

**Solution:**
- Pattern-based blocklist: `rm -rf /`, `format`, `:(){ :|:& };:`, etc.
- Path-traversal detection: prevent `rm -rf /home/*` when cwd is project
- Confirmation prompt for high-risk operations
- Override with explicit `--force` flag

**Files:**
- `core/guard.py` — CommandGuard class
- `tests/test_guard.py` — 10+ test cases

---

## L2: Diff Engine (`core/diff_engine.py`)

**Problem:** Search-and-replace editing is fragile, error-prone.

**Solution:**
- Generate unified diff from old → new content
- Apply diff with 3-way merge fallback
- Conflict detection: reject patch if context lines don't match
- Dry-run mode: preview changes before applying
- Integrate into agent's Edit tool path

**Files:**
- `core/diff_engine.py` — DiffEngine class
- `tests/test_diff_engine.py` — 10+ test cases

---

## L3: Checkpoint Manager (`core/checkpoint.py`)

**Problem:** No undo after agent makes a mistake.

**Solution:**
- Git-based checkpoint before every write/edit
- Snapshot file tree with checksums
- Rollback to any checkpoint
- Auto-cleanup old checkpoints (keep last 50)
- List/restore commands

**Files:**
- `core/checkpoint.py` — CheckpointManager class
- `tests/test_checkpoint.py` — 8+ test cases

---

## L4: Smart Repo Map (`core/repo_mapper.py`)

**Problem:** Agent sends too much/too little context.

**Solution:**
- Dependency graph from imports (Python, JS, Go)
- File ranking by relevance to current task
- Smart context selector: top-N most relevant files
- Symbol extraction: functions, classes, exports
- Incremental update: only rescan changed files

**Files:**
- `core/repo_mapper.py` — RepoMapper class
- `tests/test_repo_mapper.py` — 8+ test cases

---

## L5: PyPI Package (`pyproject.toml` + automation)

**Problem:** Users can't `pip install widdx`.

**Solution:**
- Complete pyproject.toml metadata
- Build wheel: `python -m build`
- Test publish workflow
- README badges + install instructions
- `pip install widdx-cortex` one-liner

**Files:**
- `pyproject.toml` — updated metadata
- `.github/workflows/publish.yml` — auto-publish on tag

---

## Quality Gates (per layer)

- [ ] `python -m py_compile <new_file>` — clean
- [ ] `python -m pytest tests/test_<layer>.py -v` — all pass
- [ ] `python -m pytest tests/ -q` — 105+ existing tests still pass
- [ ] Zero regressions, zero warnings

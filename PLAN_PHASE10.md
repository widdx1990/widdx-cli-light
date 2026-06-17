# WIDDX Cortex — Phase 10 Implementation Plan

> **Created:** 2026-06-18
> **Architecture by:** MUHAMMAD MUSLIH | WIDDX
> **Methodology:** Strict, systematic — zero tolerance for breakage

---

## Architecture Overview

Phase 10 fills the remaining gaps. Each layer is built in isolation,
tested independently, then integrated. No change lands without passing
the full test suite + the new layer's own tests.

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 10 LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  L1: Cache Layer         L2: Vector Memory                  │
│  ┌──────────────┐        ┌──────────────────┐              │
│  │ ResponseCache │        │ VectorMemoryStore │              │
│  │ ToolResultCache│       │ EmbeddingEngine   │              │
│  │ TTL / Invalidate│      │ SemanticSearch    │              │
│  └──────────────┘        └──────────────────┘              │
│                                                              │
│  L3: Plugin Hot-Reload   L4: Session Search                 │
│  ┌──────────────┐        ┌──────────────────┐              │
│  │ FileWatcher   │        │ FullTextIndex    │              │
│  │ SkillReloader │        │ SessionSearcher  │              │
│  │ No-restart    │        │ FuzzyMatch       │              │
│  └──────────────┘        └──────────────────┘              │
│                                                              │
│  L5: Diff Viewer (TUI)   L6: Benchmark Suite                │
│  ┌──────────────┐        ┌──────────────────┐              │
│  │ GitDiffWidget │        │ RoutingBenchmark │              │
│  │ InlineDiff    │        │ AccuracyReport   │              │
│  │ SyntaxHighlight│       │ ModelComparison  │              │
│  └──────────────┘        └──────────────────┘              │
│                                                              │
│  L7: GitHub Actions CI   L8: Advanced Self-Improvement      │
│  ┌──────────────┐        ┌──────────────────┐              │
│  │ ci.yml       │        │ ErrorPatternLearn│              │
│  │ lint + test  │        │ PromptOptimizer  │              │
│  │ auto-release │        │ CorrectionLoop   │              │
│  └──────────────┘        └──────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Order (Strict Dependency Chain)

```
L1 → L2 → L3 → L4 → L5 → L6 → L7 → L8
│     │     │     │     │     │     │     │
Cache  Vec   Plug  Srch  Diff  Bench CI    Learn
```

### Why this order:
1. **L1 (Cache)** — Foundation. Reduces load on providers, speeds up dev of other layers.
2. **L2 (Vector Memory)** — Depends on nothing. Enables semantic search for L4.
3. **L3 (Plugin Hot-Reload)** — Standalone. Improves DX during remaining work.
4. **L4 (Session Search)** — Depends on L2 (vector) for best results.
5. **L5 (Diff Viewer TUI)** — Standalone feature. Pure TUI widget.
6. **L6 (Benchmark Suite)** — Needs L1+L3 stable to compare models fairly.
7. **L7 (CI)** — Needs L6 to gate PRs on benchmark regressions.
8. **L8 (Self-Improvement)** — Needs all above stable to learn safely.

---

## Quality Gates (per layer)

Each layer MUST pass ALL of these before being marked complete:

- [ ] `python -m py_compile <new_file>` — no syntax errors
- [ ] `python -m pytest test_*.py -v` — all 54 existing tests pass
- [ ] New test file for the layer — `test_phase10_<layer>.py`
- [ ] Manual smoke test — documented in the task file
- [ ] Code review — self-review against the anti-duplication rules in AGENT_PROMPT

---

## File Structure (new files only)

```
core/
├── cache.py              # L1: Response + tool-result cache
├── cache_test.py         # L1: Tests
├── vector_memory.py      # L2: Embedding + semantic search
├── vector_memory_test.py # L2: Tests
├── plugin_loader.py      # L3: Hot-reload watcher
├── plugin_loader_test.py # L3: Tests
├── session_search.py     # L4: Full-text + semantic search
├── session_search_test.py# L4: Tests
tui/
├── widgets/
│   └── diff_viewer.py    # L5: Inline git diff widget
├── screens/
│   └── diff_screen.py    # L5: Diff viewer screen
tests/
├── test_benchmark.py     # L6: Benchmark suite
.github/
├── workflows/
│   └── ci.yml            # L7: CI pipeline (enhanced)
core/
├── self_improve.py       # L8: Advanced learning loop
├── self_improve_test.py  # L8: Tests
```

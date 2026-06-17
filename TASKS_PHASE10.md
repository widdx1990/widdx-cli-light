# Phase 10 — Task Breakdown & Execution Log

> **Rule:** No layer is marked complete until ALL quality gates pass.
> **Rule:** Every edit is validated with `node --check` or `python -m py_compile`.
> **Rule:** Full test suite (`pytest test_*.py -v`) after each layer.

---

## L1: Cache Layer ⏳

**Goal:** Eliminate redundant API calls for identical requests + cache tool results.

### Tasks:
- [ ] L1.1: Create `core/cache.py` with `ResponseCache` class
  - TTL-based expiration (configurable per cache type)
  - LRU eviction when max_size reached
  - Disk persistence (JSON) for survival across restarts
  - Cache keys: (provider, model, messages_hash)
- [ ] L1.2: Create `ToolResultCache` subclass
  - Cache keys: (tool_name, args_hash)
  - Short TTL for bash (30s), longer for read-only tools (5min)
  - Auto-invalidate on file writes
- [ ] L1.3: Integrate into provider call chain (`providers.py`)
  - Check cache before API call
  - Store result after successful call
  - Skip cache when `temperature > 0` (non-deterministic)
- [ ] L1.4: Create `test_cache.py` with 5+ tests
- [ ] L1.5: Smoke test — run WIDDX, verify cache hit on repeated query

---

## L2: Vector Memory ⏳

**Goal:** Semantic memory search using embeddings. Replace flat JSON search.

### Tasks:
- [ ] L2.1: Create `core/vector_memory.py` with `VectorMemoryStore`
  - Uses sentence-transformers or ollama embeddings (local, no API cost)
  - Cosine similarity search
  - CRUD operations (add, search, delete, update)
  - Auto-chunking for long content
- [ ] L2.2: Integrate with existing `MemoryStore` (backward compat)
- [ ] L2.3: Add `/memory search "semantic query"` command
- [ ] L2.4: Create `test_vector_memory.py` with 5+ tests
- [ ] L2.5: Smoke test — search across sessions semantically

---

## L3: Plugin Hot-Reload ⏳

**Goal:** Reload skills without restarting WIDDX.

### Tasks:
- [ ] L3.1: Create `core/plugin_loader.py` with `PluginWatcher`
  - Watch `skills/` directory for file changes (watchdog or polling)
  - Reload individual skill files on change
  - Emit events: `skill_loaded`, `skill_reloaded`, `skill_removed`
- [ ] L3.2: Integrate with `core/skills_v2.py`
  - Replace static load with dynamic registry
  - Add `/skills reload` command
- [ ] L3.3: Create `test_plugin_loader.py` with 5+ tests
- [ ] L3.4: Smoke test — edit a skill, verify it updates without restart

---

## L4: Session Search ⏳

**Goal:** Full-text + semantic search across all saved sessions.

### Tasks:
- [ ] L4.1: Create `core/session_search.py` with `SessionSearcher`
  - Full-text index using SQLite FTS5
  - Optional: semantic search via L2 (VectorMemory)
  - Search by: content, date range, session name, tags
  - Ranked results with snippets
- [ ] L4.2: Add `/sessions search "query"` CLI command
- [ ] L4.3: Add search bar in TUI session screen
- [ ] L4.4: Create `test_session_search.py` with 5+ tests
- [ ] L4.5: Smoke test — create sessions, search, verify results

---

## L5: Diff Viewer (TUI) ⏳

**Goal:** View git diffs inline in the TUI with syntax highlighting.

### Tasks:
- [ ] L5.1: Create `tui/widgets/diff_viewer.py` with `DiffWidget`
  - Parse `git diff` output
  - Render with color-coded additions/deletions
  - Line numbers
  - Scrollable
- [ ] L5.2: Create `tui/screens/diff_screen.py`
  - Show diff for current changed files
  - File picker to select which file's diff to view
- [ ] L5.3: Wire into TUI navigation
- [ ] L5.4: Create `test_diff_viewer.py` (render tests)
- [ ] L5.5: Smoke test — make a change, view diff in TUI

---

## L6: Benchmark Suite ⏳

**Goal:** Compare routing accuracy across provider/model combinations.

### Tasks:
- [ ] L6.1: Create `tests/test_benchmark.py` with `RoutingBenchmark`
  - Test dataset: 50+ labeled inputs (Arabic + English)
  - Measure: accuracy, latency, cost per classification
  - Compare: opencode-zen vs ollama vs deepseek
- [ ] L6.2: Create `BenchmarkRunner` class
  - Runs each test case, records results
  - Generates report: accuracy %, avg latency, cost
- [ ] L6.3: Add `/benchmark` command to CLI
- [ ] L6.4: Smoke test — run benchmark, verify report generated

---

## L7: GitHub Actions CI ⏳

**Goal:** Automated lint + test + benchmark on every push.

### Tasks:
- [ ] L7.1: Enhance `.github/workflows/ci.yml`
  - Python 3.11, 3.12 matrix
  - Lint: ruff check
  - Test: pytest with coverage
  - Benchmark gate: fail if accuracy drops >2%
- [ ] L7.2: Add coverage reporting
- [ ] L7.3: Smoke test — push, verify CI passes

---

## L8: Advanced Self-Improvement ⏳

**Goal:** Learn from repeated errors and optimize prompts automatically.

### Tasks:
- [ ] L8.1: Create `core/self_improve.py` with `ErrorPatternLearner`
  - Detect repeated error patterns across sessions
  - Auto-suggest prompt improvements
  - Track which fixes actually worked
- [ ] L8.2: Integrate with `self_reflection.py`
- [ ] L8.3: Create `test_self_improve.py` with 5+ tests
- [ ] L8.4: Smoke test — simulate repeated errors, verify learning

---

## Progress Tracker

| Layer | Started | Completed | Tests | Smoke |
|-------|---------|-----------|-------|-------|
| L1: Cache | ✅ | ✅ | ✅ 18/18 | ✅ integrated in agent |
| L2: Vector Memory | ✅ | ✅ | ✅ 11/11 | ✅ TF-IDF + Ollama |
| L3: Plugin Hot-Reload | ✅ | ✅ | ✅ 8/8 | ✅ watcher + reloader |
| L4: Session Search | ✅ | ✅ | ✅ 11/11 | ✅ FTS5 + LIKE fallback |
| L5: Diff Viewer TUI | ✅ | ✅ | ✅ | ✅ diff + changed files |
| L6: Benchmark Suite | ✅ | ✅ | ✅ 3/3 | ✅ 58.6% type, 75.9% mode |
| L7: GitHub CI | ✅ | ✅ | ✅ | ✅ +benchmark job |
| L8: Self-Improvement | ✅ | ✅ | ✅ | ✅ error patterns + fixes |
| L5: Diff Viewer TUI | ❌ | ❌ | ❌ | ❌ |
| L6: Benchmark Suite | ❌ | ❌ | ❌ | ❌ |
| L7: GitHub CI | ❌ | ❌ | ❌ | ❌ |
| L8: Self-Improvement | ❌ | ❌ | ❌ | ❌ |

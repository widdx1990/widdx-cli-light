# Changelog

## 3.2.0 (2026-07-01)

### Quality & Tooling
- **mypy: 253 → 0 errors** across 171 source files (core/ + scripts/ + cli/ + tui/)
- **ruff: 347 → 0 lint warnings** (E401, E402, E501, E701, E741, F401, F821, F841, F811 fixed)
- **Makefile** with 15 commands (install, test, lint, typecheck, build, clean, run-*)
- **pyproject.toml** configured for mypy + ruff
- `callable` → `Callable` type hint fix (15 occurrences)
- `any` → `Any` type hint fix (5 occurrences)
- Implicit `Optional` (PEP 484) fixed across 24 parameters in 12 files
- `CREATE_NO_WINDOW` cross-platform support for non-Windows

### Config & Validation
- `validate_config()` — checks provider, max_turns, temperature, MCP servers with warnings + defaults
- `_resolve_placeholders()` — `{PROJECT_ROOT}`, `{CWD}`, `{USER_HOME}` resolved at load
- `ReliableProvider` now has proper `_default_urls` mapping for all 5 provider types + fallback
- Config default provider changed from `nonexistent-xyz` to `opencode-zen`

### Logging
- New `core/log_setup.py` with `setup_logging()` — unified format across CLI, TUI, Web, API
- CLI app now has proper logging (was silent)
- Web UI now has proper logging (was silent)

### Architecture
- **Parallel ExpertTeam** — Researcher + Coder run in parallel via ThreadPoolExecutor (saves response time)
- Project root cleanup — `api_server.py`, `run_textual.py` removed from root; `run-web.bat` moved to `scripts/`
- Duplicate installation scripts removed (`scripts/install.bat`, `scripts/install.ps1`, etc.)

### Test Stability
- **538 passed, 0 failed** (was 530 passed, 8 failed)
- Provider tests now use `raw=True` to verify actual factory classes
- `test_decision_path` updated for new `PreDecisionForce` decision step
- `ReliableProvider.base_url` now has proper fallback URLs
- All provider tests (opencode-zen, ollama, openai, deepseek) pass reliably

## 3.1.0 (2026-06-27)

### Level 5.0 — Autonomy Platform
- TaskState persistence engine (survives restarts)
- Global StateManager (7 sources → unified context)
- AutonomyLoop (execute→verify→fix→continue without human)
- True SelfCorrection (7 classified fix strategies)
- DecisionLayer (ADR + Memory + KG + Plan weighted decisions)
- Recursive Agent Spawning (agent → sub-agent → sub-sub-agent, max depth 3)

### Level 4.0 — Advanced Capabilities
- Memory Versioning (version, confidence, status, deprecation lifecycle)
- Architecture Decision Records (ADR)
- KnowledgeGraph (BFS, nodes, edges, project structure)
- VerifyLoop (verify→fix→retest cycle)
- DocSync (code-documentation drift detection)

### Provider Reliability Layer
- ProviderPool with automatic failover (priority + cooldown)
- Retry with exponential backoff (2s, 4s, 8s)
- Checkpoint on failure for task resume
- UnifiedToolCall across all 7 providers
- Code extraction fallback (for models without tool support)
- ReliableProvider wired into AutonomousAgent

### Agent System
- Checkpoint/resume in AutonomousAgent (Step Lock idempotency)
- ExpertTeam + KG language detection
- spawn_agent tool for recursive agent trees
- Provider failover within agent loop (3 retries, never dies on first error)
- Code extraction fallback (text → files when LLM won't use tools)

### Web UI
- Project Docs viewer (PLAN/DESIGN/TASKS/ROADMAP with templates)
- Session search across all conversations
- Voice input (Web Speech API, Arabic/English)
- Image/file upload with preview badges
- Autonomous Mode toggle button
- Terminal with command history (Arrow keys)
- Safe JS stubs prevent ReferenceError before scripts load
- All scripts moved to `<head>` for reliable loading

### Security
- API auth bypass fix (empty token → 503 rejection)
- Default permission NORMAL (was PERMISSIVE)
- Request body size limit (1MB, configurable)
- SQLite-backed rate limiter
- Command guard integration in sandbox
- Skill sandbox with safe builtins + blocked modules

### Architecture
- Database migration system (schema_version + ordered migrations)
- Graceful shutdown (SIGINT/SIGTERM handlers)
- Global user config (~/.widdx/config.json) as fallback
- Config resolution: project → CWD → global → bundled
- Wrapper layer reduction (4 layers → 2)
- 17 dead imports removed across 5 files

### Quality
- 523→539 tests, 0 failures
- 15 new test files for Level 4.0/5.0
- Type hints for all public APIs
- Monkey-patch replaced with logging in debug scripts
- Complete architecture documentation (7 docs)

## 3.0.0 (2026-06-26)

### Core Systems
- UIL Brain Pipeline (Analyze → Route → Plan → Execute → Verify → Learn)
- AutonomousAgent with tool-calling loop
- ExpertTeam (5 sequential expert agents)
- 7 LLM providers with unified interface
- 18 built-in skills (React, Vue, Django, Flutter, etc.)
- Sandbox executor (Windows/Linux/macOS)
- Command guard (block dangerous commands)
- SQLite session persistence
- Memory system (markdown + frontmatter)
- MCP Protocol client
- Cron scheduler + background tasks
- Delegation (parallel sub-agents)
- WebSocket + REST API

### Interfaces
- Web UI (FastAPI + WebSocket, 40+ endpoints)
- CLI (Rich terminal interface)
- TUI (Textual terminal UI)
- REST API (Bear token auth)

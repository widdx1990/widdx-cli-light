# Changelog

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

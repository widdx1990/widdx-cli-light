# WIDDX Cortex — Roadmap

> **Created & Designed by MUHAMMAD MUSLIH | widdx**

---

## ✅ Phase 1: Foundation — COMPLETE

- [x] Smart Read: line numbers, offset/limit, syntax context
- [x] Smart Edit: diff preview, multiple replacements, undo
- [x] Context Window: sliding window, structured summarization
- [x] CLI Framework: subcommands, autocomplete, --help
- [x] Memory System: MEMORY.md frontmatter, cross-links (`core/memory.py`)
- [x] Permission System: granular allow/deny/ask per tool (`core/permissions.py`)

## ✅ Phase 2: Agent System — COMPLETE

- [x] Workflow Engine: `core/workflow.py` (agent(), parallel(), pipeline())
- [x] Sub-agents: `core/agents/agent.py` — autonomous tool-calling loop
- [x] Expert Team: `core/agents/expert.py` — specialized expert profiles
- [x] Git Integration: `core/project/git.py` — auto-commit, undo, diff
- [x] Task Tracking: project config + session state

## ✅ Phase 3: MCP Ecosystem — COMPLETE

- [x] Auto-discovery: scan registry for MCP servers (`/mcp discover`)
- [x] Dynamic Loading: hot-add/remove servers at runtime
- [x] OAuth Flow: interactive auth prompt for protected servers
- [x] Error Recovery: auto-reconnect, timeout handling

## ✅ Phase 4: Intelligence Layer (UIL) — COMPLETE

- [x] UIL Analyzer: 13 task classifiers (`core/uil/analyzer.py`)
- [x] Router: tool-group filtering, routing decisions (`core/uil/router.py`)
- [x] Planner: structured multi-step planning (`core/uil/planner.py`)
- [x] Knowledge: persistent KnowledgeBase with JSON (`core/uil/knowledge.py`)
- [x] Brain: pipeline orchestrator (`core/uil/brain.py`)
- [x] GGUF model support (Ollama local + streaming reader)
- [x] Multi-provider: DeepSeek, OpenAI, OpenCode Zen, Ollama

## ✅ Phase 5: TUI — COMPLETE

- [x] Full Textual TUI (`tui/app.py` + `tui/app.tcss`)
- [x] Screens: Settings, Session CRUD, Memory CRUD, Help, Tool Detail
- [x] CLI/TUI parity — all commands available in both interfaces
- [x] Streaming output in TUI with reasoning support

---

## 🔜 Phase 6: Polish & Distribution (Next)

- [ ] **README overhaul** — full English + Arabic docs, screenshots, GIFs
- [ ] **`/agent` command** — expose expert team from CLI directly
- [ ] **Plugin hot-reload** — reload skills without restart
- [ ] **Session search** — full-text search across saved sessions
- [ ] **Diff viewer in TUI** — inline git diff display
- [ ] **Benchmark suite** — compare routing accuracy across models
- [ ] **PyPI publish** — `pip install widdx-cortex`
- [ ] **GitHub Actions** — CI: lint + tests on push

## 🔜 Phase 7: Ecosystem

- [ ] VS Code Extension (sidebar chat panel)
- [ ] GitHub App (PR review, issue triage)
- [ ] Team Features (shared sessions, project config sync)
- [ ] Self-improvement loop: learn from corrections

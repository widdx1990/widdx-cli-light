# Project Map — WIDDX Nexus

## Identity

| Field | Value |
|---|---|
| **Package Name** | `widdx-nexus` |
| **Version** | `3.1.0` (pyproject.toml) — inconsistent with runtime strings |
| **Author** | MUHAMMAD MUSLIH — widdx.com |
| **License** | MIT |
| **Python** | ≥ 3.10 |
| **Repo** | https://github.com/widdx1990/widdx-nexus |

---

## Purpose

WIDDX Nexus is a terminal-based AI engineering workspace that provides:
- A **CLI** (plain terminal chat with streaming)
- A **TUI** (Textual-based full-screen interactive app)
- A **Web UI** (FastAPI + WebSocket + vanilla JS SPA)
- A **REST API server** (authenticated, rate-limited)
- A **VS Code extension** (sidebar chat panel)
- A **GitHub App** (PR review webhook handler)
- A **Gateway** layer (Telegram + Discord bots)
- An **MCP client** (Model Context Protocol server orchestration)

The cognitive core is the **Unified Intelligence Layer (UIL)** — a pipeline that classifies user input, routes it to the appropriate executor (simple chat, agent loop, code review, etc.), plans steps, verifies output, and records outcomes.

---

## Top-Level Directory Structure

```
chat-tool/                          ← Project root
├── .claude/                        ← Claude Code settings (gitignored)
│   └── settings.local.json
├── .github/
│   └── workflows/
│       └── ci.yml                  ← GitHub Actions CI (test + lint + build)
├── .gitignore
├── .gitattributes
├── build/                          ← Build artifact (should be gitignored — IS listed)
│   └── lib/                        ← Old stale source copies (pre-refactor)
├── cli/                            ← Plain-terminal CLI frontend
│   ├── __init__.py
│   ├── app.py                      ← CLIApp class — main readline loop
│   ├── commands.py                 ← Slash-command handler
│   ├── display.py                  ← Rich display helpers
│   ├── input.py                    ← Prompt_toolkit input handler
│   └── theme.py                    ← Terminal color theme
├── core/                           ← Business logic / AI engine
│   ├── __init__.py                 ← Public re-export surface
│   ├── __main__.py                 ← `python -m core` → web_app
│   ├── _path.py                    ← sys.path resolver
│   ├── activity.py                 ← Activity/event log store
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent.py                ← AutonomousAgent (tool-calling loop)
│   │   ├── executor_adapter.py     ← Maps ExecutionMode → executor callables
│   │   └── expert.py              ← Expert agent (specialized system prompts)
│   ├── auto_commit.py             ← Auto-commit after code changes
│   ├── auto_setup.py              ← First-run environment detection
│   ├── background.py              ← BackgroundTaskManager (threads)
│   ├── cache.py                   ← Semantic response cache
│   ├── chat.py                    ← Core chat loop (sync streaming)
│   ├── checkpoint.py              ← Session checkpoint / restore
│   ├── cli.py                     ← `widdx` entry point → CLIApp
│   ├── commands.py                ← Core command dispatch (heavy)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            ← JSON config loader/saver
│   │   └── keychain.py            ← XOR-obfuscated API key storage
│   ├── cron/
│   │   ├── __init__.py
│   │   ├── job.py                 ← CronJob dataclass
│   │   ├── parser.py              ← Cron expression parser
│   │   ├── scheduler.py           ← CronScheduler (thread-based)
│   │   └── store.py               ← Cron job persistence (JSON)
│   ├── database.py                ← SQLite ORM (sessions, messages, memories)
│   ├── delegation.py              ← DelegationManager (sub-agents)
│   ├── diagnostics.py             ← Error collector / diagnostics
│   ├── diff_engine.py             ← Unified diff generation
│   ├── engine_adapters.py         ← Bridge: new engines ↔ UIL contracts
│   ├── engine_arbiter.py          ← Resolves old vs new engine disagreements
│   ├── engine_trust.py            ← Trust accumulator for engine selection
│   ├── gateway/
│   │   ├── __init__.py            ← GatewayCore, Platform, Message, Reply
│   │   ├── discord.py             ← Discord bot adapter
│   │   └── telegram.py            ← Telegram bot adapter
│   ├── guard.py                   ← Permission guard / safety checks
│   ├── intelligence/              ← Local (no-LLM) decision engine
│   │   ├── __init__.py
│   │   ├── classifier.py          ← TF-IDF + keyword classifier
│   │   ├── decision_engine.py     ← Learned routing decisions
│   │   ├── embeddings.py          ← Local TF-IDF embeddings
│   │   ├── learner.py             ← Pattern learner from history
│   │   ├── patterns.py            ← 25+ software project patterns
│   │   └── planner.py             ← Pattern-aware task planner
│   ├── isolation/                 ← Container-based process isolation
│   │   ├── __init__.py
│   │   ├── container.py           ← ContainerManager (Docker/podman)
│   │   ├── policy.py              ← IsolationPolicy rules
│   │   └── profiles.py            ← Pre-defined isolation profiles
│   ├── linter.py                  ← Code linter wrapper
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py              ← MCPClientManager (stdio process spawn)
│   ├── memory.py                  ← MemoryStore (file + index)
│   ├── memory_learner.py          ← Auto-extract memory from conversations
│   ├── multi_editor.py            ← Batch multi-file editor
│   ├── permissions.py             ← Permission matrix
│   ├── plugin_loader.py           ← Dynamic plugin system + hot reload
│   ├── project/
│   │   ├── __init__.py
│   │   ├── git.py                 ← Git operations wrapper
│   │   ├── manifest.py            ← Project manifest (MANIFEST.json)
│   │   ├── scanner.py             ← Project file scanner
│   │   └── state.py               ← Session/branch state persistence
│   ├── project_context.py         ← Project context builder for prompts
│   ├── project_structure.py       ← Project structure formatter
│   ├── project_tracker.py         ← Project tracking / goals
│   ├── providers/
│   │   ├── __init__.py            ← Re-exports from providers.py
│   │   ├── providers.py           ← Backward-compat re-export facade
│   │   ├── base.py                ← Provider ABC + ToolCall
│   │   ├── ollama.py              ← OllamaProvider
│   │   ├── openai_compatible.py   ← OpenAICompatibleProvider
│   │   ├── opencode_zen.py        ← OpenCodeZenProvider
│   │   ├── deepseek.py            ← DeepSeekProvider
│   │   ├── free_models.py         ← Free model discovery + cost estimation
│   │   ├── gguf.py                ← GGUF file utilities (scan, import)
│   │   ├── gguf_provider.py       ← GGUFDirectProvider (llama-cpp)
│   │   └── factory.py             ← create_provider() factory
│   ├── proxy.py                   ← HTTP proxy manager
│   ├── py.typed                   ← PEP 561 marker
│   ├── rag.py                     ← Retrieval-augmented generation
│   ├── repo_mapper.py             ← Repository map builder
│   ├── sandbox.py                 ← SandboxExecutor (WSL/Docker/process)
│   ├── self_improve.py            ← Self-improvement / meta-learning
│   ├── self_reflection.py         ← Post-execution self-reflection
│   ├── session_search.py          ← Full-text session search
│   ├── session_v2.py              ← Session v2 model
│   ├── skills.py                  ← SkillManager (loads skills/ directory)
│   ├── suggester.py               ← Command suggestion engine
│   ├── token_budget.py            ← Token budget tracker
│   ├── tools/
│   │   ├── __init__.py            ← All built-in tools (1275 lines)
│   │   ├── browser.py             ← Browser/screenshot tool
│   │   └── security.py            ← Dangerous pattern scanner
│   ├── uil/                       ← Unified Intelligence Layer
│   │   ├── __init__.py
│   │   ├── analyzer.py            ← TaskAnalyzer (classification)
│   │   ├── brain.py               ← UnifiedIntelligenceLayer (orchestrator)
│   │   ├── contract.py            ← All UIL data contracts (Enums, dataclasses)
│   │   ├── executors.py           ← Simple executor implementations
│   │   ├── knowledge.py           ← KnowledgeBase (outcome recording)
│   │   ├── planner.py             ← TaskPlanner (cognitive enhancer)
│   │   ├── router.py              ← DecisionRouter (mode selection)
│   │   └── verifier.py            ← Post-execution quality verifier
│   ├── ui_visual.py               ← Rich visual renderers for CLI/TUI
│   ├── utils.py                   ← Misc utilities
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── reporter.py            ← Validation report generator
│   │   └── runner.py              ← Validation runner (linters/tests)
│   ├── vector_memory.py           ← Embedding-based vector memory
│   ├── vision.py                  ← Image description (Ollama/pipeline/fallback)
│   ├── voice.py                   ← TTS engine (edge-tts)
│   ├── web_launcher.py            ← Web UI launcher helper
│   └── workflow.py                ← Workflow executor
├── github-app/
│   ├── app.py                     ← GitHub webhook handler (Flask/httpx)
│   └── README.md
├── scripts/
│   ├── __init__.py
│   ├── api_server.py              ← FastAPI REST API (authenticated)
│   ├── main.py                    ← CLI launcher
│   ├── run_textual.py             ← TUI launcher
│   ├── static/                    ← Web UI static assets
│   │   ├── index.html             ← Main SPA page (RTL/i18n)
│   │   ├── css/
│   │   │   └── style.css          ← Full design system (87 KB)
│   │   └── js/
│   │       ├── lang.js            ← i18n engine (en/ar)
│   │       ├── nexus.js           ← Main app logic + WebSocket (47 KB)
│   │       ├── ui.js              ← Theme, sidebar, markdown parser (27 KB)
│   │       └── views/             ← View modules (one per dashboard section)
│   │           ├── activity.js
│   │           ├── apikeys.js
│   │           ├── autocommit.js
│   │           ├── checkpoints.js
│   │           ├── cron.js
│   │           ├── dashboard.js
│   │           ├── debug.js
│   │           ├── delegation.js
│   │           ├── doctor.js
│   │           ├── gateway.js
│   │           ├── gguf.js
│   │           ├── git.js
│   │           ├── manifest.js
│   │           ├── mcp.js
│   │           ├── memory.js
│   │           ├── permissions.js
│   │           ├── plugins.js
│   │           ├── proxy.js
│   │           ├── sessions.js
│   │           ├── settings.js    ← (37 KB — largest view)
│   │           ├── skills.js
│   │           ├── tokenbudget.js
│   │           └── workflows.js
│   ├── web/
│   │   ├── __init__.py
│   │   ├── server.py              ← FastAPI WebSocket server (72 routes)
│   │   ├── chat.py                ← ChatHandler (UIL pipeline wrapper)
│   │   ├── sandbox.py             ← SandboxHandler
│   │   ├── web_app.py             ← Alias (also at scripts/web_app.py)
│   │   └── dashboard/
│   │       ├── __init__.py        ← Dashboard composite class
│   │       ├── _mixin_core.py
│   │       ├── _mixin_devops.py
│   │       ├── _mixin_gateway.py
│   │       ├── _mixin_scheduler.py
│   │       ├── _mixin_settings.py
│   │       └── _mixin_storage.py
│   └── web_app.py                 ← `widdx-web` entry point (port-finder)
├── skills/                        ← Prompt-based skill definitions
│   ├── app-builder/skill.md
│   ├── cinematic-experience/skill.md
│   ├── code-review/skill.md
│   ├── django-builder/skill.md
│   ├── document/skill.md
│   ├── explain-code/skill.md
│   ├── express-builder/skill.md
│   ├── fix-bug/skill.md
│   ├── flutter-builder/skill.md
│   ├── generate-tests/skill.md
│   ├── graphic-designer/skill.md
│   ├── laravel-builder/skill.md
│   ├── react-builder/skill.md
│   ├── refactor/skill.md
│   ├── textual-master/skill.md
│   ├── tui-builder/skill.md
│   └── vue-builder/skill.md
├── tests/                         ← 41 test files (pytest)
├── tui/                           ← Textual TUI frontend
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                     ← WIDDXTUI App (Textual)
│   ├── app.tcss                   ← Textual CSS stylesheet
│   ├── chat_engine.py             ← Async chat worker for TUI
│   ├── commands.py                ← TUI command handler
│   ├── state.py                   ← TUI state object
│   ├── theme_util.py              ← Theme applicator
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── detail.py
│   │   ├── help.py
│   │   ├── memory_crud.py
│   │   ├── session_crud.py
│   │   ├── settings.py
│   │   ├── tool_detail.py
│   │   └── ubuntu_grid.py
│   └── widgets/
│       ├── __init__.py
│       ├── diff_viewer.py
│       └── header.py
├── vscode-extension/              ← VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts           ← Activation + commands
│   │   ├── panel.ts               ← WebviewView panel (chat UI)
│   │   └── client.ts              ← WiddxClient (HTTP + WebSocket)
│   ├── out/                       ← Compiled JS (committed)
│   ├── package.json
│   └── tsconfig.json
├── config.json                    ← Default config (shipped with package)
├── pyproject.toml                 ← Package metadata + build config
├── Dockerfile
├── main.py                        ← Root redirect → scripts/main.py
├── api_server.py                  ← Root redirect → scripts/api_server.py
├── run_textual.py                 ← Root redirect → scripts/run_textual.py
├── _debug_brain.py                ← Debug script (should NOT be in repo)
├── _run_tests.py                  ← Debug test runner (should NOT be in repo)
├── widdx-tui.log                  ← Runtime log (should NOT be in repo)
└── skill.md                       ← Root-level skill file (dead/misplaced)
```

---

## Entry Points

| Command | Module | Function |
|---|---|---|
| `widdx` | `core.cli` | `run()` |
| `widdx-tui` | `tui.app` | `run_tui()` |
| `widdx-api` | `scripts.api_server` | `main()` |
| `widdx-web` | `scripts.web_app` | `main()` |
| `python -m core` | `core.__main__` | redirects to `scripts.web_app` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| TUI | Textual ≥ 1.0 |
| CLI | prompt_toolkit ≥ 3.0 + rich ≥ 13.0 |
| Web server | FastAPI + uvicorn + WebSocket |
| HTTP client | httpx ≥ 0.25 |
| Database | SQLite (via stdlib `sqlite3`) |
| AI Providers | Ollama, OpenAI-compatible, DeepSeek, GGUF (llama-cpp) |
| MCP | stdio-based process spawn |
| Gateway | python-telegram-bot, discord.py |
| Voice | edge-tts |
| VS Code extension | TypeScript |
| CI | GitHub Actions |
| Build | setuptools (pyproject.toml) |
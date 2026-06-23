# CLAUDE.md — WIDDX Nexus v3.0.0

> **AI Agent Guidance File** — Read this before working on this project.

---

## Project Identity

**WIDDX Nexus** is a **Terminal AI Operating System** — a multi-provider, multi-agent, multi-channel AI workspace that wraps any LLM with tools, memory, scheduling, sandboxing, and delegation to turn even weak/free models into powerful autonomous engineering assistants.

- **Version:** 3.1.0
- **Author:** MUHAMMAD MUSLIH ([widdx.com](https://widdx.com)) — Made in Palestine 🇵🇸
- **License:** MIT
- **Python:** ≥3.10
- **Package:** `widdx-nexus` (on PyPI)
- **Tests:** 268 passing (41 test files)

## Core Philosophy

> **Weak model + strong tools + intelligent system = strong model.**

The model itself doesn't matter as much as the intelligence layer wrapped around it. WIDDX Nexus provides that layer: task analysis, routing, decomposition, tool access, sandboxed execution, verification, memory, scheduling, and multi-platform delivery.

---

## Architecture Overview

```
Entry Points (4)     CLI (widdx)  │  TUI (widdx-tui)  │  Web (widdx-web)  │  API (widdx-api)
                            │              │                    │
                            └──────────────┼────────────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │     Chat Handler         │
                              │  (UIL Brain Pipeline)    │
                              │  analyze → route → plan  │
                              │  → execute → verify      │
                              │  → knowledge → feedback  │
                              └────────────┬────────────┘
                                           │
              ┌────────────────────────────┼──────────────────────────┐
              │                            │                          │
    ┌─────────▼────────┐      ┌───────────▼──────────┐     ┌─────────▼──────────┐
    │   LLM Providers   │      │    Tool System        │     │   MCP Client       │
    │ OpenCode Zen (free)│     │ bash, read, write,    │     │ 6 default servers  │
    │ Ollama (local)    │      │ edit, grep, glob,     │     │ filesystem, memory │
    │ DeepSeek          │      │ web_fetch, validate   │     │ playwright, fetch  │
    │ OpenAI-compatible │      │ + security guard      │     │ sqlite, seq-think  │
    │ GGUF (llama-cpp)  │      └──────────────────────┘     └────────────────────┘
    └──────────────────┘
              │
    ┌─────────┼──────────────────────────────────────────────────────────┐
    │         │              Supporting Subsystems                        │
    │  ┌──────▼──────┐ ┌──────────────┐ ┌────────────┐ ┌──────────────┐ │
    │  │ Memory (2-tier)│ │ Cron Scheduler│ │ Background │ │ Delegation   │ │
    │  │ global+project │ │ SQLite-backed │ │ Task Mgr   │ │ Sub-agents   │ │
    │  └─────────────┘ └──────────────┘ └────────────┘ └──────────────┘ │
    │  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────────┐ │
    │  │ Gateway      │ │ Skills (16)  │ │ Sandbox     │ │ Permissions  │ │
    │  │ Telegram+Discord│ │ prompt tmpl  │ │ WSL/Docker  │ │ 4 levels     │ │
    │  └─────────────┘ └──────────────┘ └────────────┘ └──────────────┘ │
    └────────────────────────────────────────────────────────────────────┘
```

### Key Directories

| Directory | Role | Language |
|-----------|------|----------|
| `core/` | **Engine** — all business logic (80+ files) | Python |
| `core/uil/` | **Unified Intelligence Layer** — 7-stage cognitive pipeline | Python |
| `core/providers/` | **LLM Provider** abstraction (6 providers) | Python |
| `core/mcp/` | **MCP client** — JSON-RPC over stdio | Python |
| `core/cron/` | **Cron scheduler** — background task scheduling | Python |
| `core/gateway/` | **Multi-channel** — Telegram + Discord adapters | Python |
| `core/agents/` | **Agent executors** — AutonomousAgent + ExpertTeam | Python |
| `cli/` | **Terminal CLI** (rich + prompt_toolkit) | Python |
| `tui/` | **Textual TUI** (textual framework) | Python |
| `scripts/` | **Web UI + API Server** (FastAPI + WebSocket) | Python |
| `scripts/static/` | **Frontend SPA** | JS/HTML/CSS |
| `skills/` | **Skill templates** (16 skills) | Markdown |
| `tests/` | **Test suite** (41 files, 268 tests) | Python |
| `.widdx/` | **Local config & data** (gitignored) | JSON/SQLite |

---

## How to Run

### Entry Points (defined in `pyproject.toml`)

| Command | What It Does |
|---------|-------------|
| `widdx` | Launch CLI terminal interface (primary) |
| `widdx-tui` | Launch Textual TUI (deprecated but functional) |
| `widdx-web` | Start Web UI at `http://localhost:8000` |
| `widdx-api` | Start REST API server |

### Development Setup

```bash
git clone https://github.com/widdx1990/widdx-nexus
cd widdx-nexus
pip install -e ".[dev,api]"
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_verifier.py -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Integration test
python tests/run_integration_test.py
```

### Config Files (resolution order)

1. `.widdx/config.json` (project-local, writable)
2. `config.json` (bare in CWD, writable)
3. `<install_dir>/config.json` (bundled default, read-only)

API keys are stored in **environment variables** (`WIDDX_API_KEY_<PROVIDER>`), never in config files.

---

## Code Style — Critical Rules

From `CODING_STANDARDS.md` — these are **non-negotiable**:

### L1-L5: Fundamental Laws
- **L1:** One purpose per file. If a file does 2 unrelated things, split it.
- **L2:** All public functions MUST have type hints.
- **L3:** All public functions MUST have Google-style docstrings.
- **L4:** NEVER use bare `except:` or `except: pass`. Always `except SpecificError:` with logging.
- **L5:** No wildcard imports (`from x import *`). Explicit imports only.

### S1-S3: Structure
- **S1:** Import order — stdlib → third-party → project modules, each group alphabetized.
- **S2:** Files must not exceed 500 lines (soft limit). Break up if approaching.
- **S3:** ALL names in snake_case (files, functions, variables). Classes in PascalCase.

### U1-U3: UIL Pipeline Contract
- **U1:** All executors must implement the `execute(context: ExecutionContext) -> ExecutionResult` interface.
- **U2:** `brain.py` must never call provider methods directly — always through executors.
- **U3:** Every UIL stage must be independently unit-testable.

### SEC1-SEC3: Security
- **SEC1:** All subprocess calls go through `core/sandbox.py` or `core/guard.py`.
- **SEC2:** API keys must use `keychain.py` (environment variables), never stored in files.
- **SEC3:** Permission checks before any destructive operation.

### P1-P3: Performance
- **P1:** No LLM calls inside loops.
- **P2:** Use the retry pattern from `providers.py`, not custom retry logic.
- **P3:** Use `logging` module, not `print()`.

---

## UIL Pipeline (The Brain)

The Unified Intelligence Layer is a 7-stage pipeline in `core/uil/`:

```
User Input
    │
    ▼
[1] Analyzer (analyzer.py)     — LLM + keyword classification
    │                             Output: ClassificationResult (TaskType, Domain, Confidence)
    ▼
[2] Router (router.py)          — Deterministic TaskType → ExecutionMode mapping
    │                             Output: RoutingDecision (mode, filtered tools)
    ▼
[3] Planner (planner.py)        — Rule-based task decomposition (no LLM)
    │                             Output: ExecutionPlan (steps)
    ▼
[4] Executor (executors.py +    — Delegates to AutonomousAgent / ExpertTeam / DirectTool
    agents/executor_adapter.py)   Output: ExecutionResult
    │
    ▼
[5] Verifier (verifier.py)      — Quality checks (HTML, Python, Bash, Code verifiers)
    │                             Output: VerificationReport with findings
    ▼
[6] Knowledge (knowledge.py)    — Persists outcome to .widdx/knowledge.json
    │                             Output: ExecutionRecord
    ▼
[7] Feedback (brain.py retry)   — If verification fails, auto-retry with fix instructions
    │
    ▼
Final Result → User
```

### Task Types (from `core/uil/contract.py`)
`CODE_READ`, `CODE_WRITE`, `CODE_MODIFY`, `CODE_REVIEW`, `RESEARCH`, `BROWSER`, `DATABASE`, `REASONING`, `CHAT`, `FILE_OPS`, `SYSTEM`, `COMPLEX`, `UNKNOWN`

### Execution Modes
`SIMPLE_CHAT`, `AUTONOMOUS`, `EXPERT_TEAM`, `DIRECT_TOOL`

---

## Key Files Map

### Core Engine (`core/`)

| File | What It Does |
|------|-------------|
| `uil/brain.py` | UIL orchestrator — main pipeline driver |
| `uil/analyzer.py` | Task classification (LLM + keyword) |
| `uil/router.py` | Decision routing (task type → execution mode) |
| `uil/planner.py` | Task decomposition |
| `uil/verifier.py` | Post-execution quality verification |
| `uil/knowledge.py` | Persistent execution record keeper |
| `uil/contract.py` | All dataclasses, enums, type definitions |
| `providers/providers.py` | All 6 LLM providers in one file |
| `tools.py` | Tool definitions + execution + security patterns |
| `mcp/client.py` | MCP JSON-RPC client (subprocess-based) |
| `agents/agent.py` | AutonomousAgent — tool-calling loop |
| `agents/expert.py` | ExpertTeam — 4-agent pipeline (Orch→Research→Code→Review) |
| `agents/executor_adapter.py` | Bridge between UIL contracts and agent code |
| `memory.py` | Two-tier markdown memory (global + project) |
| `chat.py` | Conversation loop, tool processing, streaming display |
| `sandbox.py` | Cross-platform sandboxed command execution |
| `guard.py` | Dangerous command pattern detection |
| `config/settings.py` | Configuration loader/saver |
| `config/keychain.py` | Secure API key storage (env vars) |

### Entry Points

| File | Role |
|------|------|
| `cli/app.py` | CLI main loop — the primary interface |
| `cli/commands.py` | 27 slash command handlers |
| `core/cli.py` | Entry point for `widdx` command |
| `scripts/web/server.py` | FastAPI app — 60+ endpoints + WebSocket |
| `scripts/web/chat.py` | Web chat handler wrapping UIL Brain |
| `scripts/web/dashboard.py` | System dashboard aggregator |
| `tui/app.py` | Textual TUI app |

---

## Provider Pattern

All providers extend `Provider` base class (`core/providers/providers.py`):

```python
class Provider:
    name: str
    model: str
    base_url: str
    api_key: str
    timeout: int

    def chat(self, messages, tools=None) -> Generator[dict, None, None]:
        """Streaming generator yielding {"type": "content"|"reasoning"|"tool_use"|"done"}"""
        ...

    def chat_sync(self, messages, tools=None) -> dict:
        """Blocking call returning complete response."""
        ...

    @staticmethod
    def build_tools_schema(tools) -> list[dict]:
        """Convert WIDDX tool defs to OpenAI function-calling format."""
        ...
```

Current providers: `OllamaProvider`, `OpenCodeZenProvider`, `DeepSeekProvider`, `OpenAICompatibleProvider`, `GGUFProvider`.

The factory function `create_provider(name, model)` instantiates the right provider. Fallback: if one fails, the next is tried.

---

## Tool System Pattern

Tools are defined as dictionaries in `TOOL_DEFINITIONS` (`core/tools.py`):

```python
TOOL_DEFINITIONS = [
    {"name": "bash", "description": "Execute shell command", "parameters": {...}},
    {"name": "read", "description": "Read file contents", "parameters": {...}},
    # ... more tools
]
```

Handlers are registered in `_TOOL_MAP: dict[str, callable]`. Dynamic tools can be added via `register_tool(name, definition, handler)`.

Security: `_DANGEROUS_PATTERNS` regex list blocks `rm -rf`, `dd`, `chmod 777`, `shutdown`, etc. The guard runs BEFORE execution.

---

## Internationalization / Arabic Notes

- The project has **full RTL support** for Arabic (via `python-bidi` in TUI, CSS `dir="rtl"` in Web UI)
- All user-facing documentation is originally in Arabic; English translations may exist
- String handling: Arabic strings use Unicode escapes or raw Arabic text (both acceptable)
- Frontend i18n: `scripts/static/js/lang.js` — bilingual engine (en/ar)
- Coding standards include Arabic-specific rules (A1-A2 in CODING_STANDARDS.md)

---

## Git Conventions

- **Branch naming:** `feature/description`, `fix/description`, `release/version`
- **Commit messages:** descriptive, in English or Arabic. End with `Co-Authored-By: Claude <noreply@anthropic.com>` when AI-assisted.
- **Auto-commit:** Project has auto-commit enabled after successful tool execution (via `core/auto_commit.py`)
- **Don't commit:** `.widdx/` (local data), `.pytest_cache/`, `node_modules/`

---

## Common Pitfalls

1. **Don't add new provider API calls directly** — always go through `chat.py` or UIL executors
2. **The `sys.path.insert(0, ...)` pattern** in entry points is intentional — the project root must be on `sys.path`
3. **`core/__init__.py` is the public API surface** — re-exports 17 symbols. New public modules should be added here.
4. **`tools.py` is large** — new tools should be added to `_TOOL_DEFINITIONS` and `_TOOL_MAP`
5. **Session system is dual** — `database.py` (SQLite) + `session_v2.py`. Prefer `database.py` for new code.
6. **Async/sync inconsistency** — most code is synchronous; `api_server.py` uses asyncio. The `call_from_thread` pattern bridges them.
7. **Don't remove modules marked as "dead"** without checking `.widdx/DESIGN.md` — some are intentionally wired through `core/__init__.py`

---

## Dependencies

### Core (always required)
`rich`, `httpx`, `prompt_toolkit`, `pygments`, `python-bidi`

### Optional Groups
| Group | Packages | When Needed |
|-------|----------|------------|
| `dev` | pytest, pytest-asyncio, build, twine | Development |
| `api` | fastapi, uvicorn | Web UI / API server |
| `gguf` | llama-cpp-python | Local GGUF models |
| `voice` | edge-tts | Text-to-speech |
| `gateway` | python-telegram-bot, discord.py | Telegram/Discord |

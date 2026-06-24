# Dependency Graph — WIDDX Nexus

## External Dependencies

### Core (pyproject.toml — required)

| Package | Version | Purpose |
|---|---|---|
| `rich` | ≥ 13.0 | Terminal rendering (markdown, panels, progress) |
| `httpx` | ≥ 0.25 | Async HTTP client (provider API calls) |
| `textual` | ≥ 1.0 | TUI framework |
| `prompt_toolkit` | ≥ 3.0 | CLI input handling |
| `pygments` | ≥ 2.15 | Syntax highlighting |
| `python-bidi` | ≥ 0.6.0 | RTL (Arabic) text direction |

### Optional Extras

| Extra | Package | Purpose |
|---|---|---|
| `api` | `fastapi ≥ 0.110` | REST API + Web UI server |
| `api` | `uvicorn[standard] ≥ 0.27` | ASGI server |
| `gguf` | `llama-cpp-python ≥ 0.2.0` | Local GGUF model inference |
| `voice` | `edge-tts` | Text-to-speech |
| `gateway` | `python-telegram-bot` | Telegram bot |
| `gateway` | `discord.py` | Discord bot |
| `dev` | `pytest ≥ 7.0`, `pytest-asyncio`, `pytest-cov`, `build`, `twine` | Testing + packaging |

### VS Code Extension

| Package | Version | Purpose |
|---|---|---|
| `@types/vscode` | ^1.85.0 | VS Code type definitions |
| `@types/node` | 20.x | Node.js type definitions |
| `typescript` | ^5.3.2 | TypeScript compiler |

### Implicit / Runtime Dependencies

These are imported conditionally and NOT in pyproject.toml:

| Package | Used In | Install Command |
|---|---|---|
| `pydantic` | `scripts/api_server.py` | `pip install pydantic` |
| `aiofiles` | `scripts/web/server.py` (implied by FastAPI) | included with fastapi |
| `PIL` / `pillow` | `core/vision.py` (if pipeline mode) | `pip install pillow` |
| `transformers` | `core/vision.py` (if pipeline mode) | `pip install transformers` |
| `torch` | `core/vision.py` (if pipeline mode) | `pip install torch` |
| `chromadb` | `core/vector_memory.py` | `pip install chromadb` |
| `flask` | `github-app/app.py` | `pip install flask` |
| `cryptography` | `core/mcp/client.py` | `pip install cryptography` |
| `ruff` | CI lint job | `pip install ruff` |

---

## Internal Module Dependency Graph

### core/uil/ (UIL Pipeline)

```
brain.py
  ├── analyzer.py        (TaskAnalyzer)
  ├── router.py          (DecisionRouter)
  ├── planner.py         (TaskPlanner)
  ├── contract.py        (all data types)
  ├── knowledge.py       (KnowledgeBase)
  ├── verifier.py        (Verifier)
  └── [lazy] agents/executor_adapter.py
            └── (EXECUTOR_MAP)
```

### core/providers/

```
providers.py  ← backward-compat facade (re-exports ALL below)
  ├── base.py            (Provider, ToolCall)
  ├── ollama.py          (OllamaProvider)      ← base.py
  ├── openai_compatible.py (OpenAICompat...)  ← base.py
  ├── opencode_zen.py    (OpenCodeZen...)      ← base.py
  ├── deepseek.py        (DeepSeek...)         ← openai_compatible.py
  ├── free_models.py     (fetch_free_models)
  ├── gguf.py            (scan_gguf, import)
  ├── gguf_provider.py   (GGUFDirect...)       ← base.py
  └── factory.py         (create_provider)     ← all above
```

### core/tools/ (Tool System)

```
tools/__init__.py
  ├── tools/security.py  (_DANGEROUS_PATTERNS)
  └── [runtime] core.providers.providers (create_provider for agent-in-tool)
```

### core/agents/

```
agents/agent.py
  ├── core.tools        (execute)
  ├── core.skills       (skill_manager)
  ├── core.chat         (display helpers)
  └── core.providers.providers (estimate_turn_cost)

agents/executor_adapter.py
  ├── core.agents.agent  (AutonomousAgent)
  ├── core.agents.expert (ExpertAgent)
  ├── core.chat          (run_chat_turn)
  └── core.workflow      (WorkflowExecutor)
```

### core/config/

```
settings.py       ← standalone (only stdlib)
keychain.py       ← standalone (only stdlib + base64)
__init__.py       ← re-exports settings + keychain
```

### core/gateway/

```
__init__.py
  ├── telegram.py  ← [optional] python-telegram-bot
  └── discord.py   ← [optional] discord.py
```

### scripts/web/

```
server.py
  ├── scripts/web/chat.py     (ChatHandler)
  │     └── core/uil/brain.py (UIL)
  ├── scripts/web/sandbox.py  (SandboxHandler)
  │     └── core/sandbox.py
  └── scripts/web/dashboard/  (Dashboard)
        ├── _mixin_core.py
        ├── _mixin_scheduler.py
        ├── _mixin_storage.py
        ├── _mixin_gateway.py
        ├── _mixin_settings.py
        └── _mixin_devops.py
```

---

## Confirmed Circular Dependencies

> **Two confirmed circular import pairs found by static analysis.**

### Circular 1: `core.plugin_loader` ↔ `core.skills`

```
core/plugin_loader.py (lines 203, 223, 242, 283, 304)
    from core.skills import skill_manager

core/skills.py (line 312)
    from core.plugin_loader import get_hot_reloader
```

**Impact:** Both modules use deferred imports (inside functions/methods) so Python does not crash at import time. However, this creates tight coupling where either module cannot be safely refactored without checking the other. Any change to module-level code in either file can cause an `ImportError` at runtime if called before both are fully initialized.

### Circular 2: `core.sandbox` ↔ `core.engine_adapters`

```
core/sandbox.py (line 573)
    from core.engine_adapters import engine_enabled, adapt_container_result

core/engine_adapters.py (line 22)
    from core.sandbox import sandbox

core/engine_adapters.py (line 183)
    from core.sandbox import SandboxResult
```

**Impact:** Same deferred pattern saves from crash, but creates mutual dependency that complicates testing and module loading order.

---

## Dependency Fan-Out (most-imported modules)

| Module | Imported By (approx.) | Risk |
|---|---|---|
| `core.providers.providers` | 10+ files | HIGH — any change breaks many files |
| `core.tools` | 8+ files | HIGH |
| `core.config.settings` | 7+ files | MEDIUM |
| `core._path` | 6+ files | LOW (simple utility) |
| `core.uil.contract` | 5+ files | HIGH — changing contracts breaks pipeline |
| `core.chat` | 4+ files | MEDIUM |
| `core.skills` | 4+ files | MEDIUM (circular risk) |

---

## Import Chain: User Message → LLM Call

```
User types message
    └── cli/app.py: CLIApp.run()
           └── core/commands.py: dispatch()
                  └── core/chat.py: run_chat_turn()  OR
                  └── core/uil/brain.py: UIL.process()
                         └── core/agents/agent.py: AutonomousAgent.run()
                                └── core/providers/providers.py: Provider.chat()
                                       └── httpx.AsyncClient.post(base_url + "/chat/completions")
```

---

## MCP Dependency Chain

```
config.json → mcp_servers[]
    └── core/mcp/client.py: MCPClientManager
           ├── subprocess.Popen("node server.js")
           ├── stdin/stdout JSON-RPC 2.0
           └── tools/TOOL_DEFINITIONS merged with core tools
```

---

## Node.js Dependencies (vscode-extension)

```
package.json (vscode-extension)
    ├── @types/vscode   ^1.85.0
    ├── @types/node     20.x
    └── typescript      ^5.3.2

package.json (root — MCP servers for config.json)
    └── @modelcontextprotocol/server-filesystem
        @modelcontextprotocol/server-memory
        @modelcontextprotocol/server-sequential-thinking
        @playwright/mcp
    (node_modules NOT shipped — must be npm install'd separately)
```

---

## Feature Flag Dependencies (v4.0 Engine)

```
Environment Variable      Module Enabled
─────────────────────────────────────────
WIDDX_ENGINE_CLASSIFIER   core.intelligence.classifier
WIDDX_ENGINE_PLANNER      core.intelligence.planner
WIDDX_ENGINE_VALIDATION   core.validation.runner
WIDDX_ENGINE_ISOLATION    core.isolation.container
WIDDX_ENGINE_ARBITER      core.engine_arbiter
```

All accessed via `engine_enabled(name)` in `core/engine_adapters.py`. The entire v4.0 layer is off by default and degrades gracefully if any import fails.
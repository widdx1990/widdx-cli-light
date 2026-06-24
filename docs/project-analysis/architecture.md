# Architecture — WIDDX Nexus

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTENDS                            │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌────────────┐  │
│  │  CLI    │  │   TUI   │  │  Web UI   │  │  VSCode    │  │
│  │cli/app  │  │tui/app  │  │(SPA+WS)  │  │ Extension  │  │
│  └────┬────┘  └────┬────┘  └─────┬─────┘  └─────┬──────┘  │
└───────┼─────────────┼─────────────┼───────────────┼─────────┘
        │             │             │               │
        ▼             ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                     ENTRY ORCHESTRATORS                     │
│  core/cli.py    tui/chat_engine  scripts/web/chat.py        │
│  core/commands  tui/commands     scripts/web/server.py      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED INTELLIGENCE LAYER (UIL)               │
│                                                             │
│  UnifiedIntelligenceLayer (core/uil/brain.py)               │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Analyzer │→ │  Router  │→ │ Planner  │→ │ Executor  │  │
│  │(classify)│  │(routing) │  │(plan)    │  │(run task) │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────┬─────┘  │
│                                                   │         │
│  ┌──────────┐  ┌──────────┐                       ▼         │
│  │Knowledge │← │ Verifier │←──────────────── Result        │
│  │(record)  │  │(quality) │                                 │
│  └──────────┘  └──────────┘                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  EXECUTORS  │ │  PROVIDERS  │ │   TOOLS     │
    │ (agents/    │ │ (LLM APIs)  │ │ (file/bash/ │
    │  executor_  │ │             │ │  web/code)  │
    │  adapter)   │ │ Ollama      │ │             │
    │             │ │ OpenAI      │ │ ~20 built-in│
    │ DIRECT_CHAT │ │ DeepSeek    │ │ + MCP tools │
    │ AGENT       │ │ GGUF        │ │ + dynamic   │
    │ CODE_REVIEW │ │ OpenCodeZen │ │ skills      │
    │ RESEARCH    │ └─────────────┘ └─────────────┘
    │ WORKFLOW    │
    └─────────────┘
```

---

## UIL Pipeline (core/uil/)

The UIL is the cognitive heart of WIDDX. Every user message flows through this pipeline:

```
user_input
    │
    ▼
[1] TaskAnalyzer.analyze()
    → ClassificationResult:
      task_type, domain, complexity,
      confidence, detected_features
    │
    ▼
[2] DecisionRouter.route()
    → RoutingDecision:
      plan (mode, steps, tools_subset)
      confidence, reasoning
    │
    ▼
[3] TaskPlanner.plan()         ← optional cognitive enhancer
    → enriched plan
    │
    ▼
[4] _resolve_executor(mode)
    → callable executor from EXECUTOR_MAP
    │
    ▼
[5] executor(context) → ExecutionResult
    (one of: direct_chat, agent_loop,
     code_review, research, workflow, etc.)
    │
    ▼
[6] Verifier.verify(result)
    → VerificationReport (findings, severity)
    │
    ▼
[7] KnowledgeBase.record(outcome)
    → persists to .widdx/knowledge.json
    │
    ▼
ExecutionResult → caller
```

### v4.0 Engine Overlay

Added on top of the UIL without breaking it:

```
UIL Analysis Step
    │
    ├── OLD: analyzer.analyze()      (keyword/heuristic)
    │
    ├── NEW: intelligence.classify() (TF-IDF + learned patterns)
    │         ← feature-flagged via WIDDX_ENGINE_* env vars
    │
    └── ARBITER: engine_arbiter.py  (when both disagree)
               ← runs BOTH, validates BOTH, picks winner
               ← engine_trust.py accumulates trust over time
```

---

## Execution Modes (ExecutionMode enum)

| Mode | Handler | Description |
|---|---|---|
| `DIRECT_CHAT` | `_exec_direct_chat` | Single LLM call, no tools |
| `AGENT` | `_exec_agent` | AutonomousAgent tool-calling loop |
| `CODE_REVIEW` | `_exec_code_review` | Specialized code review agent |
| `RESEARCH` | `_exec_research` | Multi-step research agent |
| `WORKFLOW` | `_exec_workflow` | Structured multi-step workflow |
| `DELEGATION` | `_exec_delegation` | Sub-agent delegation |
| `BACKGROUND` | `_exec_background` | Async background task |
| `EXPERT` | `_exec_expert` | Domain expert agent |

---

## Provider Architecture

```
Provider (ABC — core/providers/base.py)
    │
    ├── OllamaProvider           ← Local Ollama server
    ├── OpenAICompatibleProvider ← Any OpenAI-compatible API
    ├── OpenCodeZenProvider      ← WIDDX hosted proxy
    ├── DeepSeekProvider         ← DeepSeek API (extends OpenAI-compat)
    └── GGUFDirectProvider       ← llama-cpp-python local inference

All providers implement:
  .chat(messages, tools)        → streaming generator of str chunks
  .chat_sync(messages, tools)   → str (full response)
  .list_models()                → list of model names

Factory: create_provider(cfg) → Provider
Resolution: resolve_model(name) → (provider_type, model_name)
```

---

## Database Architecture

Single SQLite file at `.widdx/widdx.db` (per-project).

```
sessions
  ├── id (PK)
  ├── name
  ├── branch
  ├── created_at, updated_at (Unix timestamps)
  └── metadata (JSON blob)

messages
  ├── id (PK)
  ├── session_id (FK → sessions.id CASCADE)
  ├── role (user | assistant | tool | system)
  ├── content
  ├── tool_calls (JSON)
  └── timestamp

memories
  ├── id (PK)
  ├── name, description, content
  ├── memory_type
  ├── tags (JSON array)
  └── created_at, updated_at

provider_stats
  ├── id (PK, autoincrement)
  ├── provider_name, model_name (UNIQUE)
  ├── success_count, failure_count
  ├── avg_response_time
  └── last_used
```

---

## MCP Architecture

```
MCPClientManager (core/mcp/client.py)
    │
    ├── Reads servers from config.json → mcp_servers[]
    ├── Spawns each as a subprocess (stdio transport)
    │     command: "node path/to/server.js"
    │     or:      "uvx mcp-server-fetch"
    │
    ├── Communicates via JSON-RPC 2.0 over stdin/stdout
    │
    └── Returns tool definitions → TOOL_DEFINITIONS (merged)

Supported MCP servers (in shipped config.json):
  - filesystem    (node)
  - memory        (node)
  - fetch         (uvx)
  - sequential-thinking (node)
  - playwright    (node)
  - sqlite        (uvx)
```

---

## Web UI Architecture

```
Browser (SPA)
    │ WebSocket ws://host/ws
    │ HTTP     http://host/api/*
    ▼
FastAPI app (scripts/web/server.py)
    │
    ├── /                    → index.html (static)
    ├── /static/*            → css, js assets
    ├── /ws                  → WebSocket (streaming chat)
    ├── /api/chat            → POST (non-streaming chat)
    ├── /api/sandbox/*       → Terminal + file ops
    ├── /api/dashboard/*     → System status + management
    └── /api/*               → 72 total REST endpoints
         │
         ├── ChatHandler (scripts/web/chat.py)
         │     └── UnifiedIntelligenceLayer
         │           └── All providers + tools
         │
         ├── SandboxHandler (scripts/web/sandbox.py)
         │     └── SandboxExecutor
         │
         └── Dashboard (scripts/web/dashboard/)
               └── 6 mixin classes (one per subsystem)
```

---

## VS Code Extension Architecture

```
extension.ts (activate)
    ├── Creates WiddxClient (HTTP + WebSocket to widdx-web)
    ├── Registers ChatPanelProvider (WebviewView sidebar)
    ├── Registers commands:
    │     widdx-cortex.openChat
    │     widdx-cortex.newSession
    │     widdx-cortex.sendSelection
    │     widdx-cortex.explainCode
    │     widdx-cortex.fixCode
    └── Starts health-check interval (every 30s)

panel.ts
    └── WebView HTML + message bridge → WiddxClient

client.ts (WiddxClient)
    ├── GET/POST to WIDDX API (/api/chat, /api/sessions, etc.)
    └── WebSocket for streaming
```

---

## Sandbox Architecture

```
SandboxExecutor (core/sandbox.py)
    │
    ├── detect_best_mode()
    │     Windows: WSL > Docker > process
    │     Linux:   cgroups > Docker > process
    │     macOS:   sandbox-exec > Docker > process
    │
    ├── execute(command, timeout, limits)
    │     → SandboxResult(stdout, stderr, exit_code, files_created, ...)
    │
    └── ResourceLimits:
          max_cpu_seconds: 60
          max_memory_mb:   512
          max_file_size_mb: 100
          allow_network:   True
```

---

## Gateway Architecture

```
GatewayCore (core/gateway/__init__.py)
    │
    ├── start_platform("telegram", token=...) → TelegramGateway
    ├── start_platform("discord",  token=...) → DiscordGateway
    │
    ├── set_handler(fn: str → str)
    │     fn receives Message, returns Reply text
    │
    └── Both gateways run in background threads
          → call handler(msg) → send_reply(reply)
```

---

## Config Resolution Order

```
1. .widdx/config.json   (project-local — highest priority)
2. config.json           (CWD bare)
3. <install>/config.json (bundled default — read-only)

API keys: .widdx/apikeys.json (XOR-obfuscated, never in config.json)
Engine trust: .widdx/engine_trust.json
Knowledge: .widdx/knowledge.json (UIL outcomes)
Database: .widdx/widdx.db (SQLite)
```

---

## Key Design Patterns

| Pattern | Where Used |
|---|---|
| Mixin composition | `Dashboard` class (6 mixins) |
| Lazy singleton | `get_chat()`, `get_sandbox()`, `get_mcp_manager()` |
| Feature flags | `engine_enabled(name)` via env vars |
| Backward-compat facade | `providers/providers.py` re-exports split modules |
| Trust accumulation | `engine_trust.py` promotes engines automatically |
| Hot reload | `plugin_loader.py` watches for file changes |
| Adapter pattern | `engine_adapters.py` bridges old ↔ new types |
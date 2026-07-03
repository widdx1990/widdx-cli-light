# WIDDX Nexus

> **Autonomous Software Engineering Platform** — AI that plans, builds, tests, fixes, documents, and learns. Without you.

Created by [MUHAMMAD MUSLIH](https://widdx.com) — Founder & CEO of WIDDX

---

## What is WIDDX?

WIDDX is **not a chatbot**. It is a multi-agent autonomous engineering system with **55+ integrated subsystems** organized in a **5-level execution hierarchy**. Give it a goal — it plans, writes code, tests it, fixes errors, updates documentation, records every decision, and keeps going until the job is done.

```
                     ┌─────────────────────────────────────────┐
                     │           USER GOAL (English)            │
                     └─────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       ▼                       │
              │         ┌─────────────────────────┐           │
              │         │   StateManager (7 ctx)   │           │
              │         └─────────────────────────┘           │
              │                       │                       │
              │         ┌─────────────┴─────────────┐         │
              │         │    UIL Brain Pipeline      │         │
              │         │  Analyze→Route→Plan→Exec   │         │
              │         │  →Verify→Learn             │         │
              │         └─────────────┬─────────────┘         │
              │                       │                       │
     ┌────────┴────────┐   ┌─────────┴──────────┐   ┌────────┴────────┐
     │  L1 DIRECT_TOOL │   │  L2 SIMPLE_CHAT     │   │ L3 AUTONOMOUS  │
     │  (stateless)    │   │  (LLM-only)         │   │ (agent loop)   │
     └─────────────────┘   └─────────────────────┘   └────────┬────────┘
                                                              │
                    ┌─────────────────────────────────────────┼─────────┐
                    │               L3 Agent Loop             │         │
                    │  ┌─────┐  ┌──────┐  ┌──────┐  ┌──────┐ │         │
                    │  │ LLM │→│ Tool │→│Verify│→│ Fix  │ │         │
                    │  │ Call│  │ Exec │  │Check │  │ Loop │ │         │
                    │  └─────┘  └──────┘  └──────┘  └──────┘ │         │
                    └─────────────────────────────────────────┘         │
                                                                        │
     ┌───────────────────┐  ┌────────────────┐  ┌───────────────────┐  │
     │ L4 EXPERT_TEAM    │  │ L5 CREATIVE    │  │ Execution State   │  │
     │ 5 agents parallel │  │ Strategy Mode  │  │ Controller (ESC)  │  │
     │ Orchestrator      │  │ LLM invents    │  │ L1→L5 state       │  │
     │ Researcher+Coder  │  │ new strategies │  │ machine           │  │
     │ Reviewer+Debugger │  │ when all known │  │ + World Model     │  │
     └───────────────────┘  │ exhausted      │  │ + Constraint Eng  │  │
                            └────────────────┘  │ + AIL Generator   │  │
                                                └───────────────────┘  │
                                                                        │
     ┌─────────────────────────────────────────────────────────────────┐│
     │              Cross-Cutting Systems                             ││
     │  ┌────────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌───────┐ ┌───────────┐  ││
     │  │Memory  │ │  KG  │ │ ADR  │ │Plan │ │ DocSync│ │SelfImprove│  ││
     │  │V4+Ver  │ │Graph │ │Decis.│ │     │ │        │ │           │  ││
     │  └────────┘ └──────┘ └──────┘ └────┘ └───────┘ └───────────┘  ││
     │  ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌──────────┐  ││
     │  │Influence│ │WebLearn│ │Stuck │ │PreFail│ │Self │ │Recursive │  ││
     │  │Engine  │ │  Loop  │ │Detect│ │Sim   │ │Correct│ │SubAgents │  ││
     │  └────────┘ └────────┘ └──────┘ └──────┘ └────┘ └──────────┘  ││
     └─────────────────────────────────────────────────────────────────┘│
      ┌─────────────────────────────────────────────────────────────────┘
      ▼
   ┌──────────────────────────────────────────────┐
   │   7 Providers  │  Pool Failover  │  Retry    │
   │   Sandbox      │  MCP Protocol   │  Cron     │
   └──────────────────────────────────────────────┘
```

---

## 🏗️ Architecture Layers

### L1 — Direct Tool (Stateless)

Fastest path. Single tool execution based on user input. Used for system commands, bash, and direct MCP tool calls.

### L2 — Simple Chat (LLM Only)

Standard chat interface. Single LLM turn with optional tool access for reading or simple tasks.

### L3 — Autonomous Agent (Agentic Loop)

```
Goal → Plan → [LLM → Tool → Verify → Fix] Loop → Summary
```

- **AutonomousAgent** manages a full tool-calling loop with checkpoint/resume capability.

- Automatic syntax validation after every write/edit (Python, JS).

- Intelligent loop detection and provider failover across 7+ providers.

### L4 — Expert Team (Adaptive Multi-Agent)

A sophisticated pipeline of specialized experts that scales based on task complexity:

- **Orchestrator**: Plans and coordinates the entire project.

- **Researcher & Coder**: Run in parallel for medium/complex tasks.

- **Reviewer**: Mandatory quality gate for all implementations.

- **Debugger**: Activated only when issues are found in complex tasks.

### Intelligence & ESC (Creative Mode)

While L1-L4 are primary execution modes, the **Execution State Controller (ESC)** and **Intelligence Engine** monitor performance. When standard strategies fail, the system triggers creative reasoning and pattern adaptation to find new solutions.

---

## 🧠 Core Pipeline (UIL Brain)

```
User Input
    │
    ▼
┌─────────────┐  ┌────────────────┐  ┌──────────────────┐
│  Analyzer   │→│    Router      │→│    Planner       │
│ Task type   │  │ L1-L5 mode    │  │ Task steps       │
│ Confidence  │  │ Provider pick  │  │ Dependencies     │
│ Complexity  │  │ Engine flags   │  │ Pattern match    │
└─────────────┘  └────────────────┘  └──────────────────┘
                      │                      │
                      ▼                      ▼
               ┌──────────────┐    ┌──────────────────┐
               │  Executor    │←──│  Plan            │
               │ Agent/Tool   │    │  Decomposition   │
               └──────┬───────┘    └──────────────────┘
                      │
                      ▼
               ┌──────────────┐
               │  Verifier    │←── Validation Engine
               │ Syntax check │    (syntax, runtime,
               │ Runtime run  │     quality scoring)
               │ Quality      │
               └──────┬───────┘
                      │
               ┌──────┴──────┐
               │             │
            Pass?          Fail?
               │             │
               ▼             ▼
           ┌────────┐  ┌──────────┐
           │ Learn  │  │ Fix Loop │  ← SelfCorrection
           │ Patterns│  │ (3 retry)│    (7 strategies)
           └────────┘  └──────────┘
```

---

## 🧩 55+ Integrated Systems

### Execution Systems (10)

| System | File | Description |
| --- | --- | --- |
| UIL Brain Pipeline | `core/uil/brain.py` | Analyze→Route→Plan→Execute→Verify→Learn |
| StateManager | `core/state_manager.py` | 7 context sources → unified prompt |
| AutonomyLoop | `core/autonomy_loop.py` | Execute→Verify→Fix→Continue cycle |
| AutonomousAgent | `core/agents/agent.py` | LLM loop with tool calling, checkpoint/resume |
| ExpertTeam | `core/agents/expert.py` | 5 agents: Orchestrator→Researcher→Coder→Reviewer→Debugger |
| Delegation | `core/delegation.py` | Parallel sub-agents for independent tasks |
| WorkflowEngine | `core/workflow.py` | Sequential + parallel + pipeline primitives |
| ExecutorAdapter | `core/agents/executor_adapter.py` | Bridges UIL contracts to Execution Modes |
| EngineArbiter | `core/engine_arbiter.py` | Routes tasks to engines (intelligence, validation, isolation) |
| spawn_agent | `core/tools/__init__.py` | Recursive agent creation (tree depth 3) |

### Execution State Controller (5)

| System | File | Description |
| --- | --- | --- |
| ESC | `core/execution_state_controller.py` | Deterministic L1→L5 state machine |
| WorldModel | `core/world_model.py` | Defines valid states, filters ESC actions |
| ConstraintEngine | `core/engine_arbiter.py` | Removes invalid options from state space |
| AIL Generator | `core/architecture/compiler.py` | Architecture Intelligence Layer — generates code structures |
| AIL PatternStore | `core/architecture/pattern_store.py` | Stores/scores architecture patterns |

### Intelligence Engine (6)

| System | File | Description |
| --- | --- | --- |
| DecisionEngine | `core/intelligence/decision_engine.py` | Learns optimal routing from execution history |
| Classifier | `core/intelligence/classifier.py` | TF-IDF + keyword task classification |
| Pattern Learner | `core/intelligence/learner.py` | Identifies software patterns (MVC, REST, etc.) |
| Embeddings | `core/intelligence/embeddings.py` | TF-IDF embedding + cosine similarity store |
| Planner | `core/intelligence/planner.py` | Decomposes tasks into ordered steps |
| TrustTracker | `core/engine_trust.py` | Tracks per-engine reliability over time |

### Learning & Adaptation (8)

| System | File | Description |
| --- | --- | --- |
| InfluenceEngine | `core/learning/pre_decision_force.py` | 3-tier: block/penalize/prefer decisions based on history |
| PreFailureSim | `core/learning/pre_failure_sim.py` | Predicts failure probability before execution |
| StuckDetector | `core/learning/stuck_detector.py` | 5 signal types: repetition, error loops, time, sentiment |
| StrategyShifter | `core/learning/pre_decision_force.py` | Auto-downgrades L4→L3 or L3→L2 when stuck |
| WebLearningLoop | `core/learning/web_learning.py` | Learns from web search results during tasks |
| PatternExtractor | `core/learning/pattern_extractor.py` | Extracts reusable patterns from successful executions |
| SelfCorrection | `core/self_correction.py` | 7 classified fix strategies with targeted repair |
| SelfImprove | `core/self_improve.py` | Tracks recurring errors, injects prevention rules |

### Memory & Knowledge (6)

| System | File | Description |
| --- | --- | --- |
| MemoryStore V4 | `core/memory.py` | Versioned facts with confidence, deprecation lifecycle |
| KnowledgeGraph | `core/knowledge_graph.py` | BFS graph of files→classes→functions→imports |
| VectorMemory | `core/vector_memory.py` | Ollama embedding + cosine similarity search |
| ADR | `core/adr.py` | Architecture Decision Records — prevents re-suggesting rejected solutions |
| DecisionLayer | `core/decision_layer.py` | Weighted: ADR(30%) + Memory(30%) + KG(20%) + Plan(20%) |
| RAG | `core/rag.py` | TF-IDF search across project docs |

### Validation Engine (4)

| System | File | Description |
| --- | --- | --- |
| Syntax Check | `core/validation/reporter.py` | Python/JS/HTML/Bash compile checks |
| Runtime Runner | `core/validation/runner.py` | Actually executes code, catches runtime errors |
| Quality Scorer | `core/validation/reporter.py` | Multi-signal: syntax×0.2 + runtime×0.5 + quality×0.3 |
| VerifyLoop | `core/verification/loop.py` | Verify→Fix→Retest cycle (up to 3 retries) |

### Provider System (7)

| System | File | Description |
| --- | --- | --- |
| ProviderPool | `core/provider_reliability.py` | Priority-based failover across 7 providers |
| ReliableProvider | `core/provider_reliability.py` | Wraps all providers with retry + backoff + checkpoint |
| OpenCode Zen | `core/providers/opencode_zen.py` | Free cloud, zero config |
| DeepSeek | `core/providers/deepseek.py` | API key, best tool-use |
| OpenAI Compatible | `core/providers/openai_compatible.py` | Any OpenAI-API model |
| Ollama | `core/providers/ollama.py` | Local, offline, privacy |
| GGUF Direct | `core/providers/gguf_provider.py`, `core/providers/gguf.py` | Quantized local models |

### Security & Isolation (5)

| System | File | Description |
| --- | --- | --- |
| SandboxExecutor | `core/sandbox.py` | Isolated command execution (3 OS) |
| CommandGuard | `core/guard.py` | Blocks rm -rf, fork bombs, disk formats |
| 4 Isolation Levels | `core/isolation/` | SILENT→STRICT→NORMAL→PERMISSIVE profiles |
| Rate Limiter | `scripts/web/server.py` | SQLite-backed, survives restarts |
| PermissionManager | `core/permissions.py` | Multi-level permission system |

### MCP & Tools (4)

| System | File | Description |
| --- | --- | --- |
| MCP Client | `core/mcp/client.py` | Model Context Protocol — connects to external tools |
| MCP Server Manager | `core/mcp/client.py` | Auto-discovers MCP servers from config |
| 18 Built-in Tools | `core/tools/__init__.py` | read, write, edit, bash, browser, grep, search, validate... |
| Plugin Loader | `core/plugin_loader.py` | Hot-reload third-party skill plugins |

### Persistence & State (4)

| System | File | Description |
| --- | --- | --- |
| CheckpointManager | `core/checkpoint.py` | Saves/restores agent state before every action |
| TokenBudget | `core/token_budget.py` | Tracks and limits token consumption |
| Database | `core/database.py` | SQLite session/message persistence with migrations |
| Cron Scheduler | `core/cron/scheduler.py` | Background job scheduling with persistence |

### Interfaces (4)

| System | Description |
| --- | --- |
| **Web UI** (FastAPI + WebSocket) | 80+ REST endpoints, real-time chat, dashboard, sandbox terminal |
| **CLI** (Rich) | Terminal chat with syntax highlighting, tool output, session management |
| **TUI** (Textual) | Full terminal UI with screens, panels, async widgets |
| **API** (FastAPI) | REST API with Bearer token auth, WebSocket streaming |

### Gateway & Communication (3)

| System | Description |
| --- | --- |
| Telegram Bot | `core/gateway/telegram.py` — Chat via Telegram |
| Discord Bot | `core/gateway/discord.py` — Chat via Discord |
| GatewayCore | `core/gateway/__init__.py` — Unified message routing |

---

## ⚡ Quick Start

```bash
# Install
pip install git+https://github.com/widdx1990/widdx-cli-light.git

# Or from source
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
make install     # or: pip install -e ".[api]"

# Launch
widdx-web       # Web UI → http://localhost:8000
widdx           # Terminal chat (Rich CLI )
widdx-tui       # Terminal UI (Textual)
widdx-api       # REST API server
```

**First run — no setup needed.** OpenCode Zen (free, no key) is the default.

---

## 🔧 Provider Setup

| Provider | Type | Key? | Tools | Streaming | Best For |
| --- | --- | --- | --- | --- | --- |
| **OpenCode Zen** | Cloud | Free | ✅ | ✅ | Zero-config start |
| **DeepSeek** | Cloud | API Key | ✅ | ✅ | Best tool-use |
| **OpenAI Compatible** | Cloud | API Key | ✅ | ✅ | Any OpenAI-API model |
| **Ollama** | Local | No | ✅ | ❌ | Privacy, offline |
| **GGUF Direct** | Local | No | ✅ | ✅ | Quantized models |
| **GGUF Legacy** | Local | No | ❌ | ❌ | Legacy support |
| **Free Models** | Discovery | No | ❌ | ❌ | Discovery only |

Provider failover is automatic — if one fails, the pool switches to the next available.

---

## 🛠️ Built-in Tools (18+)

| Tool | Description |
| --- | --- |
| `read` | Read files with line numbers and pagination |
| `write` | Create files (auto-creates parent directories) |
| `edit` | Surgical text replacement with diff preview |
| `bash` | Execute shell commands (sandboxed, guarded) |
| `browser_navigate` | Open URLs in Playwright browser |
| `browser_screenshot` | Take page screenshots |
| `validate` | Check file syntax (Python, JS, HTML) |
| `spawn_agent` | Create sub-agents for parallel work |
| `search` | Search project files by pattern |
| `grep` | Search file contents by regex |
| `memory_search` | Search learned facts |
| `memory_add` | Store a new fact |
| `finish` | Signal task completion |
| `ask_user` | Request human input |
| `think` | Internal reasoning log |
| `execute_with_skills` | Run a named skill |
| `web_search` | Google search via API |
| `web_fetch` | Get page content |

---

## 🧪 Development

```bash
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
make install-dev   # dev dependencies
make test          # 538 tests, 0 failures
make lint          # ruff: 0 errors
make typecheck     # mypy: 0 errors (171 files )
make clean         # reset to fresh state

# Architecture docs
docs/architecture/
  01-overview.md              # System identity, layers, numbers
  02-execution-flow.md        # Step-by-step request trace
  03-agents.md               # 9 agent types compared
  04-providers.md            # 7 providers, reliability layer
  05-memory-knowledge.md     # Memory, KG, ADR, DocSync, State
  06-api-endpoints.md        # All REST/WS endpoints
  07-development.md          # Patterns, adding providers/tools
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
| --- | --- |
| `ImportError: _ssl` | Use system Python (not venv with broken SSL) |
| `widdx-web not found` | `pip install -e ".[api]"` |
| `No module named fastapi` | `pip install fastapi uvicorn` |
| `401 Unauthorized` (API) | Set `WIDDX_API_KEY` env var |
| Provider not responding | Switch to opencode-zen (free, no key) in Settings |
| DeepSeek returns empty | Add API key in Settings → DeepSeek → Save |
| Agent stuck "Thinking" | Click Stop, restart server, agent resumes from checkpoint |
| Port already in use | WIDDX auto-increments to next available port |

---

## 📄 License

MIT — [LICENSE](LICENSE)

Created with 🇵🇸 by [MUHAMMAD MUSLIH](https://widdx.com)
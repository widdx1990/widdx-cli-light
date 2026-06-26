# WIDDX Nexus

> **Autonomous Software Engineering Platform** — AI that plans, builds, tests, fixes, documents, and learns. Without you.

Created by [MUHAMMAD MUSLIH](https://widdx.com) — Founder & CEO of WIDDX

---

## What is WIDDX?

WIDDX is not a chatbot. It's a **multi-agent autonomous engineering system**.
Give it a goal. It plans the work. It writes the code. It tests it. If something
breaks, it fixes it. It updates the documentation. It records every decision.
Then it keeps going until the job is done.

- **55 integrated systems**
- **9 agent types** (AutonomousAgent, ExpertTeam × 5, SubAgents, Delegation, Workflow)
- **7 LLM providers** with automatic failover
- **539 tests, 0 failures**

---

## ⚡ Install

### One command
```bash
pip install git+https://github.com/widdx1990/widdx-cli-light.git
```

### From source
```bash
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
pip install -e ".[api]"
```

### Requirements
- Python 3.10+
- Node.js (optional, for MCP browser tools)
- No GPU needed. No Docker needed. No API key needed for free tier.

---

## 🚀 Start

```bash
widdx-web       # Web UI → http://localhost:8000
widdx           # Terminal chat (Rich CLI)
widdx-tui       # Terminal UI (Textual)
widdx-api       # REST API server
```

---

## 🔧 Provider Setup

| Provider | Type | Key? | Tools | Streaming | Best For |
|----------|------|------|-------|-----------|----------|
| **OpenCode Zen** | Cloud | No (free) | ✅ | ✅ | Zero-config start |
| **DeepSeek** | Cloud | API Key | ✅ | ✅ | Best tool-use |
| **OpenAI Compatible** | Cloud | API Key | ✅ | ✅ | Any OpenAI-API model |
| **Ollama** | Local | No | ✅ | ❌ | Privacy, offline |
| **GGUF Direct** | Local | No | ✅ | ✅ | Quantized models |
| **GGUF Legacy** | Local | No | ❌ | ❌ | Legacy support |
| **Free Models** | Discovery | No | ❌ | ❌ | Discovery only |

**First run — no setup needed.** OpenCode Zen is the default. Just `widdx-web` and go.

To switch: Settings → Provider → pick one → enter key if needed → Save.

Any model without tool support still works — code extraction fallback handles it.

---

## 🧠 Capabilities

### Autonomous Execution
- **Single goal → complete project.** No human in the loop.
- Agent plans, writes code, runs it, tests it, fixes errors, updates docs.
- Survives restarts. Resumes from exact step where it stopped.
- Provider fails? Switches to backup automatically. You never notice.

### Multi-Agent System
| Agent | When | What |
|-------|------|------|
| **AutonomousAgent** | Every task | Main execution loop with tool calling |
| **ExpertTeam** | Complex projects | 5 specialized agents working sequentially |
| ↳ Orchestrator | Plans and coordinates | Breaks goal into steps |
| ↳ Researcher | Research tasks | Gathers information, reads docs |
| ↳ Coder | Implementation | Writes the actual code |
| ↳ Reviewer | Quality check | Reviews, finds issues |
| ↳ Debugger | Fix issues | Repairs what Reviewer found |
| **spawn_agent** | On demand | Creates sub-agents recursively (tree, depth 3) |
| **Delegation** | Parallel work | Multiple agents running simultaneously |

### Verification & Quality
- **Syntax check** — HTML, Python, JavaScript, Bash
- **Runtime validation** — Actually runs the code and catches errors
- **Verify → Fix → Retest loop** — Up to 3 retries with targeted fix strategies
- **SelfCorrection** — 7 classified error types with specific repair tactics
- Never says "done" until the code actually works

### Memory & Learning
- **Long-term memory** — Facts, preferences, fixes, patterns (versioned, confidence-scored)
- **Episodic memory** — Full conversation history (SQLite, survives restarts)
- **Semantic search** — TF-IDF vector search across memories
- **Auto-learning** — Extracts facts from conversations automatically
- **Deprecation lifecycle** — Old memories expire, confident ones persist
- **Memory Versioning** — Every fact has version, confidence, status, last_validated

### Project Understanding
- **KnowledgeGraph** — Builds a graph of your entire project (files → classes → functions → imports)
- **RepoMapper** — Maps dependencies between all files
- **Project Scanner** — Detects languages, frameworks, file counts
- **Project Docs** — Auto-creates PLAN, DESIGN, TASKS, ROADMAP for every project
- **DocSync** — Detects when documentation drifts from actual code

### Decision Intelligence
- **ADR (Architecture Decision Records)** — Records every decision and why. Prevents re-suggesting rejected solutions.
- **DecisionLayer** — Weighs ADR (30%) + Memory (30%) + KnowledgeGraph (20%) + Plan (20%) before every choice
- **SelfImprove** — Tracks recurring errors and injects prevention rules into future prompts

### Reliability
- **ProviderPool** — 7 providers with priority-based failover
- **Retry with backoff** — 2s, 4s, 8s delays on transient failures
- **Checkpoint/Resume** — State saved before every action. Never lose progress.
- **Code extraction fallback** — Even if the LLM won't use tools, code gets written
- **Atomic writes** — `.tmp` + `os.replace()` — never corrupt a file

### Security
- **Sandbox executor** — Isolated command execution (Windows/Linux/macOS)
- **Command guard** — Blocks `rm -rf /`, fork bombs, disk formats
- **4 isolation levels** — SILENT → STRICT → NORMAL → PERMISSIVE
- **API authentication** — Bearer token with empty-key rejection
- **Rate limiting** — SQLite-backed, survives restarts
- **Request size limit** — 1MB body cap (configurable)
- **Skill sandbox** — Third-party skills run with restricted builtins
- **API key encryption** — XOR-obfuscated storage, never in config files

---

## 📊 Architecture

```
User Goal
  │
  ▼
ChatHandler — Builds context from 7 sources
  │
  ▼
Brain Pipeline — Analyze → Route → Plan → Execute → Verify → Learn
  │
  ▼
AutonomousAgent — Calls LLM → executes tools → verifies → fixes → repeats
  │
  ├── Tools: write, bash, browser, spawn_agent, edit, read, validate...
  ├── Memory: versioned facts, session history
  ├── KG: project structure graph
  ├── ADR: architecture decisions
  └── State: persisted across restarts
```

Full architecture docs: [`docs/architecture/`](docs/architecture/)

---

## 🛠️ Built-in Tools (15+)

| Tool | Description |
|------|-------------|
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

---

## 🧪 Development

```bash
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
pip install -e ".[dev]"

# Run tests
pytest tests/ -q              # 539 tests, 0 failures
pytest tests/ -v              # Verbose output
pytest tests/test_memory.py   # Single test file

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
|---------|-----|
| `ImportError: _ssl` | Use system Python (not venv with broken SSL) |
| `widdx-web not found` | `pip install -e ".[api]"` first |
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

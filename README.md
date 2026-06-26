# WIDDX Nexus

> Autonomous Software Engineering Platform — Plan, Execute, Verify, Fix, Learn

Created by [MUHAMMAD MUSLIH](https://widdx.com) — Founder & CEO of WIDDX

---

## ⚡ One-Line Install

```bash
pip install git+https://github.com/widdx1990/widdx-cli-light.git
```

## 🚀 Run

```bash
widdx-web    # Web UI → http://localhost:8000
widdx        # CLI terminal chat
widdx-tui    # Textual TUI
widdx-api    # REST API server
```

## 🔧 First Run

No API key needed. The default provider is **OpenCode Zen** (free tier).

To use your own key:
1. Open http://localhost:8000
2. Go to Settings → Providers → DeepSeek
3. Enter your API key → Save

## 🧠 Capabilities

| Category | Features |
|----------|----------|
| **Autonomy** | AutonomousAgent, ExpertTeam (5 experts), Recursive Agent Spawning |
| **Planning** | Task analysis → routing → planning → execution → verification |
| **Verification** | Syntax + runtime validation, Verify→Fix→Retest loop, SelfCorrection |
| **Memory** | Long-term (versioned), episodic (SQLite), semantic (TF-IDF) |
| **Knowledge** | Project Graph (BFS), ADR records, Doc-Drift detection |
| **Persistence** | TaskState resume, Session SQLite, atomic writes |
| **Reliability** | ProviderPool failover, retry+backoff, checkpoint on failure |
| **Multi-Agent** | ExpertTeam (sequential), spawn_agent (recursive tree, depth 3) |
| **Decision** | Weighted: ADR 30% + Memory 30% + KG 20% + Plan 20% |

## 📦 Providers (7)

| Provider | Type | Key Required | Tools | Stream |
|----------|------|-------------|-------|--------|
| OpenCode Zen | Free cloud | No | ✅ | ✅ |
| DeepSeek | Cloud | API Key | ✅ | ✅ |
| OpenAI Compatible | Cloud | API Key | ✅ | ✅ |
| Ollama | Local | No | ✅ | ❌ |
| GGUF Direct | Local | No | ✅ | ✅ |
| GGUF Legacy | Local | No | ❌ | ❌ |
| Free Models | Discovery | No | ❌ | ❌ |

## 📊 Dev

```bash
pytest tests/          # 539 tests, 0 failures
docs/architecture/     # 7 architecture documents
```

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImportError: _ssl` | Use system Python, not venv with broken SSL |
| `widdx-web not found` | `pip install -e ".[api]"` first |
| `No module named fastapi` | `pip install fastapi uvicorn` |
| `401 Unauthorized` (API) | Set `WIDDX_API_KEY` env var |
| Provider not responding | Try opencode-zen (free, no key) in Settings |

## 📂 Project Structure

```
chat-tool/
├── core/          ← Engine (55 modules)
│   ├── uil/       ← Brain pipeline
│   ├── agents/    ← AutonomousAgent, ExpertTeam
│   ├── providers/ ← 7 LLM backends
│   └── tools/     ← 15+ built-in tools
├── scripts/       ← Web server + static frontend
├── cli/           ← Rich CLI
├── tui/           ← Textual TUI
├── tests/         ← 539 tests in 45 files
└── docs/          ← Full architecture docs
```

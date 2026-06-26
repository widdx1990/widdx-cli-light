# WIDDX Nexus

> AI Terminal Workspace — CLI, TUI, Web UI, REST API, VSCode Extension

Created by [MUHAMMAD MUSLIH](https://widdx.com) — Founder & CEO of WIDDX

---

## ⚡ One-Line Install

```bash
pip install git+https://github.com/widdx1990/widdx-cli-light.git
```

Or if you have the repo locally:
```bash
pip install -e ".[api]"
```

## 🪟 Windows One-Line (PowerShell)

```powershell
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

## 📦 Providers

| Provider | Type | Key Required |
|----------|------|-------------|
| OpenCode Zen | Free cloud | No |
| Ollama | Local | No |
| DeepSeek | Cloud | Yes |
| OpenAI-compatible | Cloud | Yes |

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImportError: _ssl` | Use system Python, not venv with broken SSL |
| `widdx-web not found` | `pip install -e ".[api]"` first |
| `No module named fastapi` | `pip install fastapi uvicorn` |
| `401 Unauthorized` (API) | Set `WIDDX_API_KEY` env var |

## 📊 Dev

```bash
pytest tests/          # 477 tests
docs/project-analysis/ # Full project documentation
```

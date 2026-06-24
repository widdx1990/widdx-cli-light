# WIDDX Nexus — Routes & API Reference

> All HTTP endpoints, WebSocket handlers, and CLI commands.

## REST API Server (scripts/api_server.py)

**Base URL:** `http://127.0.0.1:8000`
**Auth:** `Authorization: Bearer <WIDDX_API_KEY>` header required on all endpoints.
**Rate Limit:** 60 requests per minute per API key (sliding window).
**CORS:** Restricted to `localhost:8000` and `127.0.0.1:8000` by default (configurable via `WIDDX_CORS_ORIGINS` env var).

### Endpoints

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET` | `/api/health` | ✅ | Health check + stats | — | `{status, version, provider, model, turns, cost}` |
| `POST` | `/api/chat` | ✅ | Send chat message | `{message: str, stream: bool}` | `{response, model, turns, cost}` |
| `GET` | `/api/providers` | ✅ | List available providers | — | `{current, model, available, models}` |
| `POST` | `/api/providers/switch` | ✅ | Switch provider | `{name, model, base_url}` | `{status, provider, model}` |
| `GET` | `/api/sessions` | ✅ | List sessions summary | — | `{messages, turns}` |
| `DELETE` | `/api/sessions` | ✅ | Clear current session | — | `{status: "cleared"}` |
| `GET` | `/api/memory` | ✅ | List/search memories | `?query=str` | `{facts, total}` |
| `POST` | `/api/memory` | ✅ | Save memory | `{name, content, type}` | `{status, name}` |
| `DELETE` | `/api/memory/{name}` | ✅ | Delete memory | — | `{status: "deleted"}` |
| `GET` | `/api/tools` | ✅ | List all tools | — | `{base, mcp, total}` |
| `GET` | `/api/project/docs` | ✅ | Get project docs | — | `{PLAN.md, DESIGN.md, ...}` |
| `POST` | `/api/project/docs` | ✅ | Update project doc | `{doc, content}` | `{status, doc}` |
| `GET` | `/api/project/status` | ✅ | Project status + deps | — | `{context, dependencies}` |

### Pydantic Models

```python
class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    model: str
    turns: int
    cost: float

class ProviderSwitch(BaseModel):
    name: str
    model: Optional[str] = ""
    base_url: Optional[str] = ""

class MemoryFact(BaseModel):
    name: str
    content: str
    type: str = "feedback"

class DocUpdate(BaseModel):
    doc: str  # PLAN.md, DESIGN.md, TASKS.md, ROADMAP.md
    content: str
```

## Web Server (scripts/web/server.py)

**Base URL:** `http://localhost:3000` (configurable)

### Page Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Main web dashboard (HTML) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/status` | System status |
| `GET` | `/api/tools` | Tool list |
| `GET` | `/api/project/session` | Current session |
| `GET` | `/api/branches` | Git branches |
| `POST` | `/api/chat` | Chat message |
| `POST` | `/api/sandbox/exec` | Execute command in sandbox |
| `GET` | `/api/sandbox/files` | List sandbox files |
| `POST` | `/api/sandbox/screenshot` | Take screenshot |
| `GET` | `/api/dashboard` | Dashboard data |
| `GET` | `/api/dashboard/cron` | Cron jobs |
| `POST` | `/api/dashboard/cron` | Create cron job |
| `DELETE` | `/api/dashboard/cron/{job_id}` | Delete cron job |
| `GET` | `/api/dashboard/background` | Background tasks |
| `WS` | `/ws/chat` | WebSocket chat (streaming) |
| `WS` | `/ws/dashboard` | WebSocket dashboard updates |

## GitHub App (github-app/app.py)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/webhook` | GitHub webhook receiver |

## CLI Commands

### Slash Commands (in-chat)

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/model <name>` | Switch AI model |
| `/provider <name>` | Switch provider |
| `/temperature <0-2>` | Set temperature |
| `/max_turns <n>` | Set max turns |
| `/clear` | Clear session |
| `/sessions` | List sessions |
| `/memory` | List memories |
| `/remember <fact>` | Save a memory |
| `/forget <name>` | Delete a memory |
| `/debug` | Toggle debug mode |
| `/status` | Show system status |
| `/doctor` | Run diagnostics |
| `/cost` | Show cost breakdown |
| `/tasks` | List background tasks |
| `/sandbox <mode>` | Switch sandbox mode |
| `/mcp` | List MCP servers |
| `/skill [name]` | Activate/deactivate skill |
| `/template <name>` | Load chat template |
| `/visualize` | Show system architecture |
| `/git` | Git operations |
| `/cron` | Cron job management |
| `/workflow` | Workflow management |

### External CLI Commands

| Command | Description |
|---------|-------------|
| `widdx` | Launch CLI (default) |
| `widdx-tui` | Launch TUI (Textual) |
| `widdx-api` | Launch REST API server |
| `widdx-web` | Launch web dashboard |
| `widdx --help` | Show help |
| `widdx --version` | Show version |
| `widdx --port <n>` | Set port for API |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WIDDX_API_KEY` | (auto-generated) | API authentication key |
| `WIDDX_API_HOST` | `127.0.0.1` | API server bind address |
| `WIDDX_CORS_ORIGINS` | `localhost:8000,127.0.0.1:8000` | Allowed CORS origins |
| `WIDDX_NO_CONSOLE` | — | Suppress console output |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `DISCORD_BOT_TOKEN` | — | Discord bot token |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `OPENAI_API_KEY` | — | OpenAI API key |

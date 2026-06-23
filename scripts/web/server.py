"""WIDDX Nexus — Web UI Server (FastAPI + WebSocket).

Architecture:
  server.py          ← FastAPI app, routes, WebSocket
  chat.py            ← LLM chat handler (UIL Brain pipeline)
  sandbox.py         ← Sandbox (terminal, browser, files)
  dashboard.py       ← All-system aggregator for the REST API
  static/            ← Frontend assets
    index.html       ← Main page (with RTL/Arabic i18n)
    css/style.css    ← Full design system (dark/light, RTL)
    js/              ← JavaScript modules
      lang.js        ← i18n engine (en/ar)
      ui.js          ← Theme, sidebar, markdown parser, command palette
      nexus.js       ← Main app logic, WebSocket, all views

Usage:
    python scripts/web_app.py
    # → http://localhost:8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from typing import Any

from core._path import ensure_project_root
ensure_project_root()

from pathlib import Path

# ── Static paths ────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

# ── FastAPI imports ─────────────────────────────────────────
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("widdx.web")

# ── App ─────────────────────────────────────────────────────
app = FastAPI(title="WIDDX Nexus", version="3.0.0")

# ── Mount static files ──────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Lazy handlers ───────────────────────────────────────────
_chat_handler: Any = None
_sandbox_handler: Any = None


def get_chat():
    global _chat_handler
    if _chat_handler is None:
        from scripts.web.chat import ChatHandler
        _chat_handler = ChatHandler()
    return _chat_handler


def refresh_chat():
    """Force recreation of the chat handler (e.g. after settings change)."""
    global _chat_handler
    _chat_handler = None
    return get_chat()


def get_sandbox():
    global _sandbox_handler
    if _sandbox_handler is None:
        from scripts.web.sandbox import SandboxHandler
        _sandbox_handler = SandboxHandler()
    return _sandbox_handler


# ── Routes ──────────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the main Web UI page (no-cache)."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        from fastapi.responses import Response
        content = html_path.read_bytes()
        return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>WIDDX Nexus Web UI</h1><p>Build index.html first.</p>")


@app.get("/api/status")
async def status():
    """System status endpoint."""
    chat = get_chat()
    sandbox = get_sandbox()
    from pathlib import Path
    return {
        "status": "ok",
        "provider": chat.info,
        "sandbox": {"mode": sandbox.mode},
        "version": "3.0.0",
        "project": Path.cwd().name,
    }


@app.get("/api/tools")
async def api_tools():
    """List available tools for slash commands and UI."""
    try:
        chat = get_chat()
        defs = chat._get_tool_defs() if hasattr(chat, "_get_tool_defs") else []
        tools_out = []
        for td in defs:
            name = td.get("name") or (td.get("function") or {}).get("name", "")
            desc = td.get("description") or (td.get("function") or {}).get("description", "")
            if name:
                tools_out.append({"name": name, "description": desc[:120] if desc else ""})
        return {"tools": tools_out, "count": len(tools_out)}
    except Exception as e:
        return {"tools": [], "error": str(e)}


@app.get("/api/project/session")
async def api_project_session():
    """Load current project session (same store as CLI/TUI)."""
    try:
        from core.project import state as project_state
        session = project_state.load_session()
        if session:
            return session
        return {"messages": [], "state": {}}
    except Exception as e:
        return {"messages": [], "state": {}, "error": str(e)}


@app.get("/api/branches")
async def api_branches():
    """List session branches for the current project."""
    try:
        from core.project.state import list_branches, get_current_branch
        return {"current": get_current_branch(), "branches": list_branches()}
    except Exception as e:
        return {"current": "main", "branches": ["main"], "error": str(e)}


@app.post("/api/chat")
async def chat_message(request: Request):
    """Send a chat message (non-blocking)."""
    data = await request.json()
    message = data.get("message", "")
    history = data.get("history", [])

    chat = get_chat()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, chat.chat, message, history)
    return result


@app.post("/api/sandbox/exec")
async def sandbox_exec(request: Request):
    """Execute a shell command in the sandbox."""
    data = await request.json()
    command = data.get("command", "")
    timeout = data.get("timeout", 60)

    sandbox = get_sandbox()
    result = sandbox.execute(command, timeout)
    return result


@app.get("/api/sandbox/files")
async def sandbox_files(path: str = "."):
    """Get file tree."""
    sandbox = get_sandbox()
    return sandbox.file_tree(path)


@app.post("/api/sandbox/screenshot")
async def sandbox_screenshot():
    """Take a browser screenshot."""
    sandbox = get_sandbox()
    return sandbox.screenshot()


# ── WebSocket ───────────────────────────────────────────────

# ── Dashboard ────────────────────────────────────────────
_dashboard: Any = None

def get_dashboard():
    global _dashboard
    if _dashboard is None:
        from scripts.web.dashboard import Dashboard
        _dashboard = Dashboard()
    return _dashboard


@app.get("/api/dashboard")
async def api_dashboard():
    """Full system dashboard."""
    return get_dashboard().computer_info()


@app.get("/api/dashboard/cron")
async def api_cron():
    return get_dashboard().cron_jobs()


@app.post("/api/dashboard/cron")
async def api_cron_create(request: Request):
    data = await request.json()
    return get_dashboard().cron_create(data.get("schedule", ""), data.get("prompt", ""))


@app.delete("/api/dashboard/cron/{job_id}")
async def api_cron_delete(job_id: str):
    return get_dashboard().cron_delete(job_id)


@app.get("/api/dashboard/background")
async def api_background():
    return get_dashboard().background_tasks()


@app.get("/api/dashboard/agents")
async def api_agents():
    return get_dashboard().sub_agents()


@app.get("/api/dashboard/memories")
async def api_memories():
    return get_dashboard().memories()


@app.get("/api/dashboard/sessions")
async def api_sessions():
    return get_dashboard().sessions()


@app.get("/api/dashboard/activity")
async def api_activity(limit: int = 50):
    return get_dashboard().activity_feed(limit)


@app.get("/api/dashboard/gateway")
async def api_gateway():
    return get_dashboard().gateway_status()


@app.post("/api/gateway/start")
async def api_gateway_start(request: Request):
    """Start a gateway platform (telegram/discord/sms) with credentials."""
    data = await request.json()
    platform = data.get("platform", "")
    token = data.get("token", "")
    if not platform or not token:
        return {"status": "error", "message": "Platform and token required"}
    try:
        from core.gateway import GatewayCore
        gw = globals().get("_gateway")
        if gw is None:
            gw = GatewayCore()
            def _gh(msg) -> str:
                try:
                    chat = get_chat()
                    r = chat.chat(msg.text, history=[])
                    return r.get("content", "") or r.get("error", "No response")
                except Exception as e:
                    return f"Error: {e}"
            gw.set_handler(_gh)
            globals()["_gateway"] = gw
        gw.start_platform(platform, token=token)
        return {"status": "ok", "message": f"{platform} started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/gateway/stop")
async def api_gateway_stop(request: Request):
    """Stop a gateway platform."""
    data = await request.json()
    platform = data.get("platform", "")
    try:
        gw = globals().get("_gateway")
        if gw:
            gw.stop_platform(platform)
        return {"status": "ok", "message": f"{platform} stopped"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Settings ────────────────────────────────────────────

@app.get("/api/settings")
async def api_settings():
    return get_dashboard().get_settings()


@app.post("/api/settings")
async def api_settings_update(request: Request):
    data = await request.json()
    result = get_dashboard().update_settings(data)
    if result.get("status") == "ok":
        refresh_chat()
        try:
            from core.activity import add as add_event
            provider = data.get("provider", {})
            changed = []
            if "model" in provider: changed.append(f"model={provider['model']}")
            if "name" in provider: changed.append(f"provider={provider['name']}")
            if "temperature" in data: changed.append(f"temp={data['temperature']}")
            add_event("settings_change", detail=", ".join(changed) or "settings updated",
                      icon="fa-sliders", agent="system", status="done")
        except Exception:
            pass
    return result


@app.get("/api/settings/models")
async def api_settings_models(provider: str = "opencode-zen"):
    return get_dashboard().get_provider_models(provider)


@app.get("/api/dashboard/skills")
async def api_skills():
    return get_dashboard().skills()


# ── NEW: Session Save / Load / Export ─────────────────────

@app.post("/api/sessions")
async def api_session_save(request: Request):
    data = await request.json()
    return get_dashboard().session_save(data.get("name", "Untitled"), data.get("messages", []))


@app.get("/api/sessions")
async def api_sessions_list():
    return get_dashboard().sessions()


@app.get("/api/sessions/{session_id}")
async def api_session_load(session_id: str):
    return get_dashboard().session_load(session_id)


@app.delete("/api/sessions/{session_id}")
async def api_session_delete(session_id: str):
    return get_dashboard().session_delete(session_id)


@app.get("/api/sessions/{session_id}/export")
async def api_session_export(session_id: str):
    return get_dashboard().session_export(session_id)


# ── NEW: Memory CRUD ──────────────────────────────────────

@app.post("/api/memories")
async def api_memory_create(request: Request):
    data = await request.json()
    return get_dashboard().memory_create(data.get("content", ""), data.get("tags", ""))


@app.get("/api/memories/search")
async def api_memory_search(q: str = ""):
    return get_dashboard().memory_search(q)


@app.delete("/api/memories/{memory_id}")
async def api_memory_delete(memory_id: str):
    return get_dashboard().memory_delete(memory_id)


# ── NEW: MCP Management ────────────────────────────────────

@app.get("/api/mcp")
async def api_mcp_status():
    return get_dashboard().mcp_status()


@app.post("/api/mcp")
async def api_mcp_add(request: Request):
    data = await request.json()
    return get_dashboard().mcp_add(data.get("name", ""), data.get("command", ""), data.get("args", []))


@app.delete("/api/mcp/{name}")
async def api_mcp_remove(name: str):
    return get_dashboard().mcp_remove(name)


@app.post("/api/mcp/{name}/restart")
async def api_mcp_restart(name: str):
    return get_dashboard().mcp_restart(name)


# ── NEW: Proxy Settings ────────────────────────────────────

@app.get("/api/proxy")
async def api_proxy_status():
    return get_dashboard().proxy_status()


@app.post("/api/proxy")
async def api_proxy_update(request: Request):
    data = await request.json()
    return get_dashboard().proxy_update(
        http=data.get("http", ""),
        https=data.get("https", ""),
        enabled=data.get("enabled", False),
    )


# ── NEW: Permissions ──────────────────────────────────────

@app.get("/api/permissions")
async def api_permissions_status():
    return get_dashboard().permissions_status()


@app.post("/api/permissions")
async def api_permissions_set(request: Request):
    data = await request.json()
    return get_dashboard().permissions_set(data.get("level", "normal"))


# ── NEW: GGUF Models ──────────────────────────────────────

@app.get("/api/gguf")
async def api_gguf_models():
    return get_dashboard().gguf_models()


@app.post("/api/gguf/load")
async def api_gguf_load(request: Request):
    data = await request.json()
    return get_dashboard().gguf_load(data.get("path", ""))


@app.post("/api/gguf/unload")
async def api_gguf_unload():
    return get_dashboard().gguf_unload()


# ── NEW: Debug / Doctor ───────────────────────────────────

@app.get("/api/debug")
async def api_debug():
    return get_dashboard().debug_info()


@app.get("/api/doctor")
async def api_doctor():
    return get_dashboard().doctor_check()


# ── NEW: Manifest ─────────────────────────────────────────

@app.get("/api/manifest")
async def api_manifest():
    return get_dashboard().manifest_status()


@app.post("/api/manifest/scan")
async def api_manifest_scan():
    return get_dashboard().manifest_scan()


# ── NEW: Git ──────────────────────────────────────────────

@app.get("/api/git")
async def api_git_status():
    return get_dashboard().git_status()


@app.get("/api/git/branches")
async def api_git_branches():
    return get_dashboard().git_branches()


@app.post("/api/git/undo")
async def api_git_undo():
    return get_dashboard().git_undo()


# ── NEW: Token Budget ─────────────────────────────────────

@app.get("/api/token-budget")
async def api_token_budget():
    return get_dashboard().token_budget_status()


@app.post("/api/token-budget/reset")
async def api_token_budget_reset():
    return get_dashboard().token_budget_reset()


# ── NEW: Checkpoints ──────────────────────────────────────

@app.get("/api/checkpoints")
async def api_checkpoints():
    return get_dashboard().checkpoints_list()


@app.post("/api/checkpoints")
async def api_checkpoint_create():
    return get_dashboard().checkpoint_create()


@app.post("/api/checkpoints/{checkpoint_id}/restore")
async def api_checkpoint_restore(checkpoint_id: str):
    return get_dashboard().checkpoint_restore(checkpoint_id)


@app.delete("/api/checkpoints/{checkpoint_id}")
async def api_checkpoint_delete(checkpoint_id: str):
    return get_dashboard().checkpoint_delete(checkpoint_id)


# ── NEW: Plugins ─────────────────────────────────────────

@app.get("/api/plugins")
async def api_plugins():
    return get_dashboard().plugins_list()


@app.post("/api/plugins/{name}/enable")
async def api_plugin_enable(name: str):
    return get_dashboard().plugin_enable(name)


@app.post("/api/plugins/{name}/disable")
async def api_plugin_disable(name: str):
    return get_dashboard().plugin_disable(name)


# ── NEW: Workflows ───────────────────────────────────────

@app.get("/api/workflows")
async def api_workflows():
    return get_dashboard().workflows_list()


@app.post("/api/workflows")
async def api_workflow_create(request: Request):
    data = await request.json()
    return get_dashboard().workflow_create(data.get("name", ""), data.get("steps", []))


@app.post("/api/workflows/{workflow_id}/run")
async def api_workflow_run(workflow_id: str):
    return get_dashboard().workflow_run(workflow_id)


# ── NEW: Auto-Commit ──────────────────────────────────────

@app.get("/api/autocommit")
async def api_autocommit():
    return get_dashboard().autocommit_status()


@app.post("/api/autocommit/toggle")
async def api_autocommit_toggle():
    return get_dashboard().autocommit_toggle()


# ── NEW: API Keys ─────────────────────────────────────────

@app.get("/api/apikeys")
async def api_apikeys():
    return get_dashboard().apikeys_list()


# ── NEW: Version ──────────────────────────────────────────

@app.get("/api/version")
async def api_version():
    return get_dashboard().app_version()


# ── Simple in-memory rate limiter ──────────────────────────────
_ratelimit_store: dict[str, list[float]] = {}
_RATELIMIT_MAX = 30  # max requests
_RATELIMIT_WINDOW = 60  # per N seconds
_RATELIMIT_LAST_CLEANUP: float = 0.0


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited.

    Periodically purges stale entries (IPs with no recent activity)
    so the dict doesn't grow unbounded.
    """
    global _RATELIMIT_LAST_CLEANUP
    now = time.time()
    window = _RATELIMIT_WINDOW

    # ── Periodic full cleanup (every 5 min) ─────────────────
    if now - _RATELIMIT_LAST_CLEANUP > 300:
        cutoff = now - window
        _ratelimit_store.clear()
        _RATELIMIT_LAST_CLEANUP = now

    timestamps = _ratelimit_store.get(client_ip, [])
    # Remove old timestamps outside the window
    timestamps = [t for t in timestamps if now - t < window]
    if len(timestamps) >= _RATELIMIT_MAX:
        return False
    timestamps.append(now)
    _ratelimit_store[client_ip] = timestamps
    return True


# ── Endpoints ───────────────────────────────────────────


@app.post("/api/computer/exec")
async def api_computer_exec(request: Request):
    data = await request.json()
    client = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            {"status": "error", "message": "Rate limited — 30 req/min max"},
            status_code=429,
        )
    return get_dashboard().computer_exec(data.get("command", ""))


@app.get("/api/computer/info")
async def api_computer_info():
    return get_dashboard().computer_info()


# ── WebSocket ───────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat — persistent session, non-blocking.

    Receives:  {"message": "...", "history": [...]}
    Sends:     {"type": "text|tool|done|error", "data": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket connected")
    loop = asyncio.get_running_loop()

    try:
        while True:
            # Wait for the next message from the client (blocks until data arrives)
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            history = payload.get("history", [])

            chat = get_chat()
            event_queue: asyncio.Queue = asyncio.Queue()

            async def _stream_runner():
                """Run chat.chat_stream() in executor, feeding events into the queue."""
                def _sync_run():
                    for event in chat.chat_stream(message, history):
                        loop.call_soon_threadsafe(event_queue.put_nowait, event)
                await loop.run_in_executor(None, _sync_run)

            stream_task = asyncio.create_task(_stream_runner())

            try:
                while True:
                    event = await asyncio.wait_for(event_queue.get(), timeout=300.0)
                    if event["type"] == "done":
                        # Forward done to frontend so it resets streaming state
                        await websocket.send_json({"type": "done", "data": ""})
                        break
                    await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "error", "data": "Response timed out"})
                await websocket.send_json({"type": "done", "data": ""})
            finally:
                if not stream_task.done():
                    stream_task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for live activity events."""
    await websocket.accept()
    logger.info("Events WS connected")

    try:
        from core.activity import get_store
        store = get_store()
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        return

    import asyncio

    def send_event(event_dict: dict):
        """Push every new event to this client."""
        try:
            asyncio.get_running_loop().create_task(websocket.send_json(event_dict))
        except Exception:
            pass

    unsubscribe = store.subscribe(send_event)

    try:
        # Keep connection open; client sends keepalive pings
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe()
        logger.info("Events WS disconnected")


# ── Main ────────────────────────────────────


# ── Main ────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the Web UI server."""
    import uvicorn
    logger.info("WIDDX Nexus Web UI: http://%s:%d", host, port)

    # ── Start background services ──────────────────────────
    try:
        from core.cron.scheduler import CronScheduler
        _scheduler = CronScheduler()
        _scheduler.start()
        logger.info("Cron scheduler started via Web UI")
    except Exception as e:
        logger.warning("Cron scheduler start: %s", e)

    _gateway = None
    try:
        from core.gateway import GatewayCore, Platform, Message
        from core._path import ensure_project_root
        ensure_project_root()

        _gateway = GatewayCore()

        # Handler: incoming messages → UIL ChatHandler → response
        def _gateway_handler(msg) -> str:
            try:
                chat = get_chat()
                result = chat.chat(msg.text, history=[])
                return result.get("content", "") or result.get("error", "No response")
            except Exception as exc:
                logger.error("Gateway handler error: %s", exc)
                return f"Error: {exc}"

        _gateway.set_handler(_gateway_handler)
        # Start with tokens from config or env
        import os
        _gateway.start_platform("telegram", token=os.environ.get("TELEGRAM_TOKEN", ""))
        _gateway.start_platform("discord", token=os.environ.get("DISCORD_TOKEN", ""))
        logger.info("Gateway started via Web UI")
    except Exception as e:
        logger.info("Gateway not started: %s", e)

    # ── Startup event ──────────────────────────────────────
    try:
        from core.activity import add as add_event
        add_event("system", detail="WIDDX Nexus Mission Control started",
                  icon="fa-star", agent="system", status="done")
    except Exception:
        pass

    uvicorn.run(
        "scripts.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )

"""WIDDX Nexus — Web UI Server (FastAPI + WebSocket).

Architecture:
  server.py          ← FastAPI app, routes, WebSocket
  chat.py            ← LLM chat handler
  sandbox.py         ← Sandbox (terminal, browser, files)
  static/            ← Frontend assets
    index.html       ← Main page
    css/style.css    ← Styling
    js/              ← JavaScript modules
      app.js         ← Entry point
      chat.js        ← Chat panel
      sandbox.js     ← Sandbox panel
      websocket.js   ← WebSocket client

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
    return {
        "status": "ok",
        "provider": chat.info,
        "sandbox": {"mode": sandbox.mode},
        "version": "3.0.0",
    }


@app.post("/api/chat")
async def chat_message(request: Request):
    """Send a chat message (non-streaming)."""
    data = await request.json()
    message = data.get("message", "")
    history = data.get("history", [])

    chat = get_chat()
    result = chat.chat(message, history)
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


# ── Simple in-memory rate limiter ──────────────────────────────
_ratelimit_store: dict[str, list[float]] = {}
_RATELIMIT_MAX = 30  # max requests
_RATELIMIT_WINDOW = 60  # per N seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.time()
    window = _RATELIMIT_WINDOW
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
    """WebSocket endpoint for streaming chat.

    Receives:  {"message": "...", "history": [...]}
    Sends:     {"type": "text|tool|reasoning|done|error", "data": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket connected")

    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        message = payload.get("message", "")
        history = payload.get("history", [])

        chat = get_chat()
        for event in chat.stream_chat(message, history):
            await websocket.send_json(event)
            if event["type"] == "done" or event["type"] == "error":
                break

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
            asyncio.ensure_future(websocket.send_json(event_dict))
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

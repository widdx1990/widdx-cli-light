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
import sqlite3
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

# ── FastAPI imports (checked) ──────────────────────────────
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
    from fastapi.staticfiles import StaticFiles
except ImportError as e:
    import sys
    print(f"\n❌ FastAPI not installed: {e}")
    print("   Install: pip install widdx-nexus[api]")
    print("   Or:      pip install fastapi uvicorn\n")
    sys.exit(1)

logger = logging.getLogger("widdx.web")

# ── Log sanitization ─────────────────────────────────────────
from core.utils import sanitize_log

def _safe_log(msg: str, *args: Any) -> None:
    """Log a message with sensitive data redacted."""
    safe_msg = sanitize_log(msg % args if args else msg)
    logger.debug(safe_msg)

# ── Pydantic models for input validation ────────────────────
from pydantic import BaseModel, Field
from typing import Optional as Opt

class ChatPayload(BaseModel):
    message: str = Field(..., min_length=1, max_length=100000)
    history: list[dict] = Field(default_factory=list, max_length=1000)

class SandboxPayload(BaseModel):
    command: str = Field(..., min_length=1, max_length=10000)
    timeout: int = Field(default=60, ge=1, le=600)

class SettingsPayload(BaseModel):
    provider: dict = Field(default_factory=dict)
    # system_prompt: hardcoded in core/constants.py — not user-editable
    temperature: Opt[float] = Field(default=None, ge=0, le=2)
    max_turns: Opt[int] = Field(default=None, ge=1, le=100)
    cli_theme: Opt[str] = Field(default=None, pattern=r'^(dark|light)$')

class SessionPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    messages: list[dict] = Field(default_factory=list, max_length=1000)

class MemoryPayload(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    tags: str = Field(default="", max_length=500)

# ── App ─────────────────────────────────────────────────────
app = FastAPI(title="WIDDX Nexus", version="3.2.0")

# ── CORS + Origin validation ───────────────────────────────
# ISS-009: CSRF / Origin validation — only allow same-origin requests
ALLOWED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8099", "http://127.0.0.1:8099"]

from fastapi.middleware.cors import CORSMiddleware

@app.middleware("http")
async def _validate_origin(request: Request, call_next):
    """Reject requests with disallowed Origin header (CSRF protection).

    Only validates non-GET, non-OPTIONS requests that include an Origin header.
    Browser fetch/XHR requests include Origin automatically for cross-origin
    requests; local requests from the same origin are unaffected.
    """
    if request.method not in ("GET", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"error": "Origin not allowed"})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Mount static files ──────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Favicon ─────────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    p = STATIC_DIR / "favicon.ico"
    if p.exists():
        return FileResponse(p)
    return Response(status_code=204)

# ── Lazy handlers ───────────────────────────────────────────
_chat_handler: Any = None
_sandbox_handler: Any = None


def get_chat() -> Any:
    global _chat_handler
    if _chat_handler is None:
        from scripts.web.chat import ChatHandler
        _chat_handler = ChatHandler()
    return _chat_handler


def refresh_chat() -> Any:
    """Force recreation of the chat handler (e.g. after settings change)."""
    global _chat_handler
    _chat_handler = None
    return get_chat()


def get_sandbox() -> Any:
    global _sandbox_handler
    if _sandbox_handler is None:
        from scripts.web.sandbox import SandboxHandler
        _sandbox_handler = SandboxHandler()
    return _sandbox_handler


# ── Routes ──────────────────────────────────────────────────

@app.post("/api/new-session")
async def api_new_session() -> dict:
    """Start a new chat session."""
    chat = get_chat()
    sid = chat.new_session()
    return {"session_id": sid}


@app.get("/")
async def index() -> Response:
    """Serve the main Web UI page (no-cache)."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        content = html_path.read_bytes()
        return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>WIDDX Nexus Web UI</h1><p>Build index.html first.</p>")


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint — lightweight, no side effects."""
    return {"status": "ok", "version": "3.2.0"}


@app.get("/api/status")
async def status() -> dict:
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
async def api_tools() -> dict:
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
async def api_project_session() -> dict:
    """Load current project session from SQLite database."""
    try:
        from core.database import get_db
        db = get_db()
        sessions = db.list_sessions(limit=1)
        if not sessions:
            return {"messages": [], "state": {}}
        sid = sessions[0]["id"]
        msgs = db.get_messages(sid)
        return {
            "messages": [{"role": m["role"], "content": m["content"]} for m in msgs],
            "state": {"model": sessions[0].get("name", ""), "session_id": sid},
        }
    except Exception as e:
        return {"messages": [], "state": {}, "error": str(e)}


@app.get("/api/project/docs/{doc_name}")
async def api_project_doc(doc_name: str):
    """Read a project doc (PLAN.md, DESIGN.md, TASKS.md, or ROADMAP.md).
    Auto-creates from template if the file does not exist yet."""
    from pathlib import Path
    allowed = {"PLAN.md", "DESIGN.md", "TASKS.md", "ROADMAP.md"}
    if doc_name not in allowed:
        return JSONResponse(status_code=400, content={"error": "Invalid doc name"})
    doc_path = Path.cwd() / ".widdx" / doc_name
    if not doc_path.exists():
        # Auto-create with template from project_tracker
        from core.project_tracker import ensure_docs
        ensure_docs(Path.cwd())
    content = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""
    return {"content": content, "exists": doc_path.exists(), "name": doc_name}


@app.get("/api/branches")
async def api_branches():
    """List session branches for the current project."""
    try:
        from core.project.state import list_branches, get_current_branch
        return {"current": get_current_branch(), "branches": list_branches()}
    except Exception as e:
        return {"current": "main", "branches": ["main"], "error": str(e)}


@app.post("/api/chat")
async def chat_message(payload: ChatPayload, request: Request):
    """Send a chat message (non-blocking)."""
    message = payload.message
    history = payload.history
    # Rate limiting
    from fastapi.responses import JSONResponse as _JR
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return _JR(status_code=429, content={"content": "", "error": "Rate limited — 30 req/min max"})

    chat = get_chat()
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, chat.chat, message, history),
            timeout=600.0
        )
        return result
    except asyncio.TimeoutError:
        return {"content": "", "error": "Request timed out after 10 minutes. Please try a simpler request."}


# ── Pydantic models for File Operations (Phase 2) ────────────
class FileCreatePayload(BaseModel):
    path: str = Field(..., min_length=1, max_length=10000)
    is_directory: bool = Field(default=False)
    content: str = Field(default="", max_length=5000000)

class FileRenamePayload(BaseModel):
    path: str = Field(..., min_length=1, max_length=10000)
    new_name: str = Field(..., min_length=1, max_length=1000)


@app.get("/api/sandbox/file")
async def sandbox_file_read(path: str = ""):
    """Read file content."""
    try:
        if not path:
            return {"error": "Path is required"}
        file_path = Path(path).resolve()
        if not file_path.exists() or not file_path.is_file():
            return {"error": "File not found"}
        # Security: prevent reading outside project
        project_root = Path.cwd().resolve()
        fp_str = str(file_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        content = file_path.read_text(encoding="utf-8")
        size = file_path.stat().st_size
        return {"content": content, "size": size, "path": str(file_path)}
    except UnicodeDecodeError:
        return {"error": "Binary file — cannot read as text"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/sandbox/file")
async def sandbox_file_write(payload: FileCreatePayload):
    """Write file content."""
    try:
        file_path = Path(payload.path).resolve()
        project_root = Path.cwd().resolve()
        fp_str = str(file_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(payload.content, encoding="utf-8")
        return {"status": "ok", "path": str(file_path)}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/sandbox/file")
async def sandbox_file_delete(path: str = ""):
    """Delete a file or directory."""
    try:
        if not path:
            return {"error": "Path is required"}
        file_path = Path(path).resolve()
        project_root = Path.cwd().resolve()
        fp_str = str(file_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        if file_path.is_file():
            file_path.unlink()
            return {"status": "ok", "deleted": str(file_path)}
        elif file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
            return {"status": "ok", "deleted": str(file_path)}
        return {"error": "Path not found"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/sandbox/file/create")
async def sandbox_file_create(payload: FileCreatePayload):
    """Create a new file or directory."""
    try:
        file_path = Path(payload.path).resolve()
        project_root = Path.cwd().resolve()
        fp_str = str(file_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        if payload.is_directory:
            file_path.mkdir(parents=True, exist_ok=True)
            return {"status": "ok", "created": str(file_path), "type": "directory"}
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(payload.content, encoding="utf-8")
            return {"status": "ok", "created": str(file_path), "type": "file"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/sandbox/file/delete")
async def sandbox_file_delete_post(payload: FileCreatePayload):
    """Alias: POST endpoint matching the frontend call.
    Delegates to the existing DELETE /api/sandbox/file logic."""
    try:
        path = payload.path
        if not path:
            return {"error": "Path is required"}
        file_path = Path(path).resolve()
        project_root = Path.cwd().resolve()
        fp_str = str(file_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        if file_path.is_file():
            file_path.unlink()
            return {"status": "ok", "deleted": str(file_path)}
        elif file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
            return {"status": "ok", "deleted": str(file_path)}
        return {"error": "Path not found"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/sandbox/file/rename")
async def sandbox_file_rename(payload: FileRenamePayload):
    """Rename a file or directory."""
    try:
        old_path = Path(payload.path).resolve()
        project_root = Path.cwd().resolve()
        fp_str = str(old_path)
        pr_str = str(project_root)
        if fp_str != pr_str and not fp_str.startswith(pr_str + "/"):
            return {"error": "Access denied"}
        new_path = old_path.parent / payload.new_name
        old_path.rename(new_path)
        return {"status": "ok", "old": str(old_path), "new": str(new_path)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/sandbox/processes")
async def sandbox_processes():
    """List running processes (cross-platform)."""
    import subprocess
    try:
        if sys.platform == "win32":
            result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5)
            processes = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip(' \"') for p in line.split(",")]
                if len(parts) >= 3:
                    processes.append({
                        "pid": parts[1],
                        "name": parts[0],
                        "mem": parts[3] if len(parts) > 3 else "",
                    })
        else:
            result = subprocess.run(["ps", "aux", "--sort=-%mem"], capture_output=True, text=True, timeout=5)
            processes = []
            lines = result.stdout.strip().split("\n")
            for line in lines[1:31]:  # top 30
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    processes.append({
                        "pid": parts[1],
                        "user": parts[0],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": parts[10][:60],
                    })
        return {"processes": processes, "count": len(processes)}
    except Exception as e:
        return {"processes": [], "error": str(e)}


@app.post("/api/sandbox/processes/{pid}/kill")
async def sandbox_process_kill(pid: str):
    """Kill a process by PID."""
    import subprocess
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True, timeout=5)
        else:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True, text=True, timeout=5)
        return {"status": "ok", "killed": pid}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/sandbox/exec")
async def sandbox_exec(payload: SandboxPayload, request: Request):
    """Execute a shell command in the sandbox."""
    command = payload.command
    timeout = payload.timeout
    # Rate limiting
    from fastapi.responses import JSONResponse as _JR2
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return _JR2(status_code=429, content={"stdout": "", "stderr": "Rate limited — 30 req/min max", "exit_code": -1, "mode": "auto"})

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

def get_dashboard() -> Any:
    global _dashboard
    if _dashboard is None:
        from scripts.web.dashboard import Dashboard
        _dashboard = Dashboard()
    return _dashboard


@app.get("/api/dashboard")
async def api_dashboard() -> dict:
    """Full system dashboard."""
    return get_dashboard().computer_info()


@app.get("/api/dashboard/cron")
async def api_cron() -> list[dict]:
    jobs = get_dashboard().cron_jobs()
    if not isinstance(jobs, list):
        return []
    return jobs


@app.post("/api/dashboard/cron")
async def api_cron_create(request: Request) -> dict:
    data = await request.json()
    return get_dashboard().cron_create(data.get("schedule", ""), data.get("prompt", ""))


@app.delete("/api/dashboard/cron/{job_id}")
async def api_cron_delete(job_id: str) -> dict:
    return get_dashboard().cron_delete(job_id)


@app.post("/api/dashboard/cron/{job_id}/toggle")
async def api_cron_toggle(job_id: str) -> dict:
    return get_dashboard().cron_toggle(job_id)


# ── Frontend-facing Cron aliases (nexus.js calls /api/cron/*) ──

@app.post("/api/cron")
async def api_cron_create_frontend(request: Request):
    data = await request.json()
    return get_dashboard().cron_create(
        schedule=str(data.get("interval", 60)),
        prompt=data.get("command", ""),
    )


@app.post("/api/cron/{job_id}/toggle")
async def api_cron_toggle_frontend(job_id: str) -> dict:
    return get_dashboard().cron_toggle(job_id)


@app.delete("/api/cron/{job_id}")
async def api_cron_delete_frontend(job_id: str) -> dict:
    return get_dashboard().cron_delete(job_id)


@app.get("/api/dashboard/background")
async def api_background() -> list[dict]:
    tasks = get_dashboard().background_tasks()
    if not isinstance(tasks, list):
        return []
    return tasks


@app.get("/api/dashboard/agents")
async def api_agents() -> list[dict]:
    agents = get_dashboard().sub_agents()
    if not isinstance(agents, list):
        return []
    return agents


@app.get("/api/dashboard/memories")
async def api_memories() -> list[dict]:
    mems = get_dashboard().memories()
    if not isinstance(mems, list):
        return []
    return mems


@app.get("/api/dashboard/sessions")
async def api_sessions() -> list[dict]:
    sessions = get_dashboard().sessions()
    if not isinstance(sessions, list):
        return []
    return sessions


@app.get("/api/dashboard/activity")
async def api_activity(limit: int = 50) -> list[dict]:
    feed = get_dashboard().activity_feed(limit)
    if not isinstance(feed, list):
        return []
    return feed


@app.get("/api/dashboard/gateway")
async def api_gateway() -> dict:
    return get_dashboard().gateway_status()


@app.post("/api/gateway/start")
async def api_gateway_start(request: Request) -> dict:
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
async def api_gateway_stop(request: Request) -> dict:
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
async def api_settings() -> dict:
    return get_dashboard().get_settings()


@app.post("/api/settings")
async def api_settings_update(payload: SettingsPayload) -> dict:
    data = payload.model_dump(exclude_none=True)
    result = get_dashboard().update_settings(data)
    if result.get("status") == "ok":
        refresh_chat()
        try:
            from core.activity import add as add_event
            provider = data.get("provider", {})
            changed = []
            if "model" in provider:
                changed.append(f"model={provider['model']}")
            if "name" in provider:
                changed.append(f"provider={provider['name']}")
            if "temperature" in data:
                changed.append(f"temp={data['temperature']}")
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
async def api_session_save(payload: SessionPayload):
    return get_dashboard().session_save(payload.name, payload.messages)


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
async def api_memory_create(payload: MemoryPayload):
    return get_dashboard().memory_create(payload.content, payload.tags)


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


@app.post("/api/git/commit")
async def api_git_commit(request: Request):
    data = await request.json()
    return get_dashboard().git_commit(
        message=data.get("message", "Auto-commit from WIDDX Nexus"),
        files=data.get("files"),
    )


@app.post("/api/git/push")
async def api_git_push():
    return get_dashboard().git_push()


@app.post("/api/git/pull")
async def api_git_pull():
    return get_dashboard().git_pull()


@app.post("/api/git/branch")
async def api_git_branch(request: Request):
    data = await request.json()
    return get_dashboard().git_branch_create(
        name=data.get("name", ""),
        from_branch=data.get("from"),
    )


@app.post("/api/git/checkout")
async def api_git_checkout(request: Request):
    data = await request.json()
    return get_dashboard().git_checkout(branch=data.get("branch", ""))


@app.get("/api/git/diff")
async def api_git_diff(file: str = ""):
    return get_dashboard().git_diff(file)


# ── NEW: Token Budget ─────────────────────────────────────

@app.get("/api/token-budget")
async def api_token_budget():
    return get_dashboard().token_budget()


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


# ── SQLite-backed rate limiter (ISS-005) ────────────────────────
# State survives server restarts. Uses the same .widdx directory
# as the rest of the project's persistence layer.
_RATELIMIT_MAX = 30   # max requests
_RATELIMIT_WINDOW = 60   # per N seconds
_RL_DB: sqlite3.Connection | None = None


def _rl_db() -> sqlite3.Connection:
    """Return the rate-limiter SQLite connection (lazy init)."""
    global _RL_DB
    if _RL_DB is None:
        db_path = Path.home() / ".widdx" / "ratelimit.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _RL_DB = sqlite3.connect(str(db_path))
        _RL_DB.execute("""
            CREATE TABLE IF NOT EXISTS ratelimit (
                client_ip  TEXT NOT NULL,
                ts         REAL NOT NULL
            )
        """)
        _RL_DB.execute(
            "CREATE INDEX IF NOT EXISTS idx_rl_ip_ts ON ratelimit(client_ip, ts)"
        )
        _RL_DB.commit()
    return _RL_DB


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited.

    Uses SQLite-backed storage so rate-limit state survives server
    restarts — prevents the restart-bypass attack vector (ISS-005).

    Only deletes expired entries for the requesting client to avoid
    affecting other clients' rate-limit state (ISS-014).
    """
    now = time.time()
    cutoff = now - _RATELIMIT_WINDOW
    db = _rl_db()
    # Purge only this client's expired entries — not ALL clients
    db.execute(
        "DELETE FROM ratelimit WHERE client_ip = ? AND ts < ?",
        (client_ip, cutoff),
    )
    # Count recent requests from this client
    row = db.execute(
        "SELECT COUNT(*) FROM ratelimit WHERE client_ip = ? AND ts >= ?",
        (client_ip, cutoff),
    ).fetchone()
    if row and row[0] >= _RATELIMIT_MAX:
        db.commit()
        return False
    # Record this request
    db.execute("INSERT INTO ratelimit (client_ip, ts) VALUES (?, ?)", (client_ip, now))
    db.commit()
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
    Supports cancel: client sends {"type": "cancel"}
    """
    await websocket.accept()
    logger.info("WebSocket connected")
    loop = asyncio.get_running_loop()
    stream_task: asyncio.Task | None = None
    cancel_flag = False

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            # Handle cancellation
            if payload.get("type") == "cancel":
                cancel_flag = True
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                await websocket.send_json({"type": "cancelled", "data": ""})
                await websocket.send_json({"type": "done", "data": ""})
                stream_task = None
                continue

            message = payload.get("message", "")
            # WebSocket message validation — prevent abuse
            if len(message) > 100000:
                await websocket.send_json({"type": "error", "data": "Message too long (max 100,000 characters)"})
                await websocket.send_json({"type": "done", "data": ""})
                continue
            history = payload.get("history", [])
            # Limit history size
            if len(history) > 1000:
                history = history[-1000:]
            cancel_flag = False

            chat = get_chat()
            event_queue: asyncio.Queue = asyncio.Queue()

            async def _stream_runner():
                """Run chat.chat_stream() in executor, feeding events into the queue."""
                def _sync_run():
                    for event in chat.chat_stream(message, history):
                        if cancel_flag:
                            break
                        loop.call_soon_threadsafe(event_queue.put_nowait, event)
                await loop.run_in_executor(None, _sync_run)

            stream_task = asyncio.create_task(_stream_runner())

            try:
                while not cancel_flag:
                    event = await asyncio.wait_for(event_queue.get(), timeout=600.0)
                    if event["type"] == "done":
                        await websocket.send_json({"type": "done", "data": ""})
                        break
                    await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "data": "Response timed out after 10 minutes. The task may be too complex. Try a simpler request or check provider connectivity."
                })
                await websocket.send_json({"type": "done", "data": ""})
            finally:
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                stream_task = None

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        if stream_task and not stream_task.done():
            stream_task.cancel()
    except Exception as e:
        logger.error("WebSocket error: %s", e)


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

def run(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
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
        from core.gateway import GatewayCore
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

    # ── Graceful shutdown (SIGINT/SIGTERM handlers) ─────────
    try:
        from core.background import register_shutdown
        register_shutdown(lambda: logger.info("Web server shutting down..."))
    except Exception:
        pass

    uvicorn.run(
        "scripts.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )

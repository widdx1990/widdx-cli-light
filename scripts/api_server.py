"""WIDDX Nexus — REST API Server.

This script lives in `scripts/` to keep the repository root tidy. It adds the
project root to sys.path before importing the core application logic.
"""

import sys
from pathlib import Path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
import time
import logging
import asyncio
import os
from typing import Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError:
    print("❌ FastAPI required. Install: pip install fastapi uvicorn")
    sys.exit(1)

logger = logging.getLogger("widdx.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

# ── API Security ───────────────────────────────────────────────

_API_KEY: str = os.environ.get("WIDDX_API_KEY", "")
if not _API_KEY:
    logger.warning(
        "WIDDX_API_KEY environment variable is not set.\n"
        "  The API server will REJECT all requests (401 Unauthorized).\n"
        "  Set the key: $env:WIDDX_API_KEY=\"your-secret-key\"   (PowerShell)\n"
        "  Or:        export WIDDX_API_KEY=\"your-secret-key\"    (Bash)\n"
        "  Then restart the server."
    )

security_scheme = HTTPBearer(auto_error=False)


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> None:
    """Dependency: require valid API key on every endpoint."""
    # Reject everything if the key was never configured
    if not _API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Server not configured: WIDDX_API_KEY is not set."
        )
    # Normal token check
    if credentials is None or credentials.credentials != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# ── Rate Limiter (in-memory sliding window) ────────────────────

class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = [now]
            return True
        self._buckets[key] = [t for t in bucket if t > cutoff]
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(now)
        return True


_rate_limiter = RateLimiter()


def rate_limit(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> None:
    """Dependency: apply rate limiting per API key (or IP if no key)."""
    client_id = credentials.credentials if credentials else "anonymous"
    if not _rate_limiter.check(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
from core import tools
from core.config.settings import load as load_config, save as save_config
from core.providers.providers import (
    create_provider, get_available_models,
)
from core.memory import MemoryStore
from core.memory_learner import MemoryLearner
from core.project import state as project_state
from core.project.scanner import ProjectScanner
from core.project_tracker import ensure_docs, load_docs, update_doc, build_context_block
from core.auto_setup import detect_project_deps
from core.skills import skill_manager
from core.mcp.client import get_mcp_manager
from core.chat import run_stream_turn

# ── App State ────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.cfg = load_config()
        self.provider = create_provider(self.cfg)
        self.mcp_mgr = get_mcp_manager()
        self.mcp_mgr.load_from_config(self.cfg)
        self.messages: list[dict] = []
        self.state: dict = {"model": f"{self.provider.name}/{self.provider.model}", "cost": 0.0, "turns": 0}
        self.scanner = ProjectScanner()

state = AppState()

# ── Pydantic Models ──────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=100000, description="Chat message (max 100K chars)")
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

# ── FastAPI App ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    state.cfg = load_config()
    state.provider = create_provider(state.cfg)
    state.state["model"] = f"{state.provider.name}/{state.provider.model}"
    # Start MCP manager so tools are available
    try:
        state.mcp_mgr.load_from_config(state.cfg)
        state.mcp_mgr.start()
        logger.info("MCP manager started — %d servers", len(state.mcp_mgr.servers))  # type: ignore[attr-defined,unused-ignore]
    except Exception as e:
        logger.warning("MCP manager start skipped: %s", e)
    ensure_docs(Path.cwd().resolve())
    logger.info("WIDDX API started — provider: %s/%s", state.provider.name, state.provider.model)
    yield
    # Shutdown
    try:
        state.mcp_mgr.stop()
    except Exception:
        pass

app = FastAPI(
    title="WIDDX Nexus API",
    version="3.0.0",
    description="REST API for WIDDX Nexus — Terminal AI Engineering Assistant",
    lifespan=lifespan,
)

# Restrict CORS to local origins by default; override via WIDDX_CORS_ORIGINS env var
_allowed_origins = os.environ.get("WIDDX_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Request size limit (ISS-004) ──────────────────────────────
_MAX_BODY_BYTES = int(os.environ.get("WIDDX_MAX_BODY_BYTES", 1_048_576))  # 1 MB default

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class _BodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds _MAX_BODY_BYTES."""
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {_MAX_BODY_BYTES} bytes limit."},
            )
        return await call_next(request)

app.add_middleware(_BodySizeMiddleware)

# ─── Health ──────────────────────────────────────────────────
@app.get("/api/health")
async def health(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    return {
        "status": "ok",
        "version": "3.0.0",
        "provider": state.provider.name,
        "model": state.provider.model,
        "turns": state.state.get("turns", 0),
        "cost": state.state.get("cost", 0.0),
    }

# ─── Chat ────────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    if not req.message.strip():
        raise HTTPException(400, "message is required")

    msgs = list(state.messages)
    if not any(m.get("role") == "system" for m in msgs):
        sp = state.cfg.get("system_prompt", "")
        sn = ", ".join(s.name for s in skill_manager.list_all()) or "none"
        msgs.insert(0, {"role": "system", "content": sp.replace("{skills_list}", sn)})

    try:
        ctx = state.scanner.build_context_block()
        if ctx:
            msgs = [m for m in msgs if not m.get("_project_context")]
            msgs.insert(0, {"role": "system", "content": ctx, "_project_context": True})
    except Exception as e:
        logger.debug("Scanner context skipped: %s", e)

    try:
        pt_ctx = build_context_block(Path.cwd().resolve())
        if pt_ctx:
            msgs = [m for m in msgs if not m.get("_project_docs")]
            msgs.insert(0, {"role": "system", "content": pt_ctx, "_project_docs": True})
    except Exception as e:
        logger.debug("Project docs context skipped: %s", e)

    try:
        ml = MemoryLearner(provider=state.provider)
        mem_ctx = ml.load_relevant(req.message)
        if mem_ctx:
            msgs = [m for m in msgs if not m.get("_memory_context")]
            msgs.insert(0, {"role": "system", "content": mem_ctx, "_memory_context": True})
    except Exception as e:
        logger.debug("Memory context skipped: %s", e)

    msgs.append({"role": "user", "content": req.message})

    td = list(tools.TOOL_DEFINITIONS)
    try:
        td.extend(state.mcp_mgr.get_all_tool_definitions())
    except Exception as e:
        logger.debug("MCP tool defs skipped: %s", e)

    try:
        # Offload synchronous chat to a thread so the event loop stays free
        msgs_out, state_out = await asyncio.to_thread(
            run_stream_turn, state.provider, msgs, state.state, td, state.cfg
        )
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

    last_content = ""
    for m in reversed(msgs_out):
        if m.get("role") == "assistant":
            last_content = m.get("content", "")
            break

    state.messages = msgs_out
    state.state = state_out

    try:
        project_state.save_session(state.messages, state.state)
    except Exception as e:
        logger.debug("Session save skipped: %s", e)

    return ChatResponse(
        response=last_content or "",
        model=state.state.get("model", ""),
        turns=state.state.get("turns", 0),
        cost=state.state.get("cost", 0.0),
    )

# ─── Providers ───────────────────────────────────────────────────
@app.get("/api/providers")
async def list_providers(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    return {
        "current": state.provider.name,
        "model": state.provider.model,
        "available": ["opencode-zen", "ollama", "deepseek", "openai", "gguf"],
        "models": get_available_models(state.provider.name, state.provider.base_url, force_refresh=True),
    }

@app.post("/api/providers/switch")
async def switch_provider(req: ProviderSwitch, _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    global state
    try:
        new_provider = create_provider({
            "provider": {
                "name": req.name,
                "model": req.model or "",
                "base_url": req.base_url or "",
            }
        })
        state.provider = new_provider
        state.state["model"] = f"{new_provider.name}/{new_provider.model}"
        state.cfg["provider"] = {"name": req.name, "model": new_provider.model}
        save_config(state.cfg)
        return {"status": "ok", "provider": new_provider.name, "model": new_provider.model}
    except Exception as e:
        raise HTTPException(400, f"Failed to switch provider: {e}")

@app.get("/api/sessions")
async def list_sessions(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    return {"messages": len(state.messages), "turns": state.state.get("turns", 0)}

@app.delete("/api/sessions")
async def clear_session(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    state.messages = []
    state.state["turns"] = 0
    state.state["cost"] = 0.0
    return {"status": "cleared"}

@app.get("/api/memory")
async def list_memory(query: str = "", _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    mem = MemoryStore()
    if query:
        return {"facts": mem.search(query)}
    return {"facts": mem.list_all(), "total": mem.total()}

@app.post("/api/memory")
async def save_memory(fact: MemoryFact, _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    mem = MemoryStore()
    mem.save(fact.name, fact.content, {"type": fact.type})
    return {"status": "saved", "name": fact.name}

@app.delete("/api/memory/{name}")
async def delete_memory(name: str, _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    mem = MemoryStore()
    if mem.delete(name):
        return {"status": "deleted"}
    raise HTTPException(404, f"Memory '{name}' not found")

@app.get("/api/tools")
async def list_tools(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    base = [{"name": t["name"], "description": t.get("description", "")[:100]} for t in tools.TOOL_DEFINITIONS]
    try:
        mcp_tools = [{"name": t["name"], "description": t.get("description", "")[:100]} for t in state.mcp_mgr.get_all_tool_definitions()]
    except Exception:
        mcp_tools = []
    return {"base": base, "mcp": mcp_tools, "total": len(base) + len(mcp_tools)}

@app.get("/api/project/docs")
async def get_docs(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    return load_docs(Path.cwd().resolve())

@app.post("/api/project/docs")
async def update_docs(update: DocUpdate, _auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    valid = ("PLAN.md", "DESIGN.md", "TASKS.md", "ROADMAP.md")
    if update.doc not in valid:
        raise HTTPException(400, f"Invalid doc. Use: {', '.join(valid)}")
    ok = update_doc(Path.cwd().resolve(), update.doc, update.content)
    if ok:
        return {"status": "updated", "doc": update.doc}
    raise HTTPException(500, "Failed to update doc")

@app.get("/api/project/status")
async def project_status(_auth=Depends(verify_api_key), _rl=Depends(rate_limit)):
    ctx = state.scanner.build_context_block()
    deps = detect_project_deps(Path.cwd().resolve())
    return {
        "context": ctx,
        "dependencies": {k: bool(v) for k, v in deps.items()},
    }

def main():
    try:
        from core.diagnostics import error_collector
        error_collector.enable()
    except Exception:
        pass
    import uvicorn
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    host = os.environ.get("WIDDX_API_HOST", "127.0.0.1")
    print(f"🚀 WIDDX API running at http://{host}:{port}")
    print(f"   Docs: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()

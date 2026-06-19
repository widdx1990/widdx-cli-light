"""WIDDX Cortex — REST API Server.

This script lives in `scripts/` to keep the repository root tidy. It adds the
project root to sys.path before importing the core application logic.
"""

import sys
from pathlib import Path

# Ensure project root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import time
import logging
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("❌ FastAPI required. Install: pip install fastapi uvicorn")
    sys.exit(1)

# ── WIDDX Core imports ──────────────────────────────────────
from core import config, tools
from core.config.settings import load as load_config, save as save_config
from core.providers.providers import (
    create_provider, get_available_models, resolve_model,
    fetch_free_models, fetch_ollama_models,
)
from core.memory import MemoryStore
from core.memory_learner import MemoryLearner
from core.project import state as project_state
from core.project.scanner import ProjectScanner
from core.project_tracker import ensure_docs, load_docs, update_doc, build_context_block
from core.auto_setup import detect_project_deps, learn_project
from core.skills import skill_manager
from core.mcp.client import get_mcp_manager
from core.chat import run_stream_turn

logger = logging.getLogger("widdx.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

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
        logger.info("MCP manager started — %d servers", len(state.mcp_mgr.servers))
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
    title="WIDDX Cortex API",
    version="3.0.0",
    description="REST API for WIDDX Cortex — Terminal AI Engineering Assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health ──────────────────────────────────────────────────
@app.get("/api/health")
async def health():
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
async def chat(req: ChatRequest):
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
async def list_providers():
    return {
        "current": state.provider.name,
        "model": state.provider.model,
        "available": ["opencode-zen", "ollama", "deepseek", "openai", "gguf"],
        "models": get_available_models(state.provider.name, state.provider.base_url, force_refresh=True),
    }

@app.post("/api/providers/switch")
async def switch_provider(req: ProviderSwitch):
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
async def list_sessions():
    return {"messages": len(state.messages), "turns": state.state.get("turns", 0)}

@app.delete("/api/sessions")
async def clear_session():
    state.messages = []
    state.state["turns"] = 0
    state.state["cost"] = 0.0
    return {"status": "cleared"}

@app.get("/api/memory")
async def list_memory(query: str = ""):
    mem = MemoryStore()
    if query:
        return {"facts": mem.search(query)}
    return {"facts": mem.list_all(), "total": mem.total()}

@app.post("/api/memory")
async def save_memory(fact: MemoryFact):
    mem = MemoryStore()
    mem.save(fact.name, fact.content, {"type": fact.type})
    return {"status": "saved", "name": fact.name}

@app.delete("/api/memory/{name}")
async def delete_memory(name: str):
    mem = MemoryStore()
    if mem.delete(name):
        return {"status": "deleted"}
    raise HTTPException(404, f"Memory '{name}' not found")

@app.get("/api/tools")
async def list_tools():
    base = [{"name": t["name"], "description": t.get("description", "")[:100]} for t in tools.TOOL_DEFINITIONS]
    try:
        mcp_tools = [{"name": t["name"], "description": t.get("description", "")[:100]} for t in state.mcp_mgr.get_all_tool_definitions()]
    except Exception:
        mcp_tools = []
    return {"base": base, "mcp": mcp_tools, "total": len(base) + len(mcp_tools)}

@app.get("/api/project/docs")
async def get_docs():
    return load_docs(Path.cwd().resolve())

@app.post("/api/project/docs")
async def update_docs(update: DocUpdate):
    valid = ("PLAN.md", "DESIGN.md", "TASKS.md", "ROADMAP.md")
    if update.doc not in valid:
        raise HTTPException(400, f"Invalid doc. Use: {', '.join(valid)}")
    ok = update_doc(Path.cwd().resolve(), update.doc, update.content)
    if ok:
        return {"status": "updated", "doc": update.doc}
    raise HTTPException(500, "Failed to update doc")

@app.get("/api/project/status")
async def project_status():
    ctx = state.scanner.build_context_block()
    deps = detect_project_deps(Path.cwd().resolve())
    return {
        "context": ctx,
        "dependencies": {k: bool(v) for k, v in deps.items()},
    }

def main():
    import uvicorn
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    print(f"🚀 WIDDX API running at http://localhost:{port}")
    print(f"   Docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

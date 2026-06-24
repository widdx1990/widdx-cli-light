# WIDDX Nexus — Imports Reference

> Complete import map showing what each module imports and what it exports.

## Public API (core/__init__.py)

The `core` package re-exports its key symbols for convenient access:

```python
from core import config, tools, providers, memory, activity, delegation
from core.config.settings import load, get, save
from core.proxy import proxy_manager, ProxyManager
from core.providers.providers import (
    Provider, ToolCall,
    OllamaProvider, OpenAICompatibleProvider, OpenCodeZenProvider,
    DeepSeekProvider, GGUFDirectProvider,
    fetch_free_models, create_provider,
    get_available_models, resolve_model, estimate_turn_cost,
)
from core.memory import MemoryStore
from core.activity import ActivityStore, get_store, add
from core.background import BackgroundTaskManager
from core.delegation import DelegationManager
from core.voice import TTSEngine
from core.cron.scheduler import CronScheduler
from core.gateway import GatewayCore, Platform, Message, Reply
from core.vision import describe_image, VisionMode, process_user_input_with_vision
from core.tools import TOOL_DEFINITIONS, execute, execute_with_skills
```

## Module Import Map

### cli/

| Module | Imports From core/ | Imports From stdlib | Imports From 3rd party |
|--------|-------------------|---------------------|------------------------|
| `cli/app.py` | `config, tools, providers, memory, skills, chat, ui_visual, mcp, session_v2, project_tracker` | `pathlib, os, sys, time` | `rich, prompt_toolkit` |
| `cli/commands.py` | `config, providers, tools, skills, memory, background, cron, gateway, sandbox, delegation, workflow, project_tracker` | `os, time` | `rich` |
| `cli/display.py` | `chat, ui_visual` | `textwrap` | `rich` |
| `cli/input.py` | `config` | `os` | `prompt_toolkit` |
| `cli/theme.py` | `ui_visual` | — | `rich` |

### tui/

| Module | Imports From core/ | Imports From stdlib | Imports From 3rd party |
|--------|-------------------|---------------------|------------------------|
| `tui/app.py` | `config, tools, ui_visual, mcp, skills, memory, providers, session_v2, chat` | `pathlib, datetime, os` | `textual, rich` |
| `tui/chat_engine.py` | `tools, chat, providers, memory_learner, skills, uil, project_tracker, session_v2` | `pathlib, json` | `textual` |
| `tui/commands.py` | `providers, tools, skills, memory, background, sandbox, delegation, workflow, session_v2, cron, gateway, mcp, project_tracker, ui_visual, config` | `os, time` | `rich` |
| `tui/state.py` | `config, tools, providers, memory, memory_learner, project, project_tracker, auto_setup, skills, mcp, workflow, session_v2` | `pathlib, datetime` | — |
| `tui/screens/settings.py` | `config, providers, mcp` | `os, pathlib` | `textual, rich` |
| `tui/screens/session_crud.py` | `session_v2` | `pathlib` | `textual, rich` |
| `tui/screens/memory_crud.py` | `memory` | — | `textual, rich` |

### scripts/

| Module | Imports From core/ | Imports From stdlib | Imports From 3rd party |
|--------|-------------------|---------------------|------------------------|
| `scripts/api_server.py` | `config, tools, providers, memory, memory_learner, project, project_tracker, auto_setup, skills, mcp, chat` | `sys, json, time, os, secrets, asyncio` | `fastapi, uvicorn, pydantic` |
| `scripts/web/server.py` | `_path, tools, providers, memory, session_v2, skills, mcp, sandbox, background, cron, gateway, delegation, project_tracker, auto_setup, project` | `pathlib, os, json, time, asyncio, logging` | `fastapi, uvicorn` |
| `scripts/web/chat.py` | `_path, chat, providers, memory, tools, mcp, session_v2, skills, project_tracker, auto_setup` | `json, time, asyncio, logging` | `fastapi` |
| `scripts/web/dashboard/__init__.py` | `_path` + 6 mixin imports | `pathlib, json, time` | `fastapi` |

### core/uil/

| Module | Imports From core/ | Imports From stdlib | External deps |
|--------|-------------------|---------------------|---------------|
| `brain.py` | `analyzer, router, planner, knowledge, verifier, contract, engine_adapters` | `time, logging` | None |
| `analyzer.py` | `contract` | `re, time, logging` | None |
| `router.py` | `contract, skills` | — | None |
| `planner.py` | `contract` | — | None |
| `verifier.py` | `contract` | `re, time, logging, pathlib` | None |
| `knowledge.py` | `contract` | `json, time, statistics, logging, pathlib` | None |
| `executors.py` | `contract` | `logging` | None |
| `contract.py` | — | `dataclasses, enum, typing` | None |

### core/agents/

| Module | Imports From core/ | Imports From stdlib | External deps |
|--------|-------------------|---------------------|---------------|
| `agent.py` | `tools, skills, chat, providers` | `json, uuid, time, datetime, pathlib` | `rich` |
| `executor_adapter.py` | `uil.contract` | `logging` | None |
| `expert.py` | `agent` | `dataclasses, pathlib` | `rich` |

### core/providers/

| Module | Imports From core/ | Imports From stdlib | External deps |
|--------|-------------------|---------------------|---------------|
| `providers.py` | All provider modules (re-export) | — | — |
| `base.py` | `proxy, config.keychain` | `json, time, uuid, threading` | `httpx` |
| `openai_compatible.py` | `base` | `json, time` | `httpx` |
| `deepseek.py` | `openai_compatible` | `time` | `httpx` |
| `opencode_zen.py` | `openai_compatible` | `time` | `httpx` |
| `ollama.py` | `base` | `json, time` | `httpx` |
| `gguf_provider.py` | `base` | `json, time, os, logging` | `httpx` |
| `factory.py` | All providers | `logging` | `httpx` |
| `free_models.py` | — | `json, time, logging` | `httpx` |

## Import Anti-Patterns Found

### 1. `__import__()` usage (avoids static analysis)

| File | Line | Pattern | Alternative |
|------|------|---------|-------------|
| `core/providers/base.py` | 16 | `logger = __import__("logging").getLogger(...)` | `import logging; logger = logging.getLogger(...)` |
| `core/providers/deepseek.py` | 10 | Same | Same |
| `core/providers/factory.py` | 18 | Same | Same |
| `core/providers/free_models.py` | 9 | Same | Same |
| `core/providers/gguf_provider.py` | 10 | Same | Same |
| `core/providers/ollama.py` | 9 | Same | Same |
| `core/providers/openai_compatible.py` | 9 | Same | Same |
| `core/providers/opencode_zen.py` | 12 | Same | Same |
| `core/tools/browser.py` | 9 | Same | Same |

### 2. Lazy imports inside function bodies

| File | Function | Why |
|------|----------|-----|
| `core/tools/__init__.py` | `execute_with_skills()` | Avoid circular import with skills.py |
| `core/uil/brain.py` | `_get_executor_map()` | Avoid circular import with agents |
| `core/tools/__init__.py` | `_bash()` | Import sandbox at call time |
| `scripts/api_server.py` | `chat()` endpoint | Import chat module at call time |

### 3. Wildcard imports

**None found.** ✅ All imports are explicit.

### 4. Unused re-exports in core/__init__.py

| Export | Actually imported by consumers? |
|--------|-------------------------------|
| `VisionMode` | No |
| `describe_image` | No |
| `process_user_input_with_vision` | No |

## Import Graph Depth (longest chains)

```
cli/app.py
  → core/__init__.py
    → core/providers/providers.py
      → core/providers/factory.py
        → core/providers/base.py
          → core/proxy.py
          → core/config/keychain.py

cli/app.py
  → core/chat.py
    → core/tools/__init__.py
      → core/tools/security.py
      → core/tools/browser.py
      → core/project_tracker.py
      → core/linter.py
      → core/multi_editor.py
        → core/diff_engine.py
      → core/sandbox.py
```

**Max depth: 7 hops** from entry point to leaf module.

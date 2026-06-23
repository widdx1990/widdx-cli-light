"""Dashboard — exposes all WIDDX systems via REST API."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("widdx.web.dashboard")

from core._path import ensure_project_root
ensure_project_root()

# Project root — used for disk-usage and file-tree operations
ROOT = Path(__file__).resolve().parent.parent


class Dashboard:
    """Aggregates all WIDDX systems for the Web UI."""

    def __init__(self):
        self._ready = False
        self._init_systems()

    def _init_systems(self):
        try:
            from core import config, tools
            self._cfg = config.settings.load()
            self._tool_defs = list(tools.TOOL_DEFINITIONS)
            self._ready = True
        except Exception as e:
            logger.error("Dashboard init: %s", e)

    # ── System Info (WIDDX Computer) ──

    def system_info(self) -> dict:
        """OS, CPU, RAM, disk, Python version."""
        import os, platform, shutil
        info = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "cpu_count": os.cpu_count() or 0,
        }
        try:
            total, used, free = shutil.disk_usage(ROOT)
            info["disk"] = {"total": total, "used": used, "free": free}
        except Exception:
            pass
        return info

    def running_processes(self) -> list[dict]:
        """List running background processes."""
        try:
            from core.background import BackgroundTaskManager
            mgr = BackgroundTaskManager()
            return [
                {"id": t.id, "status": t.status.value, "elapsed": t.elapsed}
                for t in mgr.list_agents()
            ]
        except Exception:
            return []

    # ── Cron Jobs ──

    def cron_jobs(self) -> list[dict]:
        try:
            from core.cron.store import JobStore
            store = JobStore()
            return store.list_jobs()
        except Exception as e:
            logger.debug("Cron list: %s", e)
            return []

    def cron_create(self, schedule: str, prompt: str) -> dict:
        try:
            from core.cron.scheduler import CronScheduler
            sched = CronScheduler()
            job_id = sched.create_job(schedule, prompt)
            return {"id": job_id, "status": "created"}
        except Exception as e:
            return {"error": str(e)}

    def cron_delete(self, job_id: str) -> dict:
        try:
            from core.cron.store import JobStore
            store = JobStore()
            store.delete_job(job_id)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}

    # ── Background Tasks ──

    def background_tasks(self) -> list[dict]:
        try:
            from core.background import background
            return [
                {"id": t.id, "status": t.status.value, "summary": (t.result or "")[:100]}
                for t in background.list_tasks()
            ]
        except Exception:
            return []

    # ── Sub-Agents ──

    def sub_agents(self) -> list[dict]:
        try:
            from core.delegation import delegation
            return [
                {"id": a.id, "status": a.status.value, "goal": a.goal[:60]}
                for a in delegation.list_agents()
            ]
        except Exception:
            return []

    # ── Memory ──

    def memories(self) -> list[dict]:
        try:
            from core.memory import MemoryStore
            mem = MemoryStore()
            return mem.list_all()
        except Exception:
            return []

    # ── Sessions ──

    def sessions(self) -> list[dict]:
        try:
            from core.session_search import SessionSearcher
            searcher = SessionSearcher()
            return searcher.list_recent(limit=20)
        except Exception:
            return []

    # ── Activity Feed ──

    def activity_feed(self, limit: int = 50) -> list[dict]:
        """Return recent activity events from the central ActivityStore."""
        try:
            from core.activity import get_store
            store = get_store()
            events = store.get_recent(limit=limit)
            if events:
                return events
        except Exception:
            pass
        return self._emergency_activity()

    def _emergency_activity(self) -> list[dict]:
        """Last resort — return placeholder events."""
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        return [
            {"id": "welcome", "type": "message", "icon": "fa-star", "agent": "system",
             "detail": "WIDDX Nexus Mission Control active", "status": "done",
             "timestamp": now, "elapsed": "—"},
        ]

    @staticmethod
    def _get_activity_store():
        """Return the global ActivityStore."""
        from core.activity import get_store
        return get_store()

    # ── Skills ──

    def skills(self) -> list[dict]:
        try:
            from core.skills import skill_manager
            return [
                {"name": s.name, "description": s.description[:80]}
                for s in skill_manager.list_all()
            ]
        except Exception:
            return []

    # ── Gateway Status ──

    def gateway_status(self) -> dict:
        """Return status of all communication channels."""
        channels = []
        try:
            from core.gateway.manager import GatewayManager
            mgr = GatewayManager()
            for ch in mgr.list_channels():
                channels.append({
                    "name": ch.name,
                    "icon": self._gateway_icon(ch.name),
                    "status": "connected" if ch.is_connected else "disconnected",
                    "last_message": str(ch.last_message_at) if ch.last_message_at else None,
                    "message_count": ch.message_count,
                    "error": ch.error,
                })
        except ImportError:
            channels = [
                {"name": "Telegram", "icon": "fa-telegram", "status": "not_available", "last_message": None, "message_count": 0, "error": "Gateway module not installed"},
                {"name": "Discord", "icon": "fa-discord", "status": "not_available", "last_message": None, "message_count": 0, "error": "Gateway module not installed"},
            ]
        except Exception as e:
            channels = [
                {"name": "Telegram", "icon": "fa-telegram", "status": "error", "last_message": None, "message_count": 0, "error": str(e)},
            ]

        return {
            "channels": channels,
            "total_channels": len(channels),
            "active_channels": sum(1 for c in channels if c["status"] == "connected"),
        }

    @staticmethod
    def _gateway_icon(name: str) -> str:
        icons = {"telegram": "fa-telegram", "discord": "fa-discord", "sms": "fa-comment-sms", "whatsapp": "fa-whatsapp"}
        return icons.get(name.lower(), "fa-plug")

    # ── Settings ──

    PROVIDERS_META = [
        {"id": "opencode-zen", "name": "OpenCode Zen", "icon": "fa-cloud", "default_base": "https://opencode.ai/zen/v1"},
        {"id": "deepseek", "name": "DeepSeek", "icon": "fa-brain", "default_base": "https://api.deepseek.com"},
        {"id": "openai", "name": "OpenAI", "icon": "fa-openai", "default_base": "https://api.openai.com/v1"},
        {"id": "ollama", "name": "Ollama (Local)", "icon": "fa-microchip", "default_base": "http://localhost:11434"},
        {"id": "gguf", "name": "GGUF (Local)", "icon": "fa-box", "default_base": "http://localhost:11434"},
    ]

    def get_settings(self) -> dict:
        """Return full settings with available providers and models."""
        cfg = {}
        try:
            from core.config.settings import load as load_cfg
            cfg = load_cfg()
        except Exception:
            pass

        provider_cfg = cfg.get("provider", {})
        current_provider = provider_cfg.get("name") or cfg.get("default_provider", "opencode-zen")

        # Build provider list
        providers = []
        for meta in self.PROVIDERS_META:
            models = self._fetch_models(meta["id"])
            providers.append({
                "id": meta["id"],
                "name": meta["name"],
                "icon": meta["icon"],
                "default_base": meta["default_base"],
                "models": models,
            })

        return {
            "provider": {
                "name": current_provider,
                "model": provider_cfg.get("model", ""),
                "base_url": provider_cfg.get("base_url", ""),
                "api_key": "",  # Never expose the actual key
                "has_key": bool(provider_cfg.get("api_key")),
            },
            "cli_theme": cfg.get("cli_theme", "dark"),
            "system_prompt": cfg.get("system_prompt", ""),
            "temperature": cfg.get("temperature", 0.7),
            "max_turns": cfg.get("max_turns", 10),
            "available_providers": providers,
            "config_path": str(cfg.get("_path", "")),
        }

    def update_settings(self, data: dict) -> dict:
        """Update config with new settings."""
        try:
            from core.config.settings import load as load_cfg, save as save_cfg
            cfg = load_cfg()

            provider = data.get("provider", {})
            if "name" in provider:
                cfg.setdefault("provider", {})["name"] = provider["name"]
            if "model" in provider:
                cfg.setdefault("provider", {})["model"] = provider["model"]
            if "base_url" in provider and provider["base_url"]:
                cfg.setdefault("provider", {})["base_url"] = provider["base_url"]
            if "api_key" in provider and provider["api_key"]:
                cfg.setdefault("provider", {})["api_key"] = provider["api_key"]

            if "system_prompt" in data:
                cfg["system_prompt"] = data["system_prompt"]
            if "temperature" in data:
                cfg["temperature"] = float(data["temperature"])
            if "max_turns" in data:
                cfg["max_turns"] = int(data["max_turns"])
            if "cli_theme" in data:
                cfg["cli_theme"] = str(data["cli_theme"]).lower()

            save_cfg(cfg)
            return {"status": "ok", "message": "Settings saved"}
        except Exception as e:
            logger.error("Settings save error: %s", e)
            return {"status": "error", "message": str(e)}

    def _fetch_models(self, provider_id: str) -> list[str]:
        """Fetch available models for a provider with timeout."""
        try:
            from core.providers.providers import get_available_models
            import threading
            result = []
            thread = threading.Thread(target=lambda: result.extend(get_available_models(provider_id)))
            thread.daemon = True
            thread.start()
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning("Model fetch timeout for %s", provider_id)
                return []
            return result[:50] if result else []
        except Exception:
            return []

    def get_provider_models(self, provider_id: str) -> dict:
        """Get models for a specific provider (for live refresh)."""
        import threading
        result = []
        thread = threading.Thread(target=lambda: result.extend(self._fetch_models(provider_id)))
        thread.daemon = True
        thread.start()
        thread.join(timeout=8.0)
        return {"provider": provider_id, "models": result[:50] if result else []}

    # ── Sandbox Computer ──

    def computer_info(self) -> dict:
        """Full WIDDX Computer state."""
        try:
            from core.sandbox import SandboxExecutor
            sb = SandboxExecutor(mode="auto")
            mode = sb.mode
        except Exception:
            mode = "unknown"

        return {
            "mode": mode,
            "system": self.system_info(),
            "processes": self.running_processes(),
            "cron": self.cron_jobs(),
            "background": self.background_tasks(),
            "agents": self.sub_agents(),
            "memories": len(self.memories()),
            "sessions": len(self.sessions()),
            "skills": len(self.skills()),
        }

    def computer_exec(self, command: str) -> dict:
        """Execute a command in the WIDDX Computer sandbox."""
        try:
            from core.sandbox import SandboxExecutor
            sb = SandboxExecutor(mode="auto")
            result = sb.execute(command, timeout=60)
            return {
                "stdout": result.stdout if hasattr(result, 'stdout') else str(result),
                "stderr": result.stderr if hasattr(result, 'stderr') else "",
                "exit_code": result.exit_code if hasattr(result, 'exit_code') else 0,
                "mode": result.mode if hasattr(result, 'mode') else sb.mode,
            }
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1, "mode": "error"}

    # ════════════════════════════════════════════════════════
    # NEW: Memory CRUD (Create, Update, Delete)
    # ════════════════════════════════════════════════════════

    def memory_create(self, content: str, tags: str = "") -> dict:
        """Add a new memory entry."""
        try:
            from core.memory import MemoryStore
            mem = MemoryStore()
            mem.add(content, tags=tags)
            return {"status": "ok", "message": "Memory added"}
        except Exception as e:
            return {"error": str(e)}

    def memory_delete(self, memory_id: str) -> dict:
        """Delete a memory entry."""
        try:
            from core.memory import MemoryStore
            mem = MemoryStore()
            mem.delete(memory_id)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}

    def memory_search(self, query: str) -> list[dict]:
        """Search memory entries."""
        try:
            from core.memory import MemoryStore
            mem = MemoryStore()
            return mem.search(query)
        except Exception:
            return []

    # ════════════════════════════════════════════════════════
    # NEW: Session Save / Load / Export
    # ════════════════════════════════════════════════════════

    def session_save(self, name: str, messages: list) -> dict:
        """Save current session with a name."""
        try:
            from core.database import SessionDB
            db = SessionDB()
            session_id = db.save(name, messages)
            return {"id": session_id, "status": "saved"}
        except Exception as e:
            return {"error": str(e)}

    def session_load(self, session_id: str) -> dict:
        """Load a saved session."""
        try:
            from core.database import SessionDB
            db = SessionDB()
            session = db.load(session_id)
            if session:
                return {"status": "ok", "session": session}
            return {"error": "Session not found"}
        except Exception as e:
            return {"error": str(e)}

    def session_delete(self, session_id: str) -> dict:
        """Delete a saved session."""
        try:
            from core.database import SessionDB
            db = SessionDB()
            db.delete(session_id)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}

    def session_export(self, session_id: str) -> dict:
        """Export session as markdown."""
        try:
            from core.database import SessionDB
            db = SessionDB()
            session = db.load(session_id)
            if not session:
                return {"error": "Session not found"}
            lines = [f"# Chat: {session.get('name', 'Untitled')}", ""]
            for msg in session.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"## {role.upper()}")
                lines.append(content)
                lines.append("")
            return {"status": "ok", "markdown": "\n".join(lines)}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: MCP Management
    # ════════════════════════════════════════════════════════

    def mcp_status(self) -> list[dict]:
        """List all MCP servers and their status."""
        try:
            from core.mcp.client import MCPClient
            client = MCPClient()
            return client.list_servers()
        except Exception:
            return []

    def mcp_add(self, name: str, command: str, args: list = None) -> dict:
        """Add a new MCP server."""
        try:
            from core.mcp.client import MCPClient
            client = MCPClient()
            client.add_server(name, command, args or [])
            return {"status": "added", "name": name}
        except Exception as e:
            return {"error": str(e)}

    def mcp_remove(self, name: str) -> dict:
        """Remove an MCP server."""
        try:
            from core.mcp.client import MCPClient
            client = MCPClient()
            client.remove_server(name)
            return {"status": "removed", "name": name}
        except Exception as e:
            return {"error": str(e)}

    def mcp_restart(self, name: str) -> dict:
        """Restart an MCP server."""
        try:
            from core.mcp.client import MCPClient
            client = MCPClient()
            client.restart_server(name)
            return {"status": "restarted", "name": name}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Proxy Settings
    # ════════════════════════════════════════════════════════

    def proxy_status(self) -> dict:
        """Get current proxy settings."""
        try:
            from core.proxy import proxy_manager
            return proxy_manager.get_status()
        except Exception:
            return {"enabled": False, "http": "", "https": ""}

    def proxy_update(self, http: str = "", https: str = "", enabled: bool = False) -> dict:
        """Update proxy settings."""
        try:
            from core.proxy import proxy_manager
            proxy_manager.set(http=http, https=https, enabled=enabled)
            return {"status": "updated"}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Permissions Management
    # ════════════════════════════════════════════════════════

    def permissions_status(self) -> dict:
        """Get current permission level."""
        try:
            from core.permissions import permission_manager
            return {
                "level": permission_manager.level,
                "levels": permission_manager.available_levels(),
            }
        except Exception:
            return {"level": "normal", "levels": ["permissive", "normal", "strict", "silent"]}

    def permissions_set(self, level: str) -> dict:
        """Set permission level."""
        try:
            from core.permissions import permission_manager
            permission_manager.set_level(level)
            return {"status": "set", "level": level}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: GGUF Model Management
    # ════════════════════════════════════════════════════════

    def gguf_models(self) -> list[dict]:
        """List available GGUF models."""
        try:
            from core.gguf import GGUFManager
            mgr = GGUFManager()
            return mgr.list_models()
        except Exception:
            return []

    def gguf_load(self, path: str) -> dict:
        """Load a GGUF model."""
        try:
            from core.gguf import GGUFManager
            mgr = GGUFManager()
            mgr.load(path)
            return {"status": "loaded", "path": path}
        except Exception as e:
            return {"error": str(e)}

    def gguf_unload(self) -> dict:
        """Unload the current GGUF model."""
        try:
            from core.gguf import GGUFManager
            mgr = GGUFManager()
            mgr.unload()
            return {"status": "unloaded"}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: System Debug / Doctor
    # ════════════════════════════════════════════════════════

    def debug_info(self) -> dict:
        """Get full debug information."""
        try:
            from core.diagnostics import error_collector
            return {
                "errors": error_collector.get_recent(limit=50),
                "config": str(self._cfg) if hasattr(self, '_cfg') else "N/A",
                "tools": len(self._tool_defs) if hasattr(self, '_tool_defs') else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def doctor_check(self) -> list[dict]:
        """Run system diagnostics and return issues."""
        issues = []
        checks = [
            ("LLM Provider", self._check_provider),
            ("Config File", self._check_config),
            ("Sandbox", self._check_sandbox),
            ("Memory", self._check_memory),
            ("Cron Scheduler", self._check_cron),
            ("Python Version", self._check_python),
        ]
        for name, check_fn in checks:
            try:
                result = check_fn()
                issues.append({"check": name, **result})
            except Exception as e:
                issues.append({"check": name, "status": "error", "message": str(e)})
        return issues

    def _check_provider(self) -> dict:
        try:
            from core.providers.providers import create_provider
            from core.config.settings import load as load_cfg
            cfg = load_cfg()
            p = create_provider(cfg)
            return {"status": "ok" if p else "warning", "message": f"Provider: {p.name if p else 'None'}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_config(self) -> dict:
        try:
            from core.config.settings import load as load_cfg
            cfg = load_cfg()
            return {"status": "ok", "message": f"Config loaded: {len(cfg)} keys"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_sandbox(self) -> dict:
        try:
            from core.sandbox import SandboxExecutor
            sb = SandboxExecutor(mode="auto")
            return {"status": "ok", "message": f"Sandbox mode: {sb.mode}"}
        except Exception as e:
            return {"status": "warning", "message": f"Sandbox unavailable: {e}"}

    def _check_memory(self) -> dict:
        try:
            from core.memory import MemoryStore
            mem = MemoryStore()
            count = len(mem.list_all())
            return {"status": "ok", "message": f"{count} memories"}
        except Exception:
            return {"status": "warning", "message": "Memory store unavailable"}

    def _check_cron(self) -> dict:
        try:
            from core.cron.store import JobStore
            store = JobStore()
            jobs = store.list_jobs()
            return {"status": "ok", "message": f"{len(jobs)} jobs scheduled"}
        except Exception:
            return {"status": "info", "message": "Cron scheduler not active"}

    def _check_python(self) -> dict:
        import sys
        v = sys.version_info
        ok = v.major >= 3 and v.minor >= 10
        return {"status": "ok" if ok else "error", "message": f"Python {v.major}.{v.minor}.{v.micro}"}

    # ════════════════════════════════════════════════════════
    # NEW: Manifest Management
    # ════════════════════════════════════════════════════════

    def manifest_status(self) -> dict:
        """Get MANIFEST.json status."""
        try:
            from core.project.manifest import ManifestManager
            mgr = ManifestManager()
            return mgr.get_status()
        except Exception:
            return {"exists": False, "message": "Manifest system unavailable"}

    def manifest_scan(self) -> dict:
        """Trigger a manifest scan."""
        try:
            from core.project.scanner import ProjectScanner
            scanner = ProjectScanner()
            scanner.scan()
            return {"status": "scanned", "changes": scanner.changes_found()}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Git Branch / Undo
    # ════════════════════════════════════════════════════════

    def git_branches(self) -> list[dict]:
        """List git branches."""
        try:
            import subprocess
            result = subprocess.run(["git", "branch", "-a"], capture_output=True, text=True, timeout=5)
            branches = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    is_current = line.startswith("*")
                    name = line.replace("*", "").strip()
                    branches.append({"name": name, "current": is_current})
            return branches
        except Exception:
            return []

    def git_undo(self) -> dict:
        """Undo last git commit (soft reset)."""
        try:
            import subprocess
            result = subprocess.run(["git", "reset", "--soft", "HEAD~1"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return {"status": "undone", "message": "Last commit undone (soft reset)"}
            return {"error": result.stderr.strip()}
        except Exception as e:
            return {"error": str(e)}

    def git_status(self) -> dict:
        """Get git status summary."""
        try:
            import subprocess
            status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=5)
            log = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True, timeout=5)
            return {
                "changes": status.stdout.strip(),
                "recent_commits": log.stdout.strip(),
                "dirty": bool(status.stdout.strip()),
            }
        except Exception:
            return {"changes": "", "recent_commits": "", "dirty": False}

    # ════════════════════════════════════════════════════════
    # NEW: Token Budget
    # ════════════════════════════════════════════════════════

    def token_budget_status(self) -> dict:
        """Get token budget info."""
        try:
            from core.token_budget import TokenBudget
            tb = TokenBudget()
            return {
                "used": tb.used,
                "limit": tb.limit,
                "remaining": tb.remaining(),
                "percentage": tb.percentage(),
            }
        except Exception:
            return {"used": 0, "limit": 0, "remaining": 0, "percentage": 0}

    def token_budget_reset(self) -> dict:
        """Reset token budget."""
        try:
            from core.token_budget import TokenBudget
            tb = TokenBudget()
            tb.reset()
            return {"status": "reset"}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Checkpoints
    # ════════════════════════════════════════════════════════

    def checkpoints_list(self) -> list[dict]:
        """List all checkpoints."""
        try:
            from core.checkpoint import CheckpointManager
            mgr = CheckpointManager()
            return mgr.list_checkpoints()
        except Exception:
            return []

    def checkpoint_create(self) -> dict:
        """Create a new checkpoint."""
        try:
            from core.checkpoint import CheckpointManager
            mgr = CheckpointManager()
            cp = mgr.create_checkpoint()
            return {"status": "created", "id": cp.id, "timestamp": cp.timestamp}
        except Exception as e:
            return {"error": str(e)}

    def checkpoint_restore(self, checkpoint_id: str) -> dict:
        """Restore a checkpoint."""
        try:
            from core.checkpoint import CheckpointManager
            mgr = CheckpointManager()
            mgr.restore(checkpoint_id)
            return {"status": "restored", "id": checkpoint_id}
        except Exception as e:
            return {"error": str(e)}

    def checkpoint_delete(self, checkpoint_id: str) -> dict:
        """Delete a checkpoint."""
        try:
            from core.checkpoint import CheckpointManager
            mgr = CheckpointManager()
            mgr.delete(checkpoint_id)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Plugin Management
    # ════════════════════════════════════════════════════════

    def plugins_list(self) -> list[dict]:
        """List all plugins."""
        try:
            from core.plugin_loader import PluginLoader
            loader = PluginLoader()
            return loader.list_plugins()
        except Exception:
            return []

    def plugin_enable(self, name: str) -> dict:
        """Enable a plugin."""
        try:
            from core.plugin_loader import PluginLoader
            loader = PluginLoader()
            loader.enable(name)
            return {"status": "enabled", "name": name}
        except Exception as e:
            return {"error": str(e)}

    def plugin_disable(self, name: str) -> dict:
        """Disable a plugin."""
        try:
            from core.plugin_loader import PluginLoader
            loader = PluginLoader()
            loader.disable(name)
            return {"status": "disabled", "name": name}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Workflow Management
    # ════════════════════════════════════════════════════════

    def workflows_list(self) -> list[dict]:
        """List all workflows."""
        try:
            from core.workflow import WorkflowEngine
            engine = WorkflowEngine()
            return engine.list_workflows()
        except Exception:
            return []

    def workflow_run(self, workflow_id: str) -> dict:
        """Run a workflow."""
        try:
            from core.workflow import WorkflowEngine
            engine = WorkflowEngine()
            result = engine.run(workflow_id)
            return {"status": "completed", "result": str(result)[:200]}
        except Exception as e:
            return {"error": str(e)}

    def workflow_create(self, name: str, steps: list) -> dict:
        """Create a new workflow."""
        try:
            from core.workflow import WorkflowEngine
            engine = WorkflowEngine()
            wf = engine.create(name, steps)
            return {"status": "created", "id": wf.id}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: Version / App Info
    # ════════════════════════════════════════════════════════

    def app_version(self) -> dict:
        """Get full version info."""
        try:
            from core import version
            return {
                "version": version.VERSION,
                "build": version.BUILD,
                "python": version.PYTHON_VERSION,
            }
        except Exception:
            return {"version": "3.0.0", "build": "dev", "python": sys.version.split()[0]}

    # ════════════════════════════════════════════════════════
    # NEW: Auto-Commit Status
    # ════════════════════════════════════════════════════════

    def autocommit_status(self) -> dict:
        """Get auto-commit status."""
        try:
            from core.auto_commit import AutoCommit
            ac = AutoCommit()
            return {
                "enabled": ac.enabled,
                "interval": ac.interval,
                "last_commit": ac.last_commit,
            }
        except Exception:
            return {"enabled": False, "interval": 0, "last_commit": None}

    def autocommit_toggle(self) -> dict:
        """Toggle auto-commit on/off."""
        try:
            from core.auto_commit import AutoCommit
            ac = AutoCommit()
            ac.toggle()
            return {"status": "toggled", "enabled": ac.enabled}
        except Exception as e:
            return {"error": str(e)}

    # ════════════════════════════════════════════════════════
    # NEW: API Key Management (multi-key)
    # ════════════════════════════════════════════════════════

    def apikeys_list(self) -> list[dict]:
        """List all stored API keys (without exposing values)."""
        try:
            from core.config.settings import load as load_cfg
            cfg = load_cfg()
            providers = cfg.get("provider", {})
            keys = {}
            for p_name, p_cfg in providers.items() if isinstance(providers, dict) else []:
                if isinstance(p_cfg, dict) and p_cfg.get("api_key"):
                    keys[p_name] = {"has_key": True, "masked": p_cfg["api_key"][:8] + "..."}
            return keys
        except Exception:
            return {}

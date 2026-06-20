"""Dashboard — exposes all WIDDX systems via REST API."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger("widdx.web.dashboard")

from core._path import ensure_project_root
ensure_project_root()


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

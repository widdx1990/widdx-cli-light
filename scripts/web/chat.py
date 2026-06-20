"""Web UI — Chat handler. Uses UIL Brain for intelligent task processing.

Architecture:
  ChatHandler → UnifiedIntelligenceLayer (brain.process)
  → analyze → route → plan → execute → verify → knowledge → feedback
  → Returns ExecutionResult with summary + tool calls

Usage:
    from scripts.web.chat import ChatHandler
    handler = ChatHandler()
    response = handler.chat("hello")
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger("widdx.web.chat")

from core._path import ensure_project_root
ensure_project_root()


class ChatHandler:
    """Handles chat messages via the UIL Brain pipeline.

    The UIL Brain classifies, routes, plans, executes, verifies,
    and records every interaction — single-turn or autonomous.
    """

    def __init__(self):
        self._uil: Any = None
        self._cfg: dict = {}
        self._init_uil()

    def _init_uil(self):
        """Initialize the UIL Brain from config."""
        try:
            from core.config.settings import load as load_cfg
            from core.uil import UnifiedIntelligenceLayer

            self._cfg = load_cfg()
            provider_cfg = self._cfg.get("provider", {})

            # Create provider from config
            from core.providers.providers import create_provider
            provider = create_provider(self._cfg)

            # Initialize UIL Brain with provider
            self._uil = UnifiedIntelligenceLayer(
                provider=provider,
                tool_defs=self._get_tool_defs(),
            )
            logger.info(
                "ChatHandler: UIL ready — provider=%s model=%s",
                provider.name, provider.model,
            )
        except Exception as e:
            logger.error("ChatHandler init: %s", e)

    def _get_tool_defs(self) -> list[dict]:
        """Get tool definitions from the core tools module."""
        try:
            from core import tools
            return list(tools.TOOL_DEFINITIONS)
        except Exception:
            return []

    def chat(self, message: str, history: list[dict] | None = None) -> dict:
        """Send a message through the UIL Brain pipeline.

        Args:
            message: User message text.
            history: Previous messages list.

        Returns:
            {"content": str, "tools": list[dict], "error": str | None}
        """
        if self._uil is None:
            return {"content": "", "error": "UIL Brain not initialized"}

        try:
            # Convert history to UIL format
            uil_history = list(history or [])

            # Process through UIL Brain
            result, _routing = self._uil.process(
                user_input=message,
                messages=uil_history,
            )

            # Log to ActivityStore
            try:
                from core.activity import add as add_event
                add_event("message", detail=message[:80], icon="fa-user", agent="user", status="done")
                content = getattr(result, "summary", "") or ""
                if content:
                    add_event("message", detail=content[:80], icon="fa-robot", agent="widdx", status="done")
                for tc in (getattr(result, "tools_used", []) or []):
                    add_event("tool_call", detail=str(tc)[:60], icon="fa-wrench", agent="widdx", status="done")
            except Exception:
                pass

            # Extract content and tool calls from ExecutionResult
            content = getattr(result, "summary", "") or ""
            tool_calls = getattr(result, "tools_used", []) or []

            # Format tool calls for the frontend
            tools_result = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    tools_result.append(tc)
                else:
                    tools_result.append({"name": str(tc)})

            # Strip thinking tags for clean display
            clean = content
            for tag in ("[thinking]", "[/thinking]", "<thinking>", "</thinking>"):
                clean = clean.replace(tag, "")
            clean = clean.strip()

            return {
                "content": clean or "",
                "tools": tools_result,
                "error": None,
            }
        except Exception as e:
            logger.error("ChatHandler error: %s", e, exc_info=True)
            return {"content": "", "error": str(e)}

    @property
    def info(self) -> dict:
        """Return UIL/provider info."""
        if self._uil:
            provider = getattr(self._uil, "provider", None)
            if provider:
                return {
                    "name": getattr(provider, "name", "uil"),
                    "model": getattr(provider, "model", "unknown"),
                    "online": True,
                }
            return {"name": "uil", "model": "brain", "online": True}
        return {"name": "none", "model": "none", "online": False}

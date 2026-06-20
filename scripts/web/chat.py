"""Web UI — Chat handler. Connects to WIDDX providers.

Usage:
    from scripts.web.chat import ChatHandler
    handler = ChatHandler()
    response = handler.chat("hello")
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("widdx.web.chat")

# Ensure project root is in path
ROOT = str(Path(__file__).resolve().parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class ChatHandler:
    """Handles chat messages via WIDDX providers."""

    def __init__(self):
        self._provider: Any = None
        self._tool_defs: list[dict] = []
        self._cfg: dict = {}
        self._init_provider()

    def _init_provider(self):
        """Initialize the LLM provider from config."""
        try:
            from core.config.settings import load as load_cfg
            from core.providers.providers import create_provider

            self._cfg = load_cfg()
            self._provider = create_provider(self._cfg)
            self._tool_defs = []
            from core import tools
            self._tool_defs = list(tools.TOOL_DEFINITIONS)
            logger.info("ChatHandler: provider=%s model=%s",
                        self._provider.name, self._provider.model)
        except Exception as e:
            logger.error("ChatHandler init: %s", e)

    def chat(self, message: str, history: list[dict] | None = None) -> dict:
        """Send a message and get a response.

        Args:
            message: User message text.
            history: Previous messages list.

        Returns:
            {"content": str, "error": str | None}
        """
        if self._provider is None:
            return {"content": "", "error": "No provider configured"}

        messages = list(history or [])
        messages.append({"role": "user", "content": message})

        try:
            content, tool_calls = self._provider.chat(
                messages, self._tool_defs,
                self._cfg.get("temperature", 0.7),
            )
            tools_result = []
            for tc in (tool_calls or []):
                tools_result.append({"name": tc.name, "args": tc.args})

            # Strip thinking tags for clean display
            clean = (content or "")
            for tag in ("[thinking]", "[/thinking]", "<thinking>", "</thinking>"):
                clean = clean.replace(tag, "")
            return {
                "content": clean.strip() or "",
                "tools": tools_result,
                "error": None,
            }
        except Exception as e:
            logger.error("Chat error: %s", e)
            return {"content": "", "error": str(e)}

    def stream_chat(self, message: str, history: list[dict] | None = None):
        """Generator that yields streaming chunks via WebSocket.

        Yields:
            dict with keys: type ("text", "tool", "reasoning", "done", "error")
        """
        if self._provider is None:
            yield {"type": "error", "data": "No provider configured"}
            return

        messages = list(history or [])
        messages.append({"role": "user", "content": message})

        try:
            if hasattr(self._provider, "stream"):
                for event in self._provider.stream(
                    messages, self._tool_defs,
                    self._cfg.get("temperature", 0.7),
                ):
                    if event["type"] == "content":
                        yield {"type": "text", "data": event["data"]}
                    elif event["type"] == "reasoning":
                        yield {"type": "reasoning", "data": event["data"]}
                    elif event["type"] == "tool":
                        yield {"type": "tool", "data": event["data"]}
                    elif event["type"] == "error":
                        yield {"type": "error", "data": event["data"]}
                    elif event["type"] == "done":
                        content, calls = event["data"]
                        yield {"type": "done", "data": content or ""}
                        return
            else:
                content, calls = self._provider.chat(
                    messages, self._tool_defs,
                    self._cfg.get("temperature", 0.7),
                )
                yield {"type": "done", "data": content or ""}
        except Exception as e:
            logger.error("Stream error: %s", e)
            yield {"type": "error", "data": str(e)}

    @property
    def info(self) -> dict:
        """Return provider info."""
        if self._provider:
            return {
                "name": self._provider.name,
                "model": self._provider.model,
                "online": True,
            }
        return {"name": "none", "model": "none", "online": False}

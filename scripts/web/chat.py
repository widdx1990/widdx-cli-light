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
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.uil.contract import ExecutionResult

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
        self._session_id: str | None = None
        self._init_uil()

    def new_session(self):
        """Force-create a new session, abandoning the current one."""
        self._session_id = None
        return self._ensure_session()

    def _ensure_session(self):
        """Get or create the current session ID."""
        if self._session_id:
            return self._session_id
        try:
            from core.database import get_db
            db = get_db()
            sessions = db.list_sessions(limit=1)
            if sessions:
                self._session_id = sessions[0]["id"]
            else:
                self._session_id = db.create_session("Web UI Session")
        except Exception:
            import uuid
            self._session_id = str(uuid.uuid4())
        return self._session_id

    def _save_message(self, role: str, content: str):
        """Persist a message to the database."""
        try:
            from core.database import get_db
            db = get_db()
            sid = self._ensure_session()
            db.add_message(sid, role, content)
        except Exception:
            pass  # non-critical — session persistence failure shouldn't break chat

    def _init_uil(self):
        """Initialize the UIL Brain from config + auto-setup project."""
        try:
            from core.config.settings import load as load_cfg
            from core.uil import UnifiedIntelligenceLayer

            self._cfg = load_cfg()
            provider_cfg = self._cfg.get("provider", {})

            # ── Auto-setup: create planning docs + index project ──
            try:
                from pathlib import Path as _Path
                from core.project_tracker import ensure_docs, build_context_block
                cwd = _Path.cwd()
                ensure_docs(cwd)
                # Build project context for injection into system prompt
                self._project_context = build_context_block(cwd) or ""
            except Exception:
                self._project_context = ""

            # ── Web UI: PERMISSIVE to avoid blocking agent tools ──
            # The Web UI has no stdin for interactive Rich prompts.
            # Permission is handled via the UI's own confirmation system.
            try:
                import core.permissions as _perms
                if _perms._permission_manager is None:
                    pm = _perms.PermissionManager()
                    pm._level = _perms.PermissionLevel.PERMISSIVE
                    _perms._permission_manager = pm
            except Exception:
                pass

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

    def _clean_content(self, content: str) -> str:
        """Strip thinking tags and internal reasoning from content."""
        clean = content
        for tag in ("[thinking]", "[/thinking]", "<thinking>", "</thinking>"):
            clean = clean.replace(tag, "")

        import re
        marker_pat = (
            r'(?:^|\n)\s*(?:'
            r'Response\s+Generation\s*:|'
            r'Response\s+strategy\s*:|'
            r'Final\s+Response\s*:|'
            r'Final\s+Answer\s*:|'
            r'Output\s*:|'
            r'Answer\s*:'
            r')\s*\n*'
        )
        split_result = re.split(marker_pat, clean, flags=re.IGNORECASE)
        if len(split_result) > 1:
            clean = split_result[-1].strip()
        else:
            lines = clean.split('\n')
            kept = []
            found_final = False
            for line in lines:
                s = line.strip()
                if not s:
                    if not found_final:
                        continue
                    kept.append(line)
                    continue
                if not found_final:
                    if re.match(r'^Thinking\.?\s*$', s, re.IGNORECASE):
                        continue
                    if re.match(r'^\d+\.\s+\*\*', s):
                        continue
                    if re.match(r'^[\*\-]\s{2,}\w+', s):
                        continue
                    if re.match(r"^(Let(?:'s)?\s|I\s(?:should|need|can|will|must|think)|"
                                r"My\s|The\s(user|assistant|prompt|model)|"
                                r"Wait[,;]|Actually[,;]|Ah[,;]|"
                                r"Response\s+strategy|Strategy[:;])",
                                s, re.IGNORECASE):
                        continue
                    found_final = True
                kept.append(line)
            if found_final:
                clean = '\n'.join(kept).strip()
            else:
                clean = '\n'.join(l for l in lines if l.strip()).strip()
        return clean

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

            # ── Inject working directory context ──────────────────
            from pathlib import Path
            cwd = str(Path.cwd().resolve())
            cwd_msg = {
                "role": "system",
                "content": (
                    f"<working_directory>\n"
                    f"  You are working in: {cwd}\n"
                    f"  ALL files you create MUST go in this directory.\n"
                    f"  Use relative paths. This is the project root.\n"
                    f"  Do NOT use /tmp, /workspace, or any Linux paths.\n"
                    f"</working_directory>"
                ),
                "_cwd_context": True,
            }
            uil_history.insert(0, cwd_msg)

            # ── Inject project context (PLAN/DESIGN/TASKS/ROADMAP) ──
            if self._project_context:
                uil_history.insert(0, {
                    "role": "system",
                    "content": (
                        "<project_context>\n"
                        f"{self._project_context}\n"
                        "Use this context to understand the project goals, "
                        "architecture, current tasks, and roadmap.\n"
                        "Update these docs via the project_tracker when you "
                        "complete tasks or make design decisions.\n"
                        "</project_context>"
                    ),
                    "_project_context": True,
                })

            # ── Inject learned improvements from SelfImprove ──
            try:
                from core.self_improve import get_improver
                improver = get_improver()
                suggestions = improver.suggest_prompt_improvements()
                if suggestions:
                    uil_history.insert(0, {
                        "role": "system",
                        "content": (
                            "<learned_improvements>\n"
                            "Based on past errors, follow these rules:\n"
                            + "\n".join(f"- {s}" for s in suggestions[:5]) +
                            "\n</learned_improvements>"
                        ),
                    })
            except Exception:
                pass

            # ── Inject Architecture Decision Records ──
            try:
                from core.adr import adr_manager
                adr_context = adr_manager.get_context_for_prompt()
                if adr_context:
                    uil_history.insert(0, {
                        "role": "system",
                        "content": (
                            f"{adr_context}\n\n"
                            "DO NOT suggest alternatives listed as 'Rejected' above. "
                            "They were already evaluated and discarded."
                        ),
                    })
            except Exception:
                pass

            # ── Level 5: Unified StateManager context ──
            try:
                from core.state_manager import get_state_manager
                sm = get_state_manager()
                unified = sm.get_full_context(goal=message)
                if unified:
                    uil_history.insert(0, {"role": "system", "content": unified})
            except Exception:
                pass

            # ── Inject Decision Layer guidance ──
            try:
                from core.decision_layer import get_decision_layer
                guidance = get_decision_layer().get_context_for_prompt()
                if guidance:
                    uil_history.insert(0, {"role": "system", "content": guidance})
            except Exception:
                pass

            # ── Inject Learning: proven patterns ──
            try:
                from core.learning.pattern_library import UnifiedPatternStore
                store = UnifiedPatternStore()
                pattern_ctx = store.get_context_for_prompt(query=message)
                if pattern_ctx:
                    uil_history.insert(0, {"role": "system", "content": pattern_ctx})
            except Exception:
                pass

            # ── Inject Strategy Memory (World Model) ──
            try:
                from core.world_model import get_world_model
                wm = get_world_model()
                strat_ctx = wm.strategies.get_context_for_prompt(message)
                if strat_ctx:
                    uil_history.insert(0, {"role": "system", "content": strat_ctx})
            except Exception:
                pass

            # ── Inject User Preferences ──
            try:
                from core.learning.pattern_extractor import UserPreferenceLearner
                upl = UserPreferenceLearner()
                pref_ctx = upl.get_context_for_prompt()
                if pref_ctx:
                    uil_history.insert(0, {"role": "system", "content": pref_ctx})
            except Exception:
                pass

            # ── Inject Knowledge Graph context ──
            try:
                from core.knowledge_graph import get_knowledge_graph
                kg = get_knowledge_graph()
                kg_snippet = kg.get_context_snippet()
                if kg_snippet:
                    uil_history.insert(0, {"role": "system", "content": kg_snippet})
            except Exception:
                pass

            # ── Auto-suggest relevant skills ──────────────────────
            suggested_skills = []
            try:
                from core.skills import skill_manager
                suggestions = skill_manager.suggest_skills(message)
                suggested_skills = [
                    {"name": s.name, "icon": s.icon, "description": s.description[:80]}
                    for s in suggestions[:3]
                ]
            except Exception:
                pass

            # Process through UIL Brain (pass cfg for engine feature flags)
            result, _routing = self._uil.process(
                user_input=message,
                messages=uil_history,
                cfg=self._cfg,
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

            clean = self._clean_content(content)

            # ── Persist to session database ──
            self._save_message("user", message)
            if clean:
                self._save_message("assistant", clean)

            return {
                "content": clean or "",
                "tools": tools_result,
                "error": None,
                "suggested_skills": suggested_skills,
            }
        except Exception as e:
            logger.error("ChatHandler error: %s", e, exc_info=True)
            from core.utils import sanitize_error
            return {"content": "", "error": sanitize_error(str(e))}

    def chat_stream(self, message: str, history: list[dict] | None = None):
        """Generator that yields streaming events during UIL processing.

        Yields dicts with keys: type (reasoning, text, tool, tool_result, done), data

        Runs UIL processing in a background thread, yielding events as they occur.
        """
        if self._uil is None:
            yield {"type": "error", "data": "UIL Brain not initialized"}
            return

        self._save_message("user", message)

        import queue
        import threading

        event_queue: queue.Queue = queue.Queue()
        result_container: list[ExecutionResult] = []
        had_text_events = [False]

        def _run():
            try:
                uil_history = list(history or [])

                # ── Inject working directory + project context ──
                from pathlib import Path as _P
                cwd = str(_P.cwd().resolve())
                uil_history.insert(0, {"role": "system", "content": f"<working_directory>\n  You are working in: {cwd}\n  ALL files you create MUST go in this directory.\n  Use relative paths. This is the project root.\n</working_directory>", "_cwd_context": True})
                if self._project_context:
                    uil_history.insert(0, {"role": "system", "content": f"<project_context>\n{self._project_context}\nUse this context to understand the project goals, architecture, current tasks, and roadmap.\n</project_context>", "_project_context": True})

                def _on_event(event):
                    if event["type"] == "text":
                        had_text_events[0] = True
                    event_queue.put(event)

                result, _routing = self._uil.process(
                    user_input=message,
                    messages=uil_history,
                    cfg=self._cfg,
                    on_event=_on_event,
                )
                result_container.append(result)
                event_queue.put(None)  # sentinel
            except Exception as e:
                logger.error("chat_stream error: %s", e, exc_info=True)
                from core.utils import sanitize_error
                event_queue.put({"type": "error", "data": sanitize_error(str(e))})
                event_queue.put(None)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        while True:
            event = event_queue.get()
            if event is None:
                break
            yield event

        # Yield tool events from the result (tools are only available after processing)
        if result_container:
            result = result_container[0]
            tools_used = getattr(result, "tools_used", []) or []
            for tc in tools_used:
                name = tc.get("name", str(tc)) if isinstance(tc, dict) else str(tc)
                args = tc if isinstance(tc, dict) else {}
                yield {"type": "tool", "data": {"name": name, "args": args}}

            # Yield final cleaned text if no streaming text was emitted
            if not had_text_events[0]:
                content = getattr(result, "summary", "") or ""
                clean = self._clean_content(content)
                if clean:
                    self._save_message("assistant", clean)
                    yield {"type": "text", "data": clean}
        yield {"type": "done", "data": None}

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

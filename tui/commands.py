"""TUI Commands — slash command handling for the TUI.

Each command is a method on CommandHandler.  The handler is attached
to the app and calls back into it for UI operations.
"""

from pathlib import Path
from core import tools
from core.memory import MemoryStore
from core.providers.providers import fetch_free_models, fetch_ollama_models, create_provider
from core.project import state as project_state
from core.project.git import auto_commit
from core.skills import skill_manager
from core.utils import get_last_turn
from core.memory_learner import MemoryLearner
from core.diagnostics import audit_silent_errors


class CommandHandler:
    """Processes slash (/), exclamation (!), and normal input."""

    def __init__(self, app_ref):
        self.app = app_ref

    async def handle(self, text: str, state):
        text = self._auto_correct(text)
        text = self._process_mentions(text, state)
        self._track_patterns(text, state)

        if text.startswith("/"):
            await self._cmd(text, state)
        elif text.startswith("!"):
            self._do_skill(text[1:], state)
        else:
            return False  # not a command — let chat engine handle it
        return True

    # ── Slash commands ──────────────────────────────────────
    async def _cmd(self, text: str, state):
        parts = text.split(None, 1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            self.app.app.exit()
        elif cmd == "/help":
            await self.app._do_action("help")
        elif cmd == "/tools":
            await self.app._do_action("tools")
        elif cmd == "/skills":
            await self.app._do_action("skills")
        elif cmd == "/history":
            await self.app._do_action("history")
        elif cmd == "/memories":
            await self.app._do_action("memories")
        elif cmd == "/settings":
            await self.app._do_action("settings")
        elif cmd == "/sessions":
            await self.app._do_action("sessions")
        elif cmd == "/export":
            await self.app._do_action("export")
        elif cmd == "/save":
            state.save_session()
            self.app._log_message("system", "💾 Session saved")
        elif cmd == "/clear":
            if len(parts) > 1:
                # /clear session → wipe session data
                state.clear_session()
                self.app._log_message("system", "🧹 Session cleared")
            else:
                # /clear → clear chat log only
                self.app._chat_log.clear()
                self.app._show_chat()

        # ── Model ─────────────────────────────────────────
        elif cmd == "/model":
            from core.providers.providers import get_available_models
            available = get_available_models(state.provider.name, state.provider.base_url, True)
            if available:
                self.app._log_message("system", f"Models: {', '.join(available[:10])}")
            else:
                self.app._log_message("system", "No models available for current provider")

        # ── Remember / Memories ───────────────────────────
        elif cmd == "/remember" and len(parts) > 1:
            fact = parts[1]
            mem = MemoryStore()
            mem.save(f"note-{len(fact[:20])}", fact, {"type": "feedback"})
            self.app._log_message("system", f"✓ Remembered: {fact[:80]}")
            # Feed to MemoryLearner for pattern extraction
            try:
                learner = MemoryLearner(provider=state.provider)
                learner.learn(fact)
            except Exception:
                pass
            self.app._show_chat()

        # ── Debug ─────────────────────────────────────────
        elif cmd == "/debug":
            r = audit_silent_errors()
            self.app._log_message("system", f"🔍 Silent errors: {r['counts']}")

        # ── Doctor ────────────────────────────────────────
        elif cmd == "/doctor":
            await self.app._do_doctor()

        # ── Search messages ───────────────────────────────
        elif cmd == "/search" and len(parts) > 1:
            query = parts[1].strip().lower()
            results = []
            for i, m in enumerate(state.messages):
                c = (m.get("content") or "").lower()
                if query in c:
                    results.append(f"[{i+1}] {m.get('role','?')}: {c[:100]}...")
            if results:
                self.app._log_message("system", f"🔍 {len(results)} match(es):")
                for r in results[:10]:
                    self.app._log_message("system", r)
            else:
                self.app._log_message("system", f"🔍 No matches for '{query}'")

        # ── Unknown ───────────────────────────────────────
        else:
            self.app._log_message("system", f"Unknown: {cmd}. Try /help")

    # ── Skills ──────────────────────────────────────────────
    def _do_skill(self, name: str, state):
        skill_name = name.strip().lower()
        if skill_name == "off":
            if skill_manager.active:
                old = skill_manager.active.name
                skill_manager.deactivate()
                self.app._log_message("system", f"Skill '{old}' deactivated")
            return

        ok = skill_manager.toggle(skill_name)
        if ok:
            active = skill_manager.active
            if active:
                icon = active.icon + " " if active.icon else ""
                self.app._log_message("system", f"{icon}Skill '{active.name}' activated")
                state.messages = [m for m in state.messages if not m.get("_skill_prompt")]
                state.messages.insert(0, {"role": "system", "content": active.prompt, "_skill_prompt": True})
                state._rebuild_tool_defs()
            else:
                state.messages = [m for m in state.messages if not m.get("_skill_prompt")]
                self.app._log_message("system", "Skill deactivated")
                state._rebuild_tool_defs()
        else:
            self.app._log_message("system", f"Unknown skill: '{skill_name}'")

    # ── Auto-correct ───────────────────────────────────────
    def _auto_correct(self, text: str) -> str:
        corrections = {
            "/clea": "/clear", "/clera": "/clear", "/hepl": "/help",
            "/hel": "/help", "/sav": "/save", "/doctro": "/doctor",
            "/searhc": "/search", "/serach": "/search",
        }
        for typo, correction in corrections.items():
            if text.startswith(typo):
                self.app._show_toast(f"✏️ Auto-corrected: {typo} → {correction}", "info", 2)
                return text.replace(typo, correction, 1)
        return text

    def _process_mentions(self, text: str, state) -> str:
        import re
        msgs = state.messages
        if not msgs:
            return text
        mentions = re.findall(r'@(\d+)', text)
        for mention in mentions:
            try:
                idx = int(mention) - 1
                if 0 <= idx < len(msgs):
                    m = msgs[idx]
                    text = text.replace(f"@{mention}", f"[Referring to #{mention}: {m.get('role','?')} - {(m.get('content') or '')[:200]}...]")
            except ValueError:
                pass
        return text

    def _track_patterns(self, text: str, state):
        if text.startswith("/"):
            cmd = text.split()[0]
            if not hasattr(state, '_patterns'):
                state._patterns = {}
            state._patterns[cmd] = state._patterns.get(cmd, 0) + 1

"""WIDDX TUI — clean modular architecture.

Core components:
  - ``TUIState`` (state.py)    — state management
  - ``ChatEngine`` (chat_engine.py) — streaming + tools + agents
  - ``CommandHandler`` (commands.py) — slash commands
"""

import sys, logging, json, time
from pathlib import Path
from datetime import datetime
from bidi.algorithm import get_display

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import RichLog, Input, Static, Button, Select
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual import work
from rich.text import Text

from core import config, tools
from core.ui_visual import role_panel, reasoning_panel
from core.mcp.client import get_mcp_manager
from core.skills import skill_manager
from core.memory import MemoryStore

from .state import TUIState
from .chat_engine import ChatEngine, ResultMsg, ErrorMsg, StreamEndMsg, ThinkingMsg, ToolStepMsg
from .commands import CommandHandler
from .widgets import HeaderWidget
from .screens.ubuntu_grid import UbuntuGrid

logger = logging.getLogger("widdx.tui")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.FileHandler(Path(ROOT) / "widdx-tui.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s %(message)s'))
    logger.addHandler(handler)

_THINK_TAGS = ("[thinking]", "[/thinking]")


def _fix_rtl(text: str) -> str:
    if not text:
        return ""
    if any("؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ" for c in text):
        return get_display(text)
    return text


# ── View Panel ──────────────────────────────────────────────
class ViewPanel(ScrollableContainer):
    """Side panel for tools, skills, history, memories."""
    def compose(self):
        yield Static(id="view-title")
        yield ScrollableContainer(id="view-list")
    def set_title(self, text: str):
        self.query_one("#view-title", Static).update(f"  [bold #f5a623]{text}[/]")


# ── Main Screen ──────────────────────────────────────────────
class MainScreen(Screen):
    """Main chat screen for WIDDX TUI."""

    _show_thinking: bool = False  # toggle for displaying reasoning content

    BINDINGS = [
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
        Binding("escape", "cancel_or_focus", "Cancel/Focus", show=False),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("ctrl+p", "show_help", "Help", show=False),
        Binding("ctrl+t", "toggle_thinking", "𖥔 Thinking", show=False, tooltip="Toggle reasoning content display"),
        Binding("ctrl+up", "history_prev", "Previous Cmd", show=False),
        Binding("ctrl+down", "history_next", "Next Cmd", show=False),
    ]

    NAV_BUTTONS = [
        ("nav-chat", "💬", "Chat"), ("nav-tools", "🛠️", "Tools"),
        ("nav-skills", "🎯", "Skills"), ("nav-history", "📋", "History"),
        ("nav-memories", "💾", "Memories"), ("nav-sessions", "📦", "Sessions"),
        ("nav-settings", "⚙", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        self.state = TUIState()
        self.chat = ChatEngine(self)
        self.cmds = CommandHandler(self)
        self._chat_log: RichLog = None
        self._stream_buffer = ""
        self._command_history: list[str] = []
        self._history_index = -1
        self._active_view: str | None = None  # tracks current view-panel mode

    def compose(self) -> ComposeResult:
        yield HeaderWidget()
        yield Static("", id="processing", classes="hidden")
        with Horizontal(id="body"):
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True, max_lines=500)
            yield ViewPanel(id="view-panel")
        with Horizontal(id="input-container"):
            yield Static("❯", id="prompt-label")
            yield Input(placeholder="Type a message… (/help)", id="input")
        yield Static(id="status")
        yield Static("", id="toast", classes="toast-hidden")

    def on_mount(self) -> None:
        self._chat_log = self.query_one("#chat-log", RichLog)
        self._show_chat()

        # Startup
        for log_line in self.state.startup():
            self._log_message("system", log_line)

        self.query_one("#input", Input).focus()
        self.query_one("#processing", Static).set_class(False, "active")
        # Refresh header
        hw = self.query_one(HeaderWidget)
        hw.initialize_provider(self.state.model.split("/")[0])

    # ── Input handling ─────────────────────────────────────
    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        if text and (not self._command_history or text != self._command_history[-1]):
            self._command_history.append(text)
            if len(self._command_history) > 100:
                self._command_history.pop(0)
        self._history_index = -1
        self.query_one("#input", Input).value = ""
        self.query_one("#input", Input).disabled = True

        is_cmd = await self.cmds.handle(text, self.state)
        if not is_cmd:
            self._log_message("user", text)
            self.query_one("#input", Input).disabled = True
            self.query_one("#processing", Static).set_class(True, "active")
            self.run_chat(text)
        else:
            # Slash command handled — re-enable input immediately
            self._finish_chat()

    @work(exclusive=True, thread=True)
    def run_chat(self, text: str) -> None:
        """Execute chat in a background thread — keeps UI responsive.

        Per Textual official docs:
        - exclusive=True prevents race conditions (double-enter)
        - thread=True runs in a separate thread
        - self.app.call_from_thread schedules UI updates safely on main thread
        """
        from textual.worker import get_current_worker
        worker = get_current_worker()
        try:
            self.chat.start(text, self.state)
            if not worker.is_cancelled:
                self.app.call_from_thread(self._finish_chat)
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._log_message, "system", f"❌ {e}")
            self.app.call_from_thread(self._finish_chat)

    def _finish_chat(self):
        self.query_one("#input", Input).disabled = False
        self.query_one("#input", Input).focus()
        self.query_one("#processing", Static).set_class(False, "active")

    def on_input_changed(self, event: Input.Changed):
        cc = self.query_one("#prompt-label", Static)
        cc.update(f"❯ {len(event.value)}" if event.value else "❯")

    # ── UI helpers ─────────────────────────────────────────
    def _log_message(self, role: str, content: str):
        if not self._chat_log:
            return
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        content = _fix_rtl(content)
        panel = role_panel(role, content, ts)
        self._chat_log.write(panel)

    def _log(self, text: str):
        if self._chat_log:
            self._chat_log.write(text)

    def _show_chat(self):
        vp = self.query_one("#view-panel", ViewPanel)
        cl = self.query_one("#chat-log", RichLog)
        cl.display = True
        vp.display = False

    def _show_view(self, title: str):
        vp = self.query_one("#view-panel", ViewPanel)
        cl = self.query_one("#chat-log", RichLog)
        cl.display = False
        vp.display = True
        vp.set_title(title)

    # ── Navigation actions ─────────────────────────────────
    async def _do_action(self, action: str):
        if action == "help":
            from .screens.help import HelpScreen
            self.app.push_screen(HelpScreen(), self._on_help_result)
        elif action == "tools":
            self._show_view("Tools")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            from textual.widgets import Button as TButton
            for i, td in enumerate(self.state.tool_defs):
                name = td["name"]
                desc = (td.get("description", "") or "")[:70]
                tag = " [MCP]" if name.startswith("mcp__") else ""
                tag += " [WORKFLOW]" if name in ("create_agent", "run_parallel") else ""
                await vlist.mount(TButton(f"  🛠️ {name}{tag}  —  {desc}", id=f"tool-{i}"))
        elif action == "skills":
            self._show_view("Skills")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            from textual.widgets import Button as TButton
            for s in skill_manager.list_all():
                active = skill_manager.active and s.name == skill_manager.active.name
                marker = "◉" if active else "○"
                icon = getattr(s, "icon", "") or "🎯"
                btn = TButton(f"  {marker}  {icon}  !{s.name}  —  {s.description[:50]}", id=f"sk-{s.name}")
                btn.set_class(True, "active") if active else None
                await vlist.mount(btn)
        elif action == "history":
            self._show_view("History")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            icons = {"user": "👤", "assistant": "🤖", "system": "⚙️", "tool": "🛠️"}
            from textual.widgets import Button as TButton
            for i, m in enumerate(self.state.messages[-50:]):
                role = m.get("role", "?")
                c = (m.get("content") or "")[:60].replace("\n", " ")
                icon = icons.get(role, "•")
                idx_val = i  # use relative index
                await vlist.mount(TButton(f"  {icon}  [{role}]  {c}", id=f"hist-{idx_val}"))
        elif action == "memories":
            await self._show_memories()
        elif action == "sessions":
            from .screens.session_crud import SessionListScreen
            self.app.push_screen(SessionListScreen(), self._on_session_result)
        elif action == "settings":
            from .screens.settings import SettingsScreen
            self.app.push_screen(SettingsScreen(), self._on_settings_result)
        elif action == "export":
            self._export_chat()
        elif action == "doctor":
            await self._do_doctor()

    async def _show_memories(self):
        from rich.table import Table
        mem = MemoryStore()
        all_m = mem.list_all()
        query = ""
        if not all_m:
            self._log_message("system", "No memories. Use /remember to save one.")
            return
        self._show_view("Memories")
        vlist = self.query_one("#view-list", ScrollableContainer)
        await vlist.remove_children()
        from textual.widgets import Button as TButton
        for m in all_m[:30]:
            await vlist.mount(TButton(f"  📌 {m['name']}: {m.get('description','')[:80]}", id=f"mem-{m['name']}"))

    def _export_chat(self):
        lines = []
        for m in self.state.messages:
            role = m.get("role", "?")
            content = (m.get("content") or "")[:500]
            lines.append(f"## {role.upper()}\n\n{content}\n")
        path = Path.cwd() / f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path.write_text("\n---\n".join(lines), encoding="utf-8")
        self._log_message("system", f"📤 Exported to {path.name}")

    async def _do_doctor(self):
        import subprocess
        self._log_message("system", "🩺 Running doctor checks...")
        git_v, node_v = "?", "?"
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            git_v = r.stdout.strip() if r.returncode == 0 else "not found"
        except Exception:
            git_v = "not found"
        try:
            r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            node_v = r.stdout.strip() if r.returncode == 0 else "not found"
        except Exception:
            node_v = "not found"
        self._log_message("system", f"🩺 Git: {git_v}  |  Node: {node_v}")
        self._log_message("system", f"🩺 Provider: {self.state.model}  |  Turns: {self.state.turns}")
        self._log_message("system", f"🩺 Memory: {MemoryStore().total()} facts  |  Tools: {len(self.state.tool_defs)}")

    # ── Message handlers (from ChatEngine) ─────────────────
    def on_result_msg(self, msg: ResultMsg):
        display = msg.text or "[execution complete]"
        self._log_message("assistant", display)
        self._show_chat()
        self.query_one("#processing", Static).set_class(False, "active")

    def on_error_msg(self, msg: ErrorMsg):
        self._log_message("system", f"❌ {msg.text}")
        self.query_one("#processing", Static).set_class(False, "active")

    def on_tool_step_msg(self, msg: ToolStepMsg):
        from rich.text import Text as RText
        from core.ui_visual import TOOL, DIM
        self._log(f"  🔧 [bold {TOOL}]{msg.tool}[/] → [{DIM}]{msg.detail[:120]}[/]")

    def on_stream_end_msg(self, msg: StreamEndMsg):
        display = msg.content or "[tool execution complete]"
        self._log_message("assistant", display)
        self.state.messages = msg.msgs
        self.state.save_session()
        self._show_chat()
        self.query_one("#processing", Static).set_class(False, "active")

    def on_thinking_msg(self, msg: ThinkingMsg):
        """Show reasoning content only when toggle is on, and format it cleanly."""
        if not self._show_thinking:
            return
        text = _fix_rtl(msg.text)
        panel = reasoning_panel(text, getattr(msg, "elapsed", None))
        if self._chat_log:
            self._chat_log.write(panel)

    # ── Navigation screens callbacks ───────────────────────
    def _on_help_result(self, cmd: str | None):
        if cmd:
            # Execute the selected quick-action command
            import asyncio
            asyncio.create_task(self.cmds.handle(cmd, self.state))
        self.query_one("#input", Input).focus()

    def _on_settings_result(self, result: dict | None):
        if result:
            # Reload config and recreate provider from saved settings
            from core.config.settings import load as reload_config
            from core.providers.providers import create_provider
            new_cfg = reload_config()
            self.state.cfg = new_cfg
            self.state.provider = create_provider(new_cfg)
            self.state.model = f"{self.state.provider.name}/{self.state.provider.model}"
            self.state._rebuild_tool_defs()
            # Refresh header with new provider name
            try:
                hw = self.query_one(HeaderWidget)
                hw.initialize_provider(self.state.provider.name)
            except Exception:
                pass
        self.query_one("#input", Input).focus()

    def _on_session_result(self, result: tuple | None):
        if result:
            action = result[0]
            if action == "loaded" and len(result) > 1:
                msgs = result[1]
                self.state.messages = msgs
                self.state.turns = len(msgs)
                self._log_message("system", f"📂 Session loaded: {len(msgs)} messages")
                if self._chat_log:
                    self._chat_log.clear()
                    self._show_chat()
                    for m in msgs[-20:]:
                        role = m.get("role", "?")
                        content = m.get("content", "")[:300]
                        if role in ("user", "assistant", "system"):
                            self._log_message(role, content)
            elif action == "new" and len(result) > 1:
                self.state.messages = []
                self.state.turns = 0
                self._log_message("system", "✨ New session started")
        self.query_one("#input", Input).focus()

    def action_cancel_or_focus(self):
        self.query_one("#input", Input).focus()

    def action_show_help(self):
        from .screens.help import HelpScreen
        self.app.push_screen(HelpScreen(), self._on_help_result)

    def action_clear_chat(self):
        if self._chat_log:
            self._chat_log.clear()
        self._show_chat()

    def action_toggle_thinking(self):
        """Toggle display of reasoning/thinking content."""
        self._show_thinking = not self._show_thinking
        status = "🟢 on" if self._show_thinking else "🔴 off"
        self._log_message("system", f"🧠 Thinking display: {status}")
        self._show_toast(f"Thinking: {status}")

    def action_history_prev(self):
        if self._command_history:
            # Move further back: -1→0→1→2... (0 = most recent)
            max_idx = len(self._command_history) - 1
            self._history_index = min(max_idx, self._history_index + 1)
            idx = self._history_index
            inp = self.query_one("#input", Input)
            if 0 <= idx < len(self._command_history):
                inp.value = self._command_history[-(idx + 1)]

    def action_history_next(self):
        if self._command_history and self._history_index >= 0:
            # Move forward: 2→1→0→-1 (back to current input)
            self._history_index -= 1
            inp = self.query_one("#input", Input)
            idx = self._history_index
            if idx >= 0:
                inp.value = self._command_history[-(idx + 1)]
            else:
                inp.value = ""

    # ── Toast notifications ────────────────────────────────
    def _show_toast(self, msg: str, kind: str = "info", duration: float = 3.0):
        toast = self.query_one("#toast", Static)
        toast.update(f"  {msg}  ")
        toast.set_class(False, "toast-hidden")
        self.set_timer(duration, self._hide_toast)

    def _hide_toast(self):
        self.query_one("#toast", Static).set_class(True, "toast-hidden")

    # ── Header & View Panel event handlers ──────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses from header, nav, and view panel."""
        bid = event.button.id or ""
        if bid == "btn-grid":
            # Open Ubuntu Grid launcher
            main_nav = self.NAV_BUTTONS
            act_btns = [
                ("act-doctor", "🩺", "Doctor", "doctor", "info"),
                ("act-export", "📤", "Export", "export", "success"),
                ("act-clear", "🧹", "Clear", "clear", "warn"),
                ("act-search", "🔍", "Search", "search", "info"),
            ]
            help_btns = [
                ("help-help", "❓", "Help", "help", "info"),
                ("help-about", "ℹ️", "About", "about", "info"),
            ]
            self.app.push_screen(
                UbuntuGrid(nav_buttons=main_nav, act_buttons=act_btns, help_buttons=help_btns),
                self._on_grid_result
            )
            return

        # View panel button handlers
        if bid and bid.startswith("tool-"):
            idx = int(bid.split("-")[1])
            td = self.state.tool_defs[idx] if idx < len(self.state.tool_defs) else None
            if td:
                from .screens.tool_detail import ToolDetailScreen
                self.app.push_screen(ToolDetailScreen(td))
            return

        if bid and bid.startswith("sk-"):
            skill_name = bid[3:]
            self.cmds._do_skill(skill_name, self.state)
            return

        if bid and bid.startswith("hist-"):
            idx = int(bid.split("-")[1])
            # idx is relative to the last 50 shown
            shown = self.state.messages[-50:]
            if 0 <= idx < len(shown):
                m = shown[idx]
                from .screens.detail import TextDetailScreen
                title = f"Message [{m.get('role', '?')}]"
                body = m.get("content", "")
                self.app.push_screen(TextDetailScreen(title, body))
            return

        if bid and bid.startswith("mem-"):
            mem_name = bid[4:]
            mem = MemoryStore()
            content = mem.get(mem_name)
            if content:
                from .screens.detail import TextDetailScreen
                self.app.push_screen(TextDetailScreen(mem_name, content))
            return

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider and branch selector changes from header."""
        sid = event.select.id or ""
        if sid == "header-provider" and event.value and event.value != Select.BLANK:
            from core.providers.providers import create_provider
            from core.config.settings import load as reload_config
            new_name = str(event.value)
            cfg = reload_config()
            all_prov = cfg.get("all_providers", {})
            ap = all_prov.get(new_name, {})
            cfg["provider"] = {
                "name": new_name,
                "model": ap.get("model", ""),
                "base_url": ap.get("base_url", ""),
                "api_key": ap.get("api_key", "public"),
            }
            from core.config.settings import save as save_config
            save_config(cfg)
            self.state.cfg = cfg
            self.state.provider = create_provider(cfg)
            self.state.model = f"{self.state.provider.name}/{self.state.provider.model}"
            self.state._rebuild_tool_defs()
            self._log_message("system", f"🔄 Switched to {self.state.provider.name}/{self.state.provider.model}")
        elif sid == "header-branch" and event.value and event.value != Select.BLANK:
            new_branch = str(event.value)
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "checkout", new_branch],
                    capture_output=True, text=True, timeout=30, cwd=Path.cwd()
                )
                if result.returncode == 0:
                    self._log_message("system", f"🌿 Switched to branch: {new_branch}")
                    self.state.save_session()
                    # Refresh branch list in header
                    try:
                        hw = self.query_one(HeaderWidget)
                        hw._populate_header_selectors()
                    except Exception:
                        pass
                else:
                    self._log_message("system", f"❌ Branch switch failed: {result.stderr.strip()}")
            except Exception as e:
                self._log_message("system", f"❌ Branch switch failed: {e}")

    def _on_grid_result(self, action: str | None) -> None:
        """Handle result from UbuntuGrid launcher."""
        if action:
            import asyncio
            asyncio.create_task(self._do_action(action))
        self.query_one("#input", Input).focus()


# ── App Entry ────────────────────────────────────────────────
class WIDDXTUI(App):
    TITLE = "WIDDX Cortex"
    CSS_PATH = "app.tcss"
    SCREENS = {}

    def __init__(self):
        super().__init__()
        self.main_screen = None

    def on_mount(self):
        self.main_screen = MainScreen()
        self.push_screen(self.main_screen)


def run_tui():
    app = WIDDXTUI()
    app.run()


if __name__ == "__main__":
    run_tui()

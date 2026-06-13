"""WIDDX TUI — Enhanced Terminal Interface with Rich Diagnostics & Styling."""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path
ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import RichLog, Input, Static, Button, Label, Select
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.message import Message
from textual import work

from core import config, tools
from core.providers.providers import create_provider, estimate_turn_cost, fetch_ollama_models
from core.proxy import proxy_manager
from core.skills import skill_manager
from core.mcp.client import get_mcp_manager
from core.memory import MemoryStore
from core.project import state as project_state
from core.chat import _valid_tool_call_id, _build_tc_list, _sanitize_tool_call_ids


def _find_sessions_count() -> list:
    """Quick count of saved session files (no heavy imports)."""
    from pathlib import Path
    cwd = Path.cwd().resolve()
    sessions = []
    for pattern in ["chat_*.json", "chat_export_*.md"]:
        sessions.extend(cwd.glob(pattern))
    ws = cwd / ".widdx" / "session.json"
    if ws.exists():
        sessions.append(ws)
    return sessions

logger = logging.getLogger("widdx.tui")

_THINK_START = "[thinking]"
_THINK_END = "[/thinking]"


class ResultMsg(Message):
    def __init__(self, text: str, msgs: list | None = None) -> None:
        self.text = text
        self.msgs = msgs or []
        super().__init__()


class ErrorMsg(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class ToolStepMsg(Message):
    def __init__(self, tool: str, status: str, detail: str) -> None:
        self.tool = tool
        self.status = status
        self.detail = detail
        super().__init__()


class StreamChunkMsg(Message):
    """Live streaming chunk from AI response."""
    def __init__(self, chunk: str) -> None:
        self.chunk = chunk
        super().__init__()


class StreamEndMsg(Message):
    """Streaming complete — finalize and display."""
    def __init__(self, content: str, msgs: list) -> None:
        self.content = content
        self.msgs = msgs
        super().__init__()


# ── View panel (Tools, Skills, etc.) ──

class ViewPanel(ScrollableContainer):
    """Panel showing interactive content (tools, skills, history, memories)."""
    def compose(self):
        yield Static(id="view-title")
        yield ScrollableContainer(id="view-list")
        
    def set_title(self, text: str):
        self.query_one("#view-title", Static).update(f"  [bold #f5a623]{text}[/]")


# ── Main Screen ────────────────────────

class MainScreen(Screen):
    """Main chat and navigation screen."""

    BINDINGS = [
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
        Binding("escape", "cancel_or_focus", "Cancel/Focus", show=False),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("ctrl+p", "show_help", "Help", show=False),
    ]

    NAV_BUTTONS = [
        ("nav-chat",     "💬", "Chat",      "Chat",       ""),
        ("nav-tools",    "🛠️", "Tools",     "Tools",      ""),
        ("nav-skills",   "🎯", "Skills",    "Skills",     ""),
        ("nav-history",  "📋", "History",   "History",    ""),
        ("nav-memories", "💾", "Memories",  "Memories",   "C/R/U/D"),
        ("nav-sessions", "📦", "Sessions",  "Sessions",   "C/R/U/D"),
        ("nav-settings", "⚙",  "Settings",  "Settings",   ""),
    ]

    ACT_BUTTONS = [
        ("nav-doctor",   "🩺", "Doctor",    "Doctor",     ""),
        ("nav-save",     "💿", "Save",      "Save",       ""),
        ("nav-export",   "📤", "Export",    "Export",     ""),
        ("nav-clear",    "🧹", "Clear",     "Clear",      "Ctrl+L"),
    ]

    HELP_BUTTONS = [
        ("nav-help",     "❓", "Help",      "Help",       "Ctrl+P"),
    ]

    def __init__(self, state: dict, provider=None, tool_defs=None):
        super().__init__()
        self._state = state
        self._provider = provider
        self._tool_defs = tool_defs or []
        self._chat_log = None
        self._processing = False
        self._cancel_requested = False
        self._current_tools = []

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield Static("[bold #0b0f19]⚡  Thinking and executing tools  —  please wait...[/]", id="processing")
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                # Brand header
                yield Static("[bold #6366f1]◈  W I D D X  C O R T E X[/]\n[dim #475569]by Muhammad Muslih  •  widdx[/]", id="sidebar-brand")
                yield Static(classes="sidebar-divider")
                # Quick provider switcher
                yield Select(options=[], id="quick-provider", classes="provider-switch")
                yield Static(classes="sidebar-divider")
                yield Static("NAVIGATE", classes="sidebar-group")
                for bid, icon, label, _, _ in self.NAV_BUTTONS:
                    yield Button(f"{icon}  {label}", id=bid, classes="sidebar-btn")
                yield Static(classes="sidebar-divider")
                yield Static("ACTIONS", classes="sidebar-group")
                for bid, icon, label, _, shortcut in self.ACT_BUTTONS:
                    text = f"{icon}  {label}" + (f"  [dim]{shortcut}[/]" if shortcut else "")
                    yield Button(text, id=bid, classes="sidebar-btn")
                yield Static(classes="sidebar-divider")
                yield Static("HELP", classes="sidebar-group")
                for bid, icon, label, _, shortcut in self.HELP_BUTTONS:
                    text = f"{icon}  {label}" + (f"  [dim]{shortcut}[/]" if shortcut else "")
                    yield Button(text, id=bid, classes="sidebar-btn")
                # Sidebar footer with model info
                yield Static(id="sidebar-footer")
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True, max_lines=5000)
            yield Static(id="stream-output")
            yield ViewPanel(id="view-panel")
        with Horizontal(id="input-container"):
            yield Label("❯", id="prompt-label")
            yield Input(placeholder="Type a message…  (/help for commands)", id="input")
            yield Static("", id="char-count")
        yield Static(id="status")
        # Toast notification overlay (hidden by default)
        yield Static("", id="toast", classes="toast-hidden")

    def on_mount(self) -> None:
        self._chat_log = self.query_one("#chat-log", RichLog)
        self._show_chat()
        self._print_history()
        self._update_header()
        self._update_status()
        self._refresh_sidebar_badges()
        self._init_quick_provider()
        self.query_one("#input", Input).focus()

    def _init_quick_provider(self):
        """Populate the quick provider switcher in the sidebar."""
        prov_select = self.query_one("#quick-provider", Select)
        pname = self._state.get("_provider_name", "") or self._state.get("model", "").split("/")[0]
        providers = [
            ("🌐 OpenCode Zen", "opencode-zen"),
            ("🔵 DeepSeek", "deepseek"),
            ("⚪ OpenAI", "openai"),
            ("🟠 Ollama", "ollama"),
        ]
        prov_select.set_options(providers)
        if pname in dict(providers):
            prov_select.value = pname

    # ── UI logging helpers ──────────────────────

    def _log(self, text: str) -> None:
        if self._chat_log:
            self._chat_log.write(text)

    def _log_message(self, role: str, content: str) -> None:
        if not self._chat_log:
            return
        from rich.panel import Panel
        from rich.text import Text
        from rich.markdown import Markdown
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")

        if role == "user":
            title = f" 👤 You  [dim]{ts}[/dim] "
            border_style = "#6366f1"
            msg_text = Text(content, style="default")
            panel = Panel(msg_text, title=title, title_align="left", border_style=border_style, padding=(0, 2))
        elif role == "assistant":
            title = f" 🤖 Assistant  [dim]{ts}[/dim] "
            border_style = "#10b981"
            md = Markdown(content)
            panel = Panel(md, title=title, title_align="left", border_style=border_style, padding=(0, 2))
        elif role == "system":
            title = f" ⚙  [dim]{ts}[/dim] "
            border_style = "#f5a623"
            panel = Panel(content, title=title, title_align="left", border_style=border_style, padding=(0, 1))
        elif role == "tool":
            title = f" 🛠  [dim]{ts}[/dim] "
            border_style = "#0ea5e9"
            preview = content[:600] + "\n[dim]…[/dim]" if len(content) > 600 else content
            panel = Panel(preview, title=title, title_align="left", border_style=border_style, padding=(0, 1))
        else:
            panel = Panel(content, border_style="dim", padding=(0, 1))

        self._chat_log.write(panel)

    def _log_welcome_message(self) -> None:
        if not self._chat_log:
            return
        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text
        from rich.rule import Rule

        model_short = self._state.get("model", "?").split("/")[-1][:24]
        pname = self._state.get("_provider_name", "") or self._state.get("model", "").split("/")[0]
        skill_count = len(skill_manager.list_all())

        # Connection status check
        is_opencode = pname in ("opencode-zen", "opencode")
        if is_opencode:
            connected = not proxy_manager.current_proxy()
            conn_status = "Direct" if connected else proxy_manager.status()[:16]
            conn_color = "#10b981" if connected else "#f5a623"
        else:
            conn_status = "Direct API"
            conn_color = "#10b981"

        welcome_text = Text.assemble(
            ("\n◈  WIDDX Cortex  v3.0\n", "bold #6366f1"),
            ("  by Muhammad Muslih  •  widdx\n", "dim #475569"),
            ("─" * 44 + "\n\n", "dim #374151"),
            ("  Provider:  ", "dim"), (pname or "?", "bold #00c896"),
            ("   Model:  ", "dim"), (model_short, "bold #818cf8"),
            ("   Status:  ", "dim"), (conn_status, f"bold {conn_color}\n"),
            ("  Skills:    ", "dim"), (str(skill_count), "bold #f5a623"), (" available\n\n", "dim"),
            ("  ", ""), ("Ctrl+P", "bold #0891b2 on #0c1a2e"), ("  Help    ", "dim"),
            ("Ctrl+L", "bold #0891b2 on #0c1a2e"), ("  Clear    ", "dim"),
            ("Ctrl+Q", "bold #0891b2 on #0c1a2e"), ("  Quit\n\n", "dim"),
            ("  ", ""), ("!", "bold #f5a623"), ("skill_name", "#f5a623"), ("  activate skill  │  ", "dim"),
            ("!off", "bold #f5a623"), ("  deactivate  │  ", "dim"),
            ("/help", "bold #0891b2"), ("  all commands\n", "dim"),
            ("\n  Send a message to begin →\n", "dim #6b7280"),
        )

        panel = Panel(
            Align.center(welcome_text, vertical="middle"),
            border_style="#6366f1",
            padding=(1, 4),
            title="[bold #6366f1]  W I D D X  [/]",
            title_align="center",
            subtitle=f"[dim]● Ready  │  [/][bold {conn_color}]{conn_status}[/]",
            subtitle_align="right",
        )
        self._chat_log.write(panel)

    def _print_history(self) -> None:
        if not self._chat_log:
            return
        self._chat_log.clear()
        msgs = self._state.get("_messages", [])

        if not msgs:
            self._log_welcome_message()
            return

        # Filter to visible roles only, then display
        for m in msgs:
            role = m.get("role")
            content = m.get("content")
            if not content:
                continue
            if role == "system" and ("[PROJECT CONTEXT]" in content or "[INSTRUCTIONS]" in content):
                self._chat_log.write("[dim]⚙️  Project context loaded[/]")
            else:
                self._log_message(role, content)

    # ── UI helpers ──────────────────────

    # ── Provider badge colours ──────────────────────────────────
    _PROVIDER_BADGES = {
        "opencode-zen": ("🌐", "#10b981", "OpenCode Zen"),
        "opencode":     ("🌐", "#10b981", "OpenCode"),
        "deepseek":     ("🔵", "#0891b2", "DeepSeek"),
        "openai":       ("⚪", "#94a3b8", "OpenAI"),
        "ollama":       ("🟠", "#f5a623", "Ollama"),
    }

    def _update_header(self) -> None:
        m = self._state.get("model", "?")
        c = self._state.get("cost", 0.0)
        t = self._state.get("turns", 0)
        pname = self._state.get("_provider_name", "") or m.split("/")[0]
        model_short = m.split("/")[-1] if "/" in m else m

        # Provider badge
        icon, color, label = self._PROVIDER_BADGES.get(pname, ("◉", "#6366f1", pname or "?"))
        prov_badge = f"[{color}]{icon} {label}[/]"

        # Cost colour
        cost_color = "#ef4444" if c > 0.10 else "#10b981"

        # Proxy part (only for opencode)
        is_opencode = pname in ("opencode-zen", "opencode")
        proxy_part = ""
        if is_opencode:
            proxy = proxy_manager.status()[:16]
            px_icon = "🔒" if proxy_manager.current_proxy() else "🌐"
            proxy_part = f"  [dim]│[/]  {px_icon} [dim]{proxy}[/]"

        # Skill badge
        sk = f"  [dim]│[/]  [bold #f5a623]⚡ !{skill_manager.active.name}[/]" if skill_manager.active else ""

        self.query_one("#header", Static).update(
            f"  [bold #6366f1]◈[/]  {prov_badge}  [dim]│[/]  "
            f"[dim]{model_short}[/]  [dim]│[/]  "
            f"[{cost_color}]${c:.4f}[/]  [dim]│[/]  [dim]{t} turns[/]"
            f"{proxy_part}{sk}"
        )
        self._update_sidebar_footer(model_short)

    def _update_status(self) -> None:
        self.query_one("#status", Static).update(
            "  [dim #10b981]◈ Ready[/]   "
            "[bold #0891b2]Ctrl+P[/] [dim]Help[/]   "
            "[bold #0891b2]Ctrl+L[/] [dim]Clear[/]   "
            "[bold #f5a623]/agent[/] [dim]Auto[/]   "
            "[bold #0891b2]Ctrl+Q[/] [dim]Quit[/]"
        )

    def _update_sidebar_footer(self, model: str) -> None:
        """Update the sidebar footer with model and connection info."""
        model_short = model.split("/")[-1][:18] if "/" in model else model[:18]
        is_opencode = self._state.get("_provider_name", "") in ("opencode-zen", "opencode")
        if is_opencode:
            proxy_status = proxy_manager.status()[:14]
            connected = not proxy_manager.current_proxy()
            conn_icon  = "[#10b981]🟢[/]" if connected else "[#f5a623]🔒[/]"
            conn_label = "[dim]Direct[/]" if connected else f"[dim]{proxy_status}[/]"
        else:
            conn_icon = "[#10b981]🟢[/]"
            conn_label = "[dim]Direct API[/]"
        try:
            self.query_one("#sidebar-footer", Static).update(
                f"{conn_icon} [dim]{model_short}[/]\n{conn_label}"
            )
        except Exception as e:
            logger.debug("UI update skipped: %s", e)

    # ── Character counter ───────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update character count display as user types."""
        if (event.input.id or "") != "input":
            return
        try:
            n = len(event.value)
            counter = self.query_one("#char-count", Static)
            if n == 0:
                counter.update("")
            elif n > 2000:
                counter.update(f"[bold #ef4444]{n}[/]")
            elif n > 500:
                counter.update(f"[#f5a623]{n}[/]")
            else:
                counter.update(f"[dim]{n}[/]")
        except Exception:
            pass

    # ── Toast notification system ───────────────

    _toast_timer = None

    def _show_toast(self, msg: str, kind: str = "info", duration: float = 3.0) -> None:
        """Show a short-lived toast notification at the bottom of the screen."""
        try:
            toast = self.query_one("#toast", Static)
            colors = {"info": "#0891b2", "success": "#10b981", "warn": "#f5a623", "error": "#ef4444"}
            icons  = {"info": "ℹ", "success": "✓", "warn": "⚠", "error": "✕"}
            c = colors.get(kind, "#0891b2")
            i = icons.get(kind, "ℹ")
            toast.update(f"  [{c}]{i}[/]  {msg}  ")
            toast.set_class(False, "toast-hidden")
            toast.set_class(True, "toast-visible")
            # Cancel previous timer
            if self._toast_timer:
                try:
                    self._toast_timer.cancel()
                except Exception:
                    pass
            self._toast_timer = self.set_timer(duration, self._hide_toast)
        except Exception as e:
            logger.debug("Toast skipped: %s", e)

    def _hide_toast(self) -> None:
        try:
            toast = self.query_one("#toast", Static)
            toast.set_class(False, "toast-visible")
            toast.set_class(True, "toast-hidden")
        except Exception:
            pass

    # ── Sidebar badges ──────────────────────────

    def _refresh_sidebar_badges(self) -> None:
        """Update memory and session count badges in the sidebar."""
        import threading

        def _count():
            try:
                mem_count = MemoryStore().total()
            except Exception:
                mem_count = 0
            try:
                sess_count = len(_find_sessions_count())
            except Exception:
                sess_count = 0

            def _apply():
                try:
                    for bid, icon, label, _, _ in self.NAV_BUTTONS:
                        if bid == "nav-memories":
                            badge = f" [dim #10b981]{mem_count}[/]" if mem_count > 0 else ""
                            self.query_one(f"#{bid}", Button).label = f"{icon}  {label}{badge}"
                        elif bid == "nav-sessions":
                            badge = f" [dim #0891b2]{sess_count}[/]" if sess_count > 0 else ""
                            self.query_one(f"#{bid}", Button).label = f"{icon}  {label}{badge}"
                except Exception:
                    pass

            self.call_from_thread(_apply)

        threading.Thread(target=_count, daemon=True).start()


    def _show_chat(self) -> None:
        self.query_one("#chat-log", RichLog).display = True
        panel = self.query_one("#view-panel", ViewPanel)
        panel.display = False
        panel.set_class(False, "active")
        # Update nav active state
        for bid, *_ in self.NAV_BUTTONS + self.ACT_BUTTONS:
            self.query_one(f"#{bid}").set_class(False, "active")
        self.query_one("#nav-chat").set_class(True, "active")

    def _show_view(self, title: str) -> None:
        self.query_one("#chat-log", RichLog).display = False
        panel = self.query_one("#view-panel", ViewPanel)
        panel.display = True
        panel.set_class(True, "active")
        panel.set_title(title)
        # Update nav active state
        for bid, *_ in self.NAV_BUTTONS:
            self.query_one(f"#{bid}").set_class(bid == f"nav-{title.lower()}", "active")

    async def action_clear_chat(self) -> None:
        await self._do_action("clear")

    async def action_show_help(self) -> None:
        await self._do_action("help")

    # ── Button & Interactive clicks ─────

    NAV_MAP = {
        "nav-chat":     "chat",
        "nav-tools":    "tools",
        "nav-skills":   "skills",
        "nav-history":  "history",
        "nav-memories": "memories",
        "nav-sessions": "sessions",
        "nav-settings": "settings",
        "nav-doctor":   "doctor",
        "nav-save":     "save",
        "nav-export":   "export",
        "nav-clear":    "clear",
        "nav-help":     "help",
    }

    # Dispatch table for button ID prefixes → handler
    _BTN_DISPATCH = {
        "sk-":   "_on_sk_btn",
        "tool-": "_on_item_btn",
        "hist-": "_on_hist_btn",
    }

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid:
            return
        # Navigation buttons (chat, tools, skills, ...)
        action = self.NAV_MAP.get(bid)
        if action:
            await self._do_action(action)
            return
        # Prefixed buttons — dispatch by prefix
        for prefix, handler_name in self._BTN_DISPATCH.items():
            if bid.startswith(prefix):
                handler = getattr(self, handler_name, None)
                if handler:
                    await handler(bid)
                return

    async def _on_sk_btn(self, bid: str) -> None:
        self._do_skill(bid[3:])
        await self._do_action("skills")

    async def _on_item_btn(self, bid: str) -> None:
        """Handle tool-* and other index-based item buttons."""
        prefix = bid.split("-")[0] + "-"
        idx = int(bid[len(prefix):]) if bid[len(prefix):].isdigit() else -1
        if idx < 0:
            return
        if bid.startswith("tool-"):
            try:
                td = self._current_tools[idx]
                from .screens.tool_detail import ToolDetailScreen
                self.app.push_screen(ToolDetailScreen(td))
            except (IndexError, KeyError) as e:
                logger.debug("Invalid tool index %s: %s", idx, e)

    async def _on_hist_btn(self, bid: str) -> None:
        try:
            idx = int(bid[5:])
            msgs = self._state.get("_messages", [])[-30:]
            m = msgs[idx]
            from .screens.detail import TextDetailScreen
            self.app.push_screen(TextDetailScreen(
                f"Message Detail — {m.get('role', '?')}", m.get("content", ""),
            ))
        except (IndexError, KeyError, ValueError) as e:
            logger.debug("Invalid history index: %s", e)


    async def _do_action(self, action: str) -> None:
        if action == "chat":
            self._show_chat()
        elif action == "help":
            from .screens.help import HelpScreen
            self.app.push_screen(HelpScreen(), self._on_help_result)
        elif action == "tools":
            self._show_view("Tools")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            tl = list(tools.TOOL_DEFINITIONS)
            try:
                tl.extend(get_mcp_manager().get_all_tool_definitions())
            except Exception:
                pass
            self._current_tools = tl
            for i, td in enumerate(tl):
                name = td["name"]
                desc = (td.get("description", "") or "")[:75]
                mcp_tag = "  [MCP]" if name.startswith("mcp__") else ""
                vlist.mount(Button(f"  🛠️  {name}{mcp_tag}  —  {desc}", id=f"tool-{i}"))
        elif action == "skills":
            self._show_view("Skills")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            for s in skill_manager.list_all():
                active = skill_manager.active and s.name == skill_manager.active.name
                marker = "◉" if active else "○"
                icon = getattr(s, "icon", "") or "🎯"
                btn = Button(f"  {marker}  {icon}  !{s.name}  —  {s.description[:50]}", id=f"sk-{s.name}")
                if active:
                    btn.set_class(True, "active")
                vlist.mount(btn)
        elif action == "history":
            self._show_view("History")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            role_icons = {"user": "👤", "assistant": "🤖", "system": "⚙️", "tool": "🛠️"}
            for i, m in enumerate(self._state.get("_messages", [])[-30:]):
                role = m.get("role", "?")
                c = (m.get("content", "") or "")
                preview = (c[:60] if isinstance(c, str) else str(c)[:60]).replace("\n", " ")
                icon = role_icons.get(role, "•")
                vlist.mount(Button(f"  {icon}  [{role}]  {preview}", id=f"hist-{i}"))
        elif action == "memories":
            from .screens.memory_crud import MemoryListScreen
            self.app.push_screen(MemoryListScreen(state=self._state), callback=lambda _: self._refresh_sidebar_badges())
        elif action == "sessions":
            from .screens.session_crud import SessionListScreen
            msgs = list(self._state.get("_messages", []))
            self.app.push_screen(
                SessionListScreen(state=self._state, messages=msgs),
                self._on_session_result,
            )
        elif action == "settings":
            from .screens.settings import SettingsScreen
            self.app.push_screen(SettingsScreen(), self._on_settings_result)
        elif action == "doctor":
            self._show_view("Doctor")
            vlist = self.query_one("#view-list", ScrollableContainer)
            await vlist.remove_children()
            vlist.mount(Static("  🩺 Running diagnostics checks in background...", id="doctor-running"))
            self._run_doctor_checks()
        elif action == "save":
            msgs = self._state.get("_messages", [])
            if msgs:
                p = Path(ROOT) / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    p.write_text(json.dumps({"messages": msgs}, indent=2))
                    self._show_toast(f"Session saved → {p.name}  ({p.stat().st_size // 1024 or 1}KB)", kind="success")
                    self._refresh_sidebar_badges()
                except (OSError, PermissionError) as e:
                    self._show_toast(f"Save failed: {e}", kind="error")
            else:
                self._show_toast("Nothing to save yet", kind="warn")
            self._show_chat()
        elif action == "export":
            msgs = self._state.get("_messages", [])
            if msgs:
                p = Path(ROOT) / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                try:
                    lines = ["# WIDDX\n"]
                    for m in msgs:
                        role = m.get("role", "?")
                        content = m.get("content") or ""
                        lines.append(f"## {role}\n\n{content}\n\n---\n")
                    p.write_text("\n".join(lines))
                    self._show_toast(f"Exported session to {p.name}", kind="success")
                except (OSError, PermissionError) as e:
                    self._show_toast(f"Export failed: {e}", kind="error")
            self._show_chat()
        elif action == "clear":
            if self._chat_log:
                self._chat_log.clear()
            self._show_chat()

    @work(thread=True)
    def _run_doctor_checks(self) -> None:
        import subprocess
        try:
            g = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            git_ok = (g.returncode == 0)
            git_ver = g.stdout.strip().replace("git version ", "") if git_ok else "Not found"
        except Exception:
            git_ok = False
            git_ver = "Not found"

        try:
            n = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            node_ok = (n.returncode == 0)
            node_ver = n.stdout.strip() if node_ok else "Not found"
        except Exception:
            node_ok = False
            node_ver = "Not found"
            
        self.app.call_from_thread(self._update_doctor_ui, git_ok, git_ver, node_ok, node_ver)

    def _update_doctor_ui(self, git_ok: bool, git_ver: str, node_ok: bool, node_ver: str) -> None:
        try:
            vlist = self.query_one("#view-list", ScrollableContainer)
            try:
                self.query_one("#doctor-running").remove()
            except Exception:
                pass

            ok  = "[bold #10b981]✅  OK[/]"
            err = "[bold #ef4444]❌  Missing[/]"
            git_status  = ok  if git_ok  else err
            node_status = ok  if node_ok else err

            vlist.mount(Static("\n  [bold #6366f1]◈  SYSTEM DIAGNOSTICS[/]\n", classes="doctor-title"))
            vlist.mount(Static(f"  📦  Git     {git_status}  [dim]{git_ver}[/]"))
            vlist.mount(Static(f"  🟢  Node    {node_status}  [dim]{node_ver}[/]"))
            vlist.mount(Static(f"  🔗  MCP     [bold #10b981]✅  Active[/]"))
            vlist.mount(Static(f"  🐍  Python  [bold #10b981]✅  OK[/]  [dim]v3.12[/]"))
            vlist.mount(Static(""))
            all_ok = git_ok and node_ok
            summary_color = "#10b981" if all_ok else "#f5a623"
            summary_icon  = "✅" if all_ok else "⚠️"
            vlist.mount(Static(f"  {summary_icon}  [bold {summary_color}]{'All systems operational' if all_ok else 'Some tools missing — check above'}[/]\n"))
        except Exception as e:
            logger.debug("UI update skipped: %s", e)

    def _on_settings_result(self, result: dict | None) -> None:
        if result:
            try:
                # Config was already saved by SettingsScreen._do_save()
                new_cfg = config.load()
                # Rebuild the provider object from the freshly-saved config
                self._provider = create_provider(new_cfg)
                pname = self._provider.name
                model = self._provider.model
                # Sync state so header + sidebar show the right info
                self._state["model"] = f"{pname}/{model}"
                self._state["_provider_name"] = pname
                self._update_header()
                # Toast instead of cluttering the chat log
                self._show_toast(f"Provider switched → {pname} / {model}", kind="success")
                # Provider-specific post-switch actions
                if pname in ("opencode-zen", "opencode"):
                    from core.proxy import proxy_manager
                    proxy_manager.force_refresh()
                elif pname == "ollama":
                    fetch_ollama_models(force_refresh=True)
            except Exception as e:
                self._show_toast(f"Settings error: {e}", kind="error")
        # User cancelled — no action needed

    def _on_session_result(self, result: tuple | None) -> None:
        """Handle session load result from SessionListScreen."""
        if result and result[0] == "loaded":
            _, msgs = result
            self._state["_messages"] = msgs
            self._log_message("system", f"✓ Session loaded ({len(msgs)} messages)")
            self._print_history()
            self._update_header()
        self._refresh_sidebar_badges()

    def _on_help_result(self, cmd: str | None) -> None:
        """Handle quick action command from HelpScreen."""
        if cmd:
            self.run_worker(self._cmd(cmd))

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle quick provider switcher in sidebar."""
        if (event.select.id or "") == "quick-provider":
            if event.value and event.value != Select.BLANK:
                new_provider = str(event.value)
                self._switch_provider(new_provider)

    def _switch_provider(self, new_provider: str) -> None:
        """Switch to a different provider, saving config and rebuilding."""
        try:
            cfg = config.load()
            cfg["provider"] = {
                "name": new_provider,
                "model": cfg.get("provider", {}).get("model", "deepseek-v4-flash-free"),
                "base_url": cfg.get("provider", {}).get("base_url", ""),
            }
            config.save(cfg)
            self._provider = create_provider(config.load())
            pname = self._provider.name
            model = self._provider.model
            self._state["model"] = f"{pname}/{model}"
            self._state["_provider_name"] = pname
            self._update_header()
            self._show_toast(f"Switched to {pname} / {model}", kind="success")
            if pname in ("opencode-zen", "opencode"):
                proxy_manager.force_refresh()
            elif pname == "ollama":
                fetch_ollama_models(force_refresh=True)
        except Exception as e:
            self._show_toast(f"Switch failed: {e}", kind="error")

    # ── Input ───────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        self.query_one("#input", Input).value = ""
        if text.startswith("/"):
            await self._cmd(text)
        elif text.startswith("!"):
            self._do_skill(text[1:])
        else:
            self._chat(text)

    async def _cmd(self, text: str) -> None:
        parts = text.split(None, 1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            self.app.exit()
        elif cmd == "/agent" and len(parts) > 1:
            task = parts[1]
            self._chat_agent(task)
        elif cmd == "/clear":
            if self._chat_log:
                self._chat_log.clear()
            self._show_chat()
        elif cmd == "/help":
            await self._do_action("help")
        elif cmd == "/tools":
            await self._do_action("tools")
        elif cmd == "/skills":
            await self._do_action("skills")
        elif cmd == "/history":
            await self._do_action("history")
        elif cmd == "/memories":
            await self._do_action("memories")
        elif cmd == "/settings":
            await self._do_action("settings")
        elif cmd == "/provider" and len(parts) > 1:
            prov_name = parts[1].strip().lower()
            from .screens.settings import PROVIDER_LIST
            p_ids = [p["id"] for p in PROVIDER_LIST]
            if prov_name in p_ids:
                try:
                    cfg = config.load()
                    ap = cfg.get("all_providers", {}).get(prov_name, {})
                    pi_active = next((p for p in PROVIDER_LIST if p["id"] == prov_name), {})
                    
                    cfg["provider"] = {
                        "name":     prov_name,
                        "model":    ap.get("model") or pi_active.get("default_models", [""])[0],
                        "base_url": ap.get("base_url") or pi_active.get("default_url", ""),
                        "api_key":  ap.get("api_key", "public"),
                    }
                    config.save(cfg)
                    
                    self._provider = create_provider(cfg)
                    self._state["model"] = f"{prov_name}/{self._provider.model}"
                    self._state["_provider_name"] = prov_name
                    self._update_header()
                    self._show_toast(f"Provider switched to {prov_name}", kind="success")
                except Exception as e:
                    self._show_toast(f"Failed to switch provider: {e}", kind="error")
            else:
                self._show_toast(f"Unknown provider: {prov_name}. Available: {', '.join(p_ids)}", kind="warn")
        elif cmd == "/model" and len(parts) > 1:
            model_name = parts[1].strip()
            try:
                cfg = config.load()
                prov_name = cfg.get("provider", {}).get("name", "opencode-zen")
                
                cfg["provider"]["model"] = model_name
                if "all_providers" not in cfg:
                    cfg["all_providers"] = {}
                if prov_name not in cfg["all_providers"]:
                    cfg["all_providers"][prov_name] = {}
                cfg["all_providers"][prov_name]["model"] = model_name
                
                config.save(cfg)
                
                self._provider = create_provider(cfg)
                self._state["model"] = f"{prov_name}/{model_name}"
                self._update_header()
                self._show_toast(f"Model switched to {model_name}", kind="success")
            except Exception as e:
                self._show_toast(f"Failed to switch model: {e}", kind="error")
        elif cmd == "/doctor":
            await self._do_action("doctor")
        elif cmd == "/save":
            await self._do_action("save")
        elif cmd == "/export":
            await self._do_action("export")
        elif cmd == "/remember" and len(parts) > 1:
            MemoryStore().save(f"note-{parts[1][:20]}", parts[1], {"type": "feedback"})
            self._log_message("system", "✓ Feedback memory has been recorded")
            self._show_chat()
        elif cmd.startswith("/skills") and len(parts) > 1:
            self._do_skill(parts[1].strip().lstrip("!"))
        elif cmd == "/version":
            self._log_message("system", "WIDDX v3.0 — Terminal AI Chat Tool")
        elif cmd == "/agent" and len(parts) > 1:
            self._chat_agent(parts[1])
        else:
            self._log_message("system", f"✗ Unknown command: {cmd}. Click Help in sidebar or type /help")

    def _do_skill(self, name: str) -> None:
        if name == "off":
            skill_manager.deactivate()
            # Strip all skill prompts from stored messages
            msgs = self._state.get("_messages", [])
            self._state["_messages"] = [m for m in msgs if not m.get("_skill_prompt")]
            self._log_message("system", "⚡ Skill deactivated")
        elif skill_manager.toggle(name):
            s = skill_manager.active
            if s:
                # Inject skill prompt into stored messages (same as CLI)
                msgs = [m for m in self._state.get("_messages", []) if not m.get("_skill_prompt")]
                msgs.insert(0, {"role": "system", "content": s.prompt, "_skill_prompt": True})
                self._state["_messages"] = msgs
                self._log_message("system", f"⚡ Skill activated: !{s.name} — {s.description[:60]}")
            else:
                msgs = [m for m in self._state.get("_messages", []) if not m.get("_skill_prompt")]
                self._state["_messages"] = msgs
                self._log_message("system", "⚡ Skill deactivated")
            self._update_header()
        else:
            self._log_message("system", f"✗ Unknown skill: {name}")

    # ── Agent execution ─────────────────

    def _chat_agent(self, task: str) -> None:
        """Run task through AutonomousAgent (expert team)."""
        if self._processing:
            return
        self._show_chat()
        try:
            self._processing = True
            self._log_message("user", f"/agent {task}")
            self.query_one("#input", Input).disabled = True
            self._update_header()
            self.query_one("#processing", Static).set_class(True, "active")
            cfg = config.load()
            pv = self._provider or create_provider(cfg)
            td = list(self._tool_defs or tools.TOOL_DEFINITIONS)
            # Add use_skill + skill tools + MCP
            use_skill_def = skill_manager.get_use_skill_tool_def()
            if use_skill_def:
                td.append(use_skill_def)
            skill_tools = skill_manager.get_active_tools()
            if skill_tools:
                td.extend(skill_tools)
            try:
                td.extend(get_mcp_manager().get_all_tool_definitions())
            except Exception:
                pass
            self._run_agent(pv, td, task, cfg)
        except Exception as e:
            logger.warning("_chat_agent setup error: %s", e)
            self._processing = False
            raise

    @work(thread=True)
    def _run_agent(self, pv, td, task, cfg_d):
        """Run AutonomousAgent in background thread with live TUI feedback."""
        # ── Redirect agent output to TUI chat log ────────────
        import core.ui.ui as ui_mod
        _orig_sys = ui_mod.print_system_msg
        _orig_tc  = ui_mod.print_tool_call
        _orig_tm  = ui_mod.print_tool_msg
        _orig_re  = ui_mod.print_reasoning
        _orig_ai  = ui_mod.print_ai_msg

        def _tui_sys(msg): self.post_message(ResultMsg(f"⚙️ {msg}"))
        def _tui_tc(name, args):  self.post_message(ToolStepMsg(name, "pending", args[:100]))
        def _tui_tm(name, args):  self.post_message(ToolStepMsg(name, "ok", args[:200]))
        def _tui_re(text):  self._log_message("system", f"🧠 {text[:500]}")
        def _tui_ai(msg):   pass

        try:
            ui_mod.print_system_msg = _tui_sys
            ui_mod.print_tool_call  = _tui_tc
            ui_mod.print_tool_msg   = _tui_tm
            ui_mod.print_reasoning  = _tui_re
            ui_mod.print_ai_msg     = _tui_ai

            from core.agents.agent import AutonomousAgent
            cfg_d["_cancel_flag"] = lambda: self._cancel_requested
            agent = AutonomousAgent(pv, td, cfg_d, self._state)
            steps, summary = agent.run(task)
            step_log = "\n".join(
                f"  Step {s.step_num}: {s.tool_name} — {s.status}"
                for s in steps
            ) if steps else "  (no tools called)"
            result = f"[Agent completed {len(steps)} steps]\n\n{step_log}\n\n{summary}"
            self._state.setdefault("turns", 0)
            self._state["turns"] += len(steps)
            self.post_message(ResultMsg(result))
        except Exception as e:
            logger.warning("Agent execution error: %s", e)
            self.post_message(ErrorMsg(str(e)))
        finally:
            ui_mod.print_system_msg = _orig_sys
            ui_mod.print_tool_call  = _orig_tc
            ui_mod.print_tool_msg   = _orig_tm
            ui_mod.print_reasoning  = _orig_re
            ui_mod.print_ai_msg     = _orig_ai

    # ── Chat execution ──────────────────

    def _chat(self, text: str) -> None:
        if self._processing:
            return
        self._show_chat()
        try:
            self._processing = True
            self._log_message("user", text)
            self.query_one("#input", Input).disabled = True
            self._update_header()
            self.query_one("#processing", Static).set_class(True, "active")
            cfg = config.load()
            pv = self._provider or create_provider(cfg)
            td = list(self._tool_defs or tools.TOOL_DEFINITIONS)
            use_skill_def = skill_manager.get_use_skill_tool_def()
            if use_skill_def:
                td.append(use_skill_def)
            skill_tools = skill_manager.get_active_tools()
            if skill_tools:
                td.extend(skill_tools)
            try:
                td.extend(get_mcp_manager().get_all_tool_definitions())
            except Exception:
                pass

            # ── UIL routing: auto-detect if task needs agent ──
            try:
                from core.uil import UnifiedIntelligenceLayer, ExecutionMode
                uil = UnifiedIntelligenceLayer(provider=pv)
                uil.set_tool_defs(td)
                decision, _ = uil.process(text)
                mode = decision.mode if decision else ExecutionMode.SIMPLE_CHAT
            except Exception:
                mode = None  # fallback to simple chat

            msgs = list(self._state.get("_messages", []))
            if not any(m.get("role") == "system" for m in msgs):
                sp = cfg.get("system_prompt", "")
                sn = ", ".join(s.name for s in skill_manager.list_all()) or "none"
                msgs.insert(0, {"role": "system", "content": sp.replace("{skills_list}", sn)})
            if skill_manager.active:
                msgs = [m for m in msgs if not m.get("_skill_prompt")]
                msgs.insert(0, {"role": "system", "content": skill_manager.active.prompt, "_skill_prompt": True})

            # Route: complex tasks → agent, simple → single-loop chat
            if mode and mode in (ExecutionMode.AUTONOMOUS, ExecutionMode.EXPERT_TEAM):
                self._log_message("system", f"🧠 UIL routed to {mode.value} agent")
                self._run_agent(pv, td, text, cfg)
            else:
                msgs.append({"role": "user", "content": text})
                self._run_chat(pv, td, msgs, cfg)
        except Exception as e:
            logger.warning("_chat setup error: %s", e)
            self._processing = False
            raise

    @work(thread=True)
    def _run_chat(self, pv, td, msgs, cfg_d: dict) -> None:
        """Background chat execution — runs in a worker thread via Textual @work."""
        try:
            cfg_t = cfg_d.get("temperature", 0.7)
            max_iter = cfg_d.get("max_turns", 10)
            if hasattr(pv, "stream") and callable(pv.stream):
                self._stream_run(pv, td, msgs, cfg_t, max_iter)
            else:
                self._nonstream_run(pv, td, msgs, cfg_t, max_iter)
        except Exception as e:
            logger.warning("Chat execution error: %s", e)
            try:
                self.post_message(ErrorMsg(str(e)))
            except Exception:
                self.app.call_from_thread(self._finish)

    def _execute_tool_calls(self, tool_calls, content, msgs, model_name):
        """Shared: append assistant msg with tool_calls, execute tools, post results."""
        tc_list = _build_tc_list(tool_calls)
        msgs.append({"role": "assistant", "content": content or None,
                     "tool_calls": tc_list})
        for tc in tool_calls:
            if tc.name == "use_skill":
                # Handle skill activation/deactivation (same as CLI process_tool_calls)
                result = tools.execute_with_skills(tc.name, tc.args)
                if "activated" in result and skill_manager.active:
                    msgs = [m for m in msgs if not m.get("_skill_prompt")]
                    msgs.insert(0, {"role": "system", "content": skill_manager.active.prompt, "_skill_prompt": True})
                elif "deactivated" in result:
                    msgs[:] = [m for m in msgs if not m.get("_skill_prompt")]
                self._state["cost"] += estimate_turn_cost(model_name, 200, 50)
                msgs.append({"role": "tool",
                             "tool_call_id": _valid_tool_call_id(tc.id),
                             "name": tc.name, "content": result})
                continue

            if tc.name not in self._state.setdefault("tools_used", []):
                self._state["tools_used"].append(tc.name)
            try:
                result = tools.execute_with_skills(tc.name, tc.args)
            except Exception as tool_err:
                result = f"[Tool error: {tool_err}]"
            self._state["cost"] += estimate_turn_cost(model_name, 200, 100)
            msgs.append({"role": "tool",
                         "tool_call_id": _valid_tool_call_id(tc.id),
                         "name": tc.name, "content": result})
            self.post_message(ToolStepMsg(tc.name, "ok", result[:200]))

    def _nonstream_run(self, pv, td, msgs, cfg_t: float, max_iter: int) -> None:
        """Fallback: non-streaming provider."""
        last_content = ""
        model_name = self._state.get("model", "").split("/")[-1] or "unknown"
        for _ in range(max_iter):
            _sanitize_tool_call_ids(msgs)  # ensure valid tool_call_ids before API call
            content, calls = pv.chat(msgs, td, cfg_t)
            self._state["cost"] += estimate_turn_cost(model_name, 500, 1000)
            if not calls:
                self.post_message(ResultMsg(content, msgs=msgs))
                return
            self._execute_tool_calls(calls, content, msgs, model_name)
            last_content = content or ""
        self.post_message(ResultMsg(last_content or "[Max iterations]", msgs=msgs))

    def _stream_run(self, pv, td, msgs, cfg_t: float, max_iter: int) -> None:
        """Live streaming AI response — chunks arrive via StreamChunkMsg."""
        model_name = self._state.get("model", "").split("/")[-1] or "unknown"

        for turn in range(max_iter):
            _sanitize_tool_call_ids(msgs)  # ensure valid tool_call_ids before API call
            content_chunks: list[str] = []
            err_msg: str | None = None
            tool_calls = None

            for event in pv.stream(msgs, td, cfg_t):
                if event["type"] == "content":
                    content_chunks.append(event["data"])
                    self.post_message(StreamChunkMsg(event["data"]))
                elif event["type"] == "error":
                    err_msg = event["data"]
                    break
                elif event["type"] == "done":
                    _, tool_calls = event["data"]
                    break

            if err_msg:
                self.post_message(ErrorMsg(err_msg))
                return

            content = "".join(content_chunks)
            self._state["cost"] += estimate_turn_cost(model_name, 500, 1000)

            if tool_calls:
                self._execute_tool_calls(tool_calls, content, msgs, model_name)
            else:
                self.post_message(StreamEndMsg(content, msgs))
                return

        self.post_message(ResultMsg("[Max iterations]", msgs=msgs))

    @staticmethod
    def _parse_thinking(text: str) -> tuple[str, str]:
        """Extract [thinking] block from AI response.

        Returns (display_text, reasoning) where display_text has the
        thinking block stripped and reasoning is the extracted content.
        """
        if not text.startswith(_THINK_START):
            return text, ""
        end = text.find(_THINK_END)
        if end < 0:
            return text, ""
        reasoning = text[len(_THINK_START):end].strip()
        display = text[end + len(_THINK_END):].strip()
        return display, reasoning

    def on_result_msg(self, msg: ResultMsg) -> None:
        self._show_chat()
        raw = msg.text
        display, reasoning = self._parse_thinking(raw)
        if reasoning and self._chat_log:
            from rich.panel import Panel
            from rich.text import Text
            reasoning_summary = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            title = f" 🧠 Thinking Process ({reasoning.count('\n')+1} lines) "
            reasoning_panel = Panel(
                Text(reasoning_summary, style="italic #c084fc"),
                title=title,
                title_align="left",
                border_style="#8b5cf6",
                padding=(0, 2),
            )
            self._chat_log.write(reasoning_panel)
        if msg.msgs:
            # Bug#5 fix: strip _tool_desc injected by OllamaProvider text-mode
            self._state["_messages"] = [m for m in msg.msgs if not m.get("_tool_desc")]
        else:
            self._state["_messages"].append({"role": "assistant", "content": raw})
        self._state["turns"] = self._state.get("turns", 0) + 1

        self._log_message("assistant", display)
        self.query_one("#chat-log", RichLog).scroll_end(animate=False)
        self._finish()

    def on_tool_step_msg(self, msg: ToolStepMsg) -> None:
        # Update processing bar with current tool name
        try:
            bar = self.query_one("#processing", Static)
            tool_icons = {
                "read": "📖", "write": "✏️", "edit": "🔧", "bash": "💻",
                "glob": "🔍", "grep": "🔎", "web_fetch": "🌐",
                "validate": "✅", "use_skill": "⚡",
            }
            icon = tool_icons.get(msg.tool, "🛠")
            if msg.status == "pending":
                bar.update(f"[bold #0b0f19]{icon}  Calling: [bold]{msg.tool}[/]  —  {msg.detail[:50]}[/]")
            else:
                bar.update(f"[bold #0b0f19]{icon}  Done: [bold]{msg.tool}[/]  ✓  please wait…[/]")
        except Exception:
            pass
        # Log only completed tool steps (not pending)
        if msg.status == "ok":
            self._log_message("tool", f"🛠 {msg.tool}\n{msg.detail[:300]}")

    def on_stream_chunk_msg(self, msg: StreamChunkMsg) -> None:
        """Live chunk from AI stream — update in-place Static widget."""
        try:
            stream_out = self.query_one("#stream-output", Static)
            if not stream_out.display:
                stream_out.display = True
            current = str(stream_out.renderable or "")
            # Bug#3 fix: cap accumulated text to prevent memory bloat
            if len(current) > 10_000:
                current = current[-8_000:]
            stream_out.update(current + msg.chunk)
            # Bug#2 fix: Static.scroll_visible() doesn't exist — scroll chat-log instead
            try:
                self.query_one("#chat-log", RichLog).scroll_end(animate=False)
            except Exception:
                pass
        except Exception as e:
            logger.debug("UI update skipped: %s", e)  # widget not available yet

    def on_stream_end_msg(self, msg: StreamEndMsg) -> None:
        """Stream completed — hide live widget, show formatted panel."""
        try:
            stream_out = self.query_one("#stream-output", Static)
            stream_out.update("")
            stream_out.display = False
        except Exception as e:
            logger.debug("UI update skipped: %s", e)
        raw = msg.content
        display, reasoning = self._parse_thinking(raw)
        if reasoning and self._chat_log:
            from rich.panel import Panel
            from rich.text import Text
            reasoning_summary = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            title = f" 🧠 Thinking Process ({reasoning.count(chr(10))+1} lines) "
            reasoning_panel = Panel(
                Text(reasoning_summary, style="italic #c084fc"),
                title=title,
                title_align="left",
                border_style="#8b5cf6",
                padding=(0, 2),
            )
            self._chat_log.write(reasoning_panel)
        # Bug#4 fix: strip internal _tool_desc messages before saving to state
        # Bug#5 fix: _tool_desc added by OllamaProvider text-mode must not persist
        clean_msgs = [m for m in msg.msgs if not m.get("_tool_desc")]
        clean_msgs.append({"role": "assistant", "content": raw})
        self._state["_messages"] = clean_msgs
        self._state["turns"] = self._state.get("turns", 0) + 1
        self._log_message("assistant", display)
        self._finish()

    def on_error_msg(self, msg: ErrorMsg) -> None:
        self._log_message("system", f"Error: {msg.text}")
        self._finish()

    def action_cancel_or_focus(self) -> None:
        """Escape: cancel running task, or focus input if idle."""
        if self._processing:
            self._cancel_requested = True
            self._log_message("system", "🛑 Cancel requested — finishing current step...")
        else:
            self.query_one("#input", Input).focus()

    def _finish(self) -> None:
        if not self._processing:
            return
        self._cancel_requested = False
        self._processing = False
        self.query_one("#input", Input).disabled = False
        self.query_one("#input", Input).focus()
        self._update_header()
        self.query_one("#processing", Static).set_class(False, "active")
        try:
            project_state.save_session(self._state.get("_messages", []), self._state)
        except Exception as e:
            logger.debug("Session save skipped: %s", e)

        # ── Auto-index + auto-commit + summarization (same as CLI main.py) ──
        try:
            project_state.save_index(Path().resolve(), extra_ignore=[])
        except Exception as e:
            logger.debug("Index save skipped: %s", e)

        try:
            from core.project import git as git_utils
            auto_commit = project_state.load_project_config().get("auto_commit", True)
            if auto_commit:
                git_utils.auto_commit(Path().resolve(), "")
        except Exception as e:
            logger.debug("Auto-commit skipped: %s", e)

        try:
            msgs = self._state.get("_messages", [])
            old_len = len(msgs)
            msgs = project_state.summarize_conversation(msgs, keep_last=10)
            if len(msgs) < old_len:
                self._state["_messages"] = msgs
                self._log_message("system", f"Conversation summarized ({old_len} → {len(msgs)} messages)")
        except Exception as e:
            logger.debug("Summarization skipped: %s", e)


class WIDDXTUI(App):
    CSS_PATH = "app.tcss"
    BINDINGS = [Binding("ctrl+q", "quit", "Quit", show=False, priority=True)]
    TITLE = "WIDDX"

    def __init__(self, state=None, provider=None, tool_defs=None):
        super().__init__()
        self._state = state or {"model": "WIDDX", "cost": 0.0, "turns": 0, "_messages": []}
        self._provider = provider
        self._tool_defs = tool_defs or []

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self._state, self._provider, self._tool_defs))


def run_tui() -> None:
    # Prevent permission prompts from freezing TUI (no input() in async mode)
    from core.permissions import enable_tui_mode
    enable_tui_mode()

    cfg = config.load()
    tools.configure(cfg.get("sandbox_path"))  # sandbox safety (same as CLI)
    provider = create_provider(cfg)
    if provider.name in ("opencode-zen", "opencode"):
        proxy_manager.force_refresh()
    td = list(tools.TOOL_DEFINITIONS)
    st = {"model": f"{provider.name}/{provider.model}", "cost": 0.0, "turns": 0,
          "_messages": [], "tools_used": [], "_last_reasoning": ""}
    sd = project_state.load_session()
    if sd:
        m = sd.get("messages", [])
        ss = sd.get("state", {})
        if m:
            st["_messages"] = m
            st["cost"] = ss.get("cost", 0.0)
            st["turns"] = ss.get("turns", 0)
            if ss.get("model"):
                st["model"] = ss["model"]
    ctx = project_state.build_project_context()
    if ctx and not sd:
        st["_messages"].append({"role": "system", "content": f"[PROJECT CONTEXT]\n{ctx}"})
    ins = project_state.load_project_config().get("project_instructions", "")
    if ins:
        st["_messages"].append({"role": "system", "content": f"[INSTRUCTIONS]\n{ins}"})
    WIDDXTUI(state=st, provider=provider, tool_defs=td).run()


if __name__ == "__main__":
    run_tui()

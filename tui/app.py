"""WIDDX TUI — Enhanced Terminal Interface with Rich Diagnostics & Styling."""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path
from bidi.algorithm import get_display
ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fix_rtl(text: str) -> str:
    """Fix RTL/Arabic text for proper display using python-bidi."""
    if not text:
        return ""
    # Check if text contains RTL characters
    rtl_chars = any("\u0600" <= char <= "\u06FF" or  # Arabic
                    "\u0750" <= char <= "\u077F" or  # Arabic Supplement
                    "\u08A0" <= char <= "\u08FF" or  # Arabic Extended-A
                    "\uFB50" <= char <= "\uFDFF" or  # Arabic Presentation Forms-A
                    "\uFE70" <= char <= "\uFEFF"    # Arabic Presentation Forms-B
                    for char in text)
    if rtl_chars:
        return get_display(text)
    return text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import RichLog, Input, Static, Button, Label, Select
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.message import Message
from textual import work
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.markdown import Markdown
from rich.align import Align

from core import config, tools
from core.providers.providers import create_provider, estimate_turn_cost, fetch_ollama_models, get_available_models
from core.proxy import proxy_manager
from core.skills import skill_manager
from core.mcp.client import get_mcp_manager
from core.memory import MemoryStore
from core.project import state as project_state
from core.chat import _valid_tool_call_id, _build_tc_list, _sanitize_tool_call_ids
from core.workflow import WorkflowEngine
from core.session_v2 import SessionV2, get_current_session, set_current_session, create_new_session


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
logger.setLevel(logging.DEBUG)
logger.propagate = False

# Create log format
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Avoid adding duplicate handlers
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # File handler
    log_file = Path(ROOT) / "widdx-tui.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

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


from .screens.ubuntu_grid import UbuntuGrid
from .widgets import HeaderWidget


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
        Binding("ctrl+t", "toggle_thinking", "Toggle Thinking Panels", show=False),
        Binding("ctrl+up", "history_prev", "Previous Command", show=False),
        Binding("ctrl+down", "history_next", "Next Command", show=False),
        Binding("alt+up", "msg_prev", "Previous Message", show=False),
        Binding("alt+down", "msg_next", "Next Message", show=False),
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
        self._stream_buffer = ""
        self._show_thinking = True
        self._live_response_renderable = None  # Track last live response in RichLog
        self._command_history = []  # Command history for autocomplete
        self._history_index = -1  # Current position in history
        self._message_index = -1  # Current position in message navigation
        self._important_messages = set()  # Track important message indices
        self._compact_mode = False  # Compact mode for long messages
        self._user_patterns = {}  # Track user patterns/preferences
        self._response_cache = {}  # Cache responses to prevent data loss
        self._silent_mode = False  # Silent mode (no sounds)
        self._backup_timer = None  # Periodic backup timer
        self._show_quick_reply = False  # Toggle quick reply mode
        # Initialize Session V2
        self._session = get_current_session()
        if not self._session:
            self._session = create_new_session(name="Default Session")
        # Sync initial messages
        if not self._state.get("_messages"):
            self._state["_messages"] = self._session.messages.copy()

    def compose(self) -> ComposeResult:
        yield HeaderWidget()
        yield Static("[bold #0b0f19]⚡  Thinking and executing tools  —  please wait...[/]", id="processing")
        with Horizontal(id="body"):
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True, max_lines=5000)
            yield Static(id="stream-output")
            yield ViewPanel(id="view-panel")
        with Horizontal(id="input-container"):
            yield Label("❯", id="prompt-label")
            yield Input(placeholder="Type a message…  (/help for commands)", id="input")
            yield Static("", id="char-count")
            # Quick reply buttons (shown when input is hidden)
            yield Button("Yes", id="quick-yes", variant="default", classes="quick-reply")
            yield Button("No", id="quick-no", variant="default", classes="quick-reply")
            yield Button("Explain more", id="quick-explain", variant="default", classes="quick-reply")
        yield Static(id="status")
        # Toast notification overlay (hidden by default)
        yield Static("", id="toast", classes="toast-hidden")

    def on_mount(self) -> None:
        self._chat_log = self.query_one("#chat-log", RichLog)
        self._show_chat()
        self._print_history()
        self._update_header()
        self._update_status()
        self._refresh_badges()
        # Initialize provider in header
        current_provider = self._state.get("model", "").split("/")[0]
        header_widget = self.query_one(HeaderWidget)
        header_widget.initialize_provider(current_provider)
        self.query_one("#input", Input).focus()
        # Set initial display state for quick reply widgets
        self._toggle_quick_reply(self._show_quick_reply)
        # Preload models and resources
        self._preload_resources()
        # Start periodic backup timer (every 5 minutes)
        self._backup_timer = self.set_timer(300, self._periodic_backup)
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider/branch change from header or legacy."""
        logger.info(f"[MainScreen] on_select_changed: {event.select.id} = {event.value}")
        try:
            event.stop()
            sid = event.select.id or ""
            value = event.value
            if value is None or value == Select.BLANK:
                return
            
            if sid == "header-provider":
                logger.info(f"[MainScreen] Switching provider to {value}")
                self._switch_provider(value)
            elif sid == "header-branch":
                logger.info(f"[MainScreen] Switching branch to {value}")
                self._switch_branch(value)
        except Exception as e:
            logger.exception(f"[MainScreen] Error handling select change: {e}")

    # ── UI logging helpers ──────────────────────

    def _log(self, text: str) -> None:
        if self._chat_log:
            self._chat_log.write(text)

    def _categorize_message(self, role: str, content: str) -> str:
        """Auto-categorize message based on content."""
        if role == "tool":
            return "tool"
        elif role == "system":
            return "system"
        
        content_lower = content.lower()
        
        # Code-related
        if any(kw in content_lower for kw in ["```", "def ", "class ", "function", "import ", "code", "programming"]):
            return "code"
        # Research-related
        elif any(kw in content_lower for kw in ["research", "search", "find", "look up", "investigate"]):
            return "research"
        # Question-related
        elif any(kw in content_lower for kw in ["?", "how", "what", "why", "explain", "tell me"]):
            return "question"
        # File-related
        elif any(kw in content_lower for kw in ["file", "read", "write", "edit", "create", "delete"]):
            return "file"
        # Default
        else:
            return "chat"

    def _process_mentions(self, text: str) -> str:
        """Process @message_number mentions to reference previous messages."""
        import re
        msgs = self._state.get("_messages", [])
        if not msgs:
            return text
        
        # Find all @number patterns
        mentions = re.findall(r'@(\d+)', text)
        for mention in mentions:
            try:
                idx = int(mention) - 1  # Convert to 0-based index
                if 0 <= idx < len(msgs):
                    msg = msgs[idx]
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:200]
                    # Replace @number with actual message reference
                    text = text.replace(f"@{mention}", f"[Referring to message #{mention}: {role.upper()} - {content}...]")
            except (ValueError, IndexError):
                pass
        return text

    def _auto_correct(self, text: str) -> str:
        """Auto-correct common command errors."""
        # Common command typos
        corrections = {
            "/clea": "/clear",
            "/clera": "/clear",
            "/hepl": "/help",
            "/hel": "/help",
            "/sav": "/save",
            "/exprot": "/export",
            "/expot": "/export",
            "/serach": "/search",
            "/searhc": "/search",
            "/doctro": "/doctor",
            "/doctr": "/doctor",
            "/previe": "/preview",
            "/previw": "/preview",
            "/sumary": "/summary",
            "/sumamry": "/summary",
            "/compac": "/compact",
            "/compct": "/compact",
        }
        for typo, correction in corrections.items():
            if text.startswith(typo):
                self._show_toast(f"✏️ Auto-corrected: {typo} → {correction}", kind="info", duration=2.0)
                return text.replace(typo, correction, 1)
        return text

    def _track_patterns(self, text: str) -> None:
        """Track user patterns and preferences."""
        # Track command usage
        if text.startswith("/"):
            cmd = text.split()[0]
            self._user_patterns[cmd] = self._user_patterns.get(cmd, 0) + 1
        # Track time of day patterns
        from datetime import datetime
        hour = datetime.now().hour
        time_key = f"hour_{hour}"
        self._user_patterns[time_key] = self._user_patterns.get(time_key, 0) + 1
        # Track message length preference
        msg_len = len(text)
        if msg_len < 50:
            self._user_patterns["short_msgs"] = self._user_patterns.get("short_msgs", 0) + 1
        elif msg_len > 200:
            self._user_patterns["long_msgs"] = self._user_patterns.get("long_msgs", 0) + 1

    def _preload_resources(self) -> None:
        """Preload models and resources for faster startup."""
        try:
            # Preload common modules
            import importlib
            modules_to_preload = ["rich", "textual", "pathlib"]
            for module in modules_to_preload:
                try:
                    importlib.import_module(module)
                except ImportError:
                    pass
            # Preload configuration
            try:
                from core import config
                config.load()
            except Exception:
                pass
        except Exception as e:
            logger.debug("Preloading skipped: %s", e)

    def _periodic_backup(self) -> None:
        """Perform periodic backup of the session."""
        try:
            import json
            msgs = self._state.get("_messages", [])
            if not msgs:
                # Restart timer if no messages
                self._backup_timer = self.set_timer(300, self._periodic_backup)
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"auto_backup_{timestamp}.json"
            
            session_data = {
                "timestamp": timestamp,
                "model": self._state.get("model", "unknown"),
                "turns": self._state.get("turns", 0),
                "messages": msgs
            }
            
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            if not self._silent_mode:
                self._log_message("system", f"💾 Auto-backup created: {filename}")
            
            # Restart timer for next backup
            self._backup_timer = self.set_timer(300, self._periodic_backup)
        except Exception as e:
            logger.debug("Periodic backup failed: %s", e)
            # Restart timer even on failure
            self._backup_timer = self.set_timer(300, self._periodic_backup)

    def _log_message(self, role: str, content: str) -> None:
        if not self._chat_log:
            return
        from rich.panel import Panel
        from rich.text import Text
        from rich.markdown import Markdown
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")

        # Fix RTL text
        content = _fix_rtl(content)

        # Auto-categorize message
        category = self._categorize_message(role, content)

        # Compact mode: trim long messages
        if self._compact_mode and len(content) > 500:
            content = content[:500] + "... [truncated in compact mode]"

        # Smart formatting for code blocks
        if "```" in content and not self._compact_mode:
            # Preserve code blocks with better formatting
            content = content.replace("```python", "```").replace("```javascript", "```").replace("```typescript", "```")

        if role == "user":
            title = f" 👤 You  [dim]{ts}[/dim] "
            border_style = "#4f46e5"
            msg_text = Text(content, style="default")
            panel = Panel(msg_text, title=title, title_align="left", border_style=border_style, padding=(1, 2))
        elif role == "assistant":
            title = f" 🤖 Assistant  [dim]{ts}[/dim] "
            border_style = "#059669"
            md = Markdown(content, code_theme="monokai")
            panel = Panel(md, title=title, title_align="left", border_style=border_style, padding=(1, 2))
        elif role == "system":
            title = f" ⚙ System  [dim]{ts}[/dim] "
            border_style = "#d97706"
            panel = Panel(content, title=title, title_align="left", border_style=border_style, padding=(1, 1))
        else:
            panel = Panel(content, border_style="dim", padding=(1, 1))

        self._chat_log.write(panel)
        
        # Sync message to Session V2 (don't save system/tool messages unless needed)
        if self._session and role in ["user", "assistant"]:
            try:
                # Check if message is already in state (avoid duplicates)
                msgs = self._state.get("_messages", [])
                if len(msgs) > 0:
                    last_msg = msgs[-1]
                    if last_msg.get("role") == role and last_msg.get("content") == content:
                        return  # already added
                self._session.add_message(role, content)
            except Exception as e:
                logger.debug(f"Failed to sync message to session: {e}")

    def _log_welcome_message(self) -> None:
        if not self._chat_log:
            return
        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text

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
        "gguf":         ("📦", "#8b5cf6", "GGUF Local"),
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

        self.query_one("#header-info", Static).update(
            f"  [bold #6366f1]◈[/]  {prov_badge}  [dim]│[/]  "
            f"[dim]{model_short}[/]  [dim]│[/]  "
            f"[{cost_color}]${c:.4f}[/]  [dim]│[/]  [dim]{t} turns[/]"
            f"{proxy_part}{sk}"
        )

    def _update_status(self) -> None:
        self.query_one("#status", Static).update(
            "  [dim #10b981]◈ Ready[/]   "
            "[bold #0891b2]Ctrl+P[/] [dim]Help[/]   "
            "[bold #0891b2]Ctrl+L[/] [dim]Clear[/]   "
            "[bold #f5a623]/agent[/] [dim]Auto[/]   "
            "[bold #0891b2]Ctrl+Q[/] [dim]Quit[/]"
        )

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
        # Skip toast in silent mode (except for errors)
        if self._silent_mode and kind != "error":
            return
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

    # ── Badge updates (simplified) ──────────────

    def _refresh_badges(self) -> None:
        """No longer needed — sidebar removed."""
        pass


    def _show_chat(self) -> None:
        self.query_one("#chat-log", RichLog).display = True
        self.query_one("#stream-output", Static).display = False
        panel = self.query_one("#view-panel", ViewPanel)
        panel.display = False
        panel.set_class(False, "active")

    def _show_view(self, title: str) -> None:
        self.query_one("#chat-log", RichLog).display = False
        self.query_one("#stream-output", Static).display = False
        panel = self.query_one("#view-panel", ViewPanel)
        panel.display = True
        panel.set_class(True, "active")
        panel.set_title(title)

    async def action_clear_chat(self) -> None:
        await self._do_action("clear")

    async def action_show_help(self) -> None:
        await self._do_action("help")

    def action_toggle_thinking(self) -> None:
        """Toggle visibility of thinking panels."""
        self._show_thinking = not self._show_thinking
        # Show a toast notification
        try:
            toast = self.query_one("#toast", Static)
            status = "shown" if self._show_thinking else "hidden"
            toast.update(f"[bold]🧠 Thinking panels {status}[/]")
            toast.remove_class("toast-hidden")
            toast.add_class("toast-visible")
            # Hide after 2 seconds
            async def hide_toast():
                await self.sleep(2)
                toast.remove_class("toast-visible")
                toast.add_class("toast-hidden")
            self.run_async(hide_toast())
        except Exception as e:
            logger.debug("Toast error: %s", e)

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
        logger.info(f"[MainScreen] on_button_pressed, button id: {bid}")
        if not bid:
            return
        
        # Handle quick reply buttons first
        if bid == "quick-yes":
            self._chat("Yes")
            self._toggle_quick_reply(False)
            return
        elif bid == "quick-no":
            self._chat("No")
            self._toggle_quick_reply(False)
            return
        elif bid == "quick-explain":
            self._chat("Please explain this in more detail")
            self._toggle_quick_reply(False)
            return
        
        # ── Grid button → open Ubuntu-style launcher ───────
        if bid == "btn-grid":
            logger.info("[MainScreen] Pushing UbuntuGrid screen...")
            event.stop()
            try:
                self.app.push_screen(UbuntuGrid(
                    nav_buttons=self.NAV_BUTTONS,
                    act_buttons=self.ACT_BUTTONS,
                    help_buttons=self.HELP_BUTTONS,
                ), self._on_grid_result)
                logger.info("[MainScreen] UbuntuGrid screen pushed successfully")
            except Exception as e:
                logger.exception(f"[MainScreen] Error pushing UbuntuGrid screen: {e}")
            return
        
        # ── Navigation buttons (chat, tools, skills, ...) ──
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

    def _on_grid_result(self, result: str | None) -> None:
        """Handle result from UbuntuGrid launcher."""
        logger.info(f"[UbuntuGrid Result]: Received result: {result}")
        try:
            if not result:
                logger.info("[UbuntuGrid Result]: No result, returning")
                return
            if result.startswith("provider:"):
                # Switch provider
                new_provider = result[9:]
                logger.info(f"[UbuntuGrid Result]: Switching provider to {new_provider}")
                self._switch_provider(new_provider)
            elif result.startswith("branch:"):
                # Switch branch
                new_branch = result[7:]
                logger.info(f"[UbuntuGrid Result]: Switching branch to {new_branch}")
                self._switch_branch(new_branch)
            elif result == "clear":
                logger.info("[UbuntuGrid Result]: Calling clear action")
                self.run_worker(self._do_action("clear"))
            else:
                # It's a nav action (chat, tools, skills, etc.)
                logger.info(f"[UbuntuGrid Result]: Calling action {result}")
                self.run_worker(self._do_action(result))
        except Exception as e:
            logger.exception(f"[UbuntuGrid Result]: Error processing result: {e}")

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
            # Add workflow tools if provider is available
            if self._provider:
                try:
                    wf = WorkflowEngine(self._provider, tl, config.load(), self._state)
                    tl.extend(wf.get_tool_definitions())
                except Exception:
                    pass
            self._current_tools = tl
            for i, td in enumerate(tl):
                name = td["name"]
                desc = (td.get("description", "") or "")[:75]
                mcp_tag = "  [MCP]" if name.startswith("mcp__") else ""
                wf_tag = "  [WORKFLOW]" if name in ("create_agent", "run_parallel") else ""
                vlist.mount(Button(f"  🛠️  {name}{mcp_tag}{wf_tag}  —  {desc}", id=f"tool-{i}"))
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
            self.app.push_screen(MemoryListScreen(state=self._state), callback=lambda _: self._refresh_badges())
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
                    self._refresh_badges()
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
            self._state["_messages"] = []
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
            vlist.mount(Static("  🔗  MCP     [bold #10b981]✅  Active[/]"))
            vlist.mount(Static("  🐍  Python  [bold #10b981]✅  OK[/]  [dim]v3.12[/]"))
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
        if result:
            if result[0] == "loaded":
                _, msgs = result
                self._state["_messages"] = msgs
                self._log_message("system", f"✓ Session loaded ({len(msgs)} messages)")
                self._print_history()
                self._update_header()
            elif result[0] == "new":
                _, sess = result
                self._session = sess
                set_current_session(sess)
                self._state["_messages"] = []
                self._chat_log.clear()
                self._log_welcome_message()
                self._update_header()
        self._refresh_badges()

    def _on_help_result(self, cmd: str | None) -> None:
        """Handle quick action command from HelpScreen."""
        if cmd:
            self.run_worker(self._cmd(cmd))
                
    def _switch_branch(self, new_branch: str) -> None:
        """Switch to a different session branch."""
        try:
            from core.project.state import set_current_branch, load_session
            ok = set_current_branch(new_branch)
            if ok:
                # Reload session
                session_data = load_session()
                self._state["_messages"] = []
                if session_data:
                    s = session_data.get("state", {})
                    self._state["model"] = s.get("model", self._state["model"])
                    self._state["cost"] = s.get("cost", 0.0)
                    self._state["turns"] = s.get("turns", 0)
                    saved_msgs = session_data.get("messages", [])
                    if saved_msgs:
                        self._state["_messages"] = list(saved_msgs)
                # Clear chat log and reload messages
                self._chat_log.clear()
                self._print_history()
                self._update_header()
                
                # Update branch selector in header
                header_widget = self.query_one(HeaderWidget)
                header_widget.update_branch(new_branch)
                
                self._show_toast(f"Switched to branch '{new_branch}'!", kind="success")
            else:
                self._show_toast("Failed to switch branch!", kind="error")
        except Exception as e:
            self._log_message("system", f"Failed to switch branch: {e}")

    def _switch_provider(self, new_provider: str) -> None:
        """Switch to a different provider, fetching available models automatically."""
        import threading
        try:
            cfg = config.load()
            
            # Get default base URL for the new provider
            from core.providers.providers import _DEFAULT_BASE_URLS
            new_base_url = cfg.get("provider", {}).get("base_url", "") or _DEFAULT_BASE_URLS.get(new_provider, "")
            
            # Fetch available models in background (to not block UI)
            def _fetch_and_switch():
                try:
                    # Get available models for new provider
                    available_models = get_available_models(new_provider, base_url=new_base_url, force_refresh=True)
                    
                    # Determine which model to use: first available, or existing if it's still valid
                    existing_model = cfg.get("provider", {}).get("model", "")
                    if existing_model and existing_model in available_models:
                        new_model = existing_model
                    elif available_models:
                        new_model = available_models[0]
                    else:
                        # Fall back to default
                        from core.providers.providers import _DEFAULT_MODELS
                        new_model = _DEFAULT_MODELS.get(new_provider, ["deepseek-v4-flash-free"])[0]
                    
                    # Update config
                    new_cfg = config.load()
                    new_cfg["provider"] = {
                        "name": new_provider,
                        "model": new_model,
                        "base_url": new_base_url,
                    }
                    
                    # Update all_providers if present
                    if "all_providers" not in new_cfg:
                        new_cfg["all_providers"] = {}
                    new_cfg["all_providers"][new_provider] = {
                        "model": new_model,
                        "base_url": new_base_url,
                        "api_key": new_cfg["provider"].get("api_key", "public" if new_provider in ("opencode-zen", "opencode") else "")
                    }
                    
                    config.save(new_cfg)
                    
                    # Update UI from main thread
                    def _apply_switch():
                        try:
                            self._provider = create_provider(new_cfg)
                            pname = self._provider.name
                            model = self._provider.model
                            self._state["model"] = f"{pname}/{model}"
                            self._state["_provider_name"] = pname
                            self._update_header()
                            
                            header_widget = self.query_one(HeaderWidget)
                            header_widget.update_provider(pname)
                            
                            self._show_toast(f"Switched to {pname} / {model}", kind="success")
                            
                            if pname in ("opencode-zen", "opencode"):
                                proxy_manager.force_refresh()
                        except Exception as inner_e:
                            self._show_toast(f"Switch failed: {inner_e}", kind="error")
                    
                    self.app.call_from_thread(_apply_switch)
                except Exception as e:
                    self.app.call_from_thread(lambda: self._show_toast(f"Failed to fetch models: {e}", kind="error"))
            
            # Show loading toast
            self._show_toast(f"Switching to {new_provider}…", kind="info", duration=5)
            
            # Run fetch in background
            threading.Thread(target=_fetch_and_switch, daemon=True).start()
            
        except Exception as e:
            self._show_toast(f"Switch failed: {e}", kind="error")

    # ── Input ───────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        # Auto-correct common errors
        text = self._auto_correct(text)
        # Process mentions (@message_number)
        text = self._process_mentions(text)
        # Track user patterns
        self._track_patterns(text)
        # Add to command history
        if text and (not self._command_history or text != self._command_history[-1]):
            self._command_history.append(text)
            if len(self._command_history) > 100:  # Keep last 100 commands
                self._command_history.pop(0)
        self._history_index = -1  # Reset history index
        self.query_one("#input", Input).value = ""
        if text.startswith("/"):
            await self._cmd(text)
        elif text.startswith("!"):
            self._do_skill(text[1:])
        else:
            self._chat(text)



    def _toggle_quick_reply(self, show: bool) -> None:
        """Toggle quick reply mode."""
        self._show_quick_reply = show
        try:
            input_field = self.query_one("#input", Input)
            char_count = self.query_one("#char-count", Static)
            quick_yes = self.query_one("#quick-yes", Button)
            quick_no = self.query_one("#quick-no", Button)
            quick_explain = self.query_one("#quick-explain", Button)
            
            input_field.display = not show
            char_count.display = not show
            quick_yes.display = show
            quick_no.display = show
            quick_explain.display = show
            
            if not show:
                input_field.focus()
        except Exception as e:
            logger.debug("Toggle quick reply failed: %s", e)

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
        elif cmd == "/search" and len(parts) > 1:
            query = parts[1].strip().lower()
            msgs = self._state.get("_messages", [])
            results = []
            for i, msg in enumerate(msgs):
                content = msg.get("content", "").lower()
                if query in content:
                    role = msg.get("role", "unknown")
                    results.append(f"[{i+1}] {role.upper()}: {content[:100]}...")
            if results:
                self._log_message("system", f"🔍 Found {len(results)} matches for '{query}':")
                for r in results[:10]:  # Show first 10 results
                    self._log_message("system", r)
                if len(results) > 10:
                    self._log_message("system", f"... and {len(results) - 10} more")
            else:
                self._log_message("system", f"🔍 No matches found for '{query}'")
        elif cmd == "/reply" and len(parts) > 1:
            try:
                msg_num = int(parts[1].strip())
                msgs = self._state.get("_messages", [])
                if 1 <= msg_num <= len(msgs):
                    msg = msgs[msg_num - 1]
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    self._log_message("system", f"📝 Replying to message #{msg_num} ({role.upper()})")
                    # Add context to next message
                    self._state["_reply_context"] = f"[Replying to: {content[:200]}...]"
                    self._show_toast(f"Replying to message #{msg_num}", kind="info", duration=2.0)
                else:
                    self._log_message("system", f"❌ Invalid message number: {msg_num}")
            except ValueError:
                self._log_message("system", "❌ Usage: /reply <message_number>")
        elif cmd == "/mark" and len(parts) > 1:
            try:
                msg_num = int(parts[1].strip())
                msgs = self._state.get("_messages", [])
                if 1 <= msg_num <= len(msgs):
                    if msg_num in self._important_messages:
                        self._important_messages.remove(msg_num)
                        self._log_message("system", f"⭐ Unmarked message #{msg_num}")
                    else:
                        self._important_messages.add(msg_num)
                        self._log_message("system", f"⭐ Marked message #{msg_num} as important")
                    self._show_toast(f"Message #{msg_num} marked", kind="info", duration=2.0)
                else:
                    self._log_message("system", f"❌ Invalid message number: {msg_num}")
            except ValueError:
                self._log_message("system", "❌ Usage: /mark <message_number>")
        elif cmd == "/compact":
            self._compact_mode = not self._compact_mode
            status = "enabled" if self._compact_mode else "disabled"
            self._log_message("system", f"📐 Compact mode {status}")
            self._show_toast(f"Compact mode {status}", kind="info", duration=2.0)
        elif cmd == "/silent":
            self._silent_mode = not self._silent_mode
            status = "enabled" if self._silent_mode else "disabled"
            self._log_message("system", f"🔇 Silent mode {status}")
            if not self._silent_mode:
                self._show_toast(f"Silent mode {status}", kind="info", duration=2.0)
        elif cmd == "/quickreply" or cmd == "/qr":
            self._toggle_quick_reply(not self._show_quick_reply)
            status = "enabled" if self._show_quick_reply else "disabled"
            self._log_message("system", f"⚡ Quick reply mode {status}")
            if not self._silent_mode:
                self._show_toast(f"Quick reply {status}", kind="info", duration=2.0)
        elif cmd == "/context":
            try:
                project_ctx = get_project_context()
                ctx_summary = project_ctx.get_context_summary()
                self._log_message("system", "📋 Project Context:")
                self._log_message("system", ctx_summary)
                self._show_toast("Project context loaded", kind="success", duration=2.0)
            except Exception as e:
                self._log_message("system", f"❌ Failed to load project context: {e}")
        elif cmd == "/structure":
            try:
                analyzer = get_structure_analyzer()
                structure_summary = analyzer.get_structure_summary()
                self._log_message("system", "📁 Project Structure:")
                self._log_message("system", structure_summary)
                self._show_toast("Project structure loaded", kind="success", duration=2.0)
            except Exception as e:
                self._log_message("system", f"❌ Failed to load project structure: {e}")
        elif cmd == "/git":
            try:
                project_ctx = get_project_context()
                git = project_ctx.context.git
                if git.is_git_repo:
                    self._log_message("system", "📊 Git Info:")
                    self._log_message("system", f"  Branch: {git.current_branch}")
                    if git.remote_url:
                        self._log_message("system", f"  Remote: {git.remote_url}")
                    if git.last_commit:
                        self._log_message("system", f"  Last Commit: {git.last_commit[:12]}")
                        self._log_message("system", f"  Date: {git.last_commit_date}")
                else:
                    self._log_message("system", "📊 Not a git repository")
                self._show_toast("Git info loaded", kind="success", duration=2.0)
            except Exception as e:
                self._log_message("system", f"❌ Failed to load git info: {e}")
        elif cmd == "/preview" and len(parts) > 1:
            filepath = parts[1].strip()
            try:
                from pathlib import Path
                path = Path(filepath)
                if path.exists() and path.is_file():
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    preview = content[:1000] + "\n... [truncated]" if len(content) > 1000 else content
                    self._log_message("system", f"📄 Preview of {filepath}:")
                    self._log_message("tool", preview)
                else:
                    self._log_message("system", f"❌ File not found: {filepath}")
            except Exception as e:
                self._log_message("system", f"❌ Error previewing file: {e}")
        elif cmd == "/summary":
            try:
                from core.project import project_state
                msgs = self._state.get("_messages", [])
                old_len = len(msgs)
                if old_len < 5:
                    self._log_message("system", "ℹ️ Conversation too short to summarize")
                    return
                msgs = project_state.summarize_conversation(msgs, keep_last=10)
                if len(msgs) < old_len:
                    self._state["_messages"] = msgs
                    self._log_message("system", f"📝 Conversation summarized ({old_len} → {len(msgs)} messages)")
                    self._show_toast("Conversation summarized", kind="success", duration=2.0)
                else:
                    self._log_message("system", "ℹ️ No summarization needed")
            except Exception as e:
                self._log_message("system", f"❌ Summarization failed: {e}")
        elif cmd == "/export" and len(parts) > 1:
            format_type = parts[1].strip().lower()
            if format_type in ("html", "pdf", "markdown"):
                try:
                    msgs = self._state.get("_messages", [])
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"conversation_{timestamp}.{format_type}"
                    
                    if format_type == "markdown":
                        content = "# Conversation Export\n\n"
                        for i, msg in enumerate(msgs):
                            role = msg.get("role", "unknown")
                            content_text = msg.get("content", "")
                            content += f"## {role.upper()} (Message {i+1})\n\n{content_text}\n\n"
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write(content)
                        self._log_message("system", f"📤 Exported conversation to {filename}")
                    elif format_type == "html":
                        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Conversation Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .user {{ background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .assistant {{ background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .system {{ background: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Conversation Export</h1>
"""
                        for i, msg in enumerate(msgs):
                            role = msg.get("role", "unknown")
                            content_text = msg.get("content", "").replace("\n", "<br>")
                            content += f"<div class=\"{role}\"><strong>{role.upper()} (Message {i+1}):</strong><br>{content_text}</div>"
                        content += "</body></html>"
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write(content)
                        self._log_message("system", f"📤 Exported conversation to {filename}")
                    elif format_type == "pdf":
                        self._log_message("system", "⚠️ PDF export requires additional dependencies. Exporting as HTML instead.")
                        # Fallback to HTML
                        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Conversation Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .user {{ background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .assistant {{ background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .system {{ background: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Conversation Export</h1>
"""
                        for i, msg in enumerate(msgs):
                            role = msg.get("role", "unknown")
                            content_text = msg.get("content", "").replace("\n", "<br>")
                            content += f"<div class=\"{role}\"><strong>{role.upper()} (Message {i+1}):</strong><br>{content_text}</div>"
                        content += "</body></html>"
                        filename = f"conversation_{timestamp}.html"
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write(content)
                        self._log_message("system", f"📤 Exported conversation to {filename}")
                    self._show_toast(f"Exported to {filename}", kind="success", duration=2.0)
                except Exception as e:
                    self._log_message("system", f"❌ Export failed: {e}")
            else:
                self._log_message("system", "❌ Usage: /export <html|pdf|markdown>")
        elif cmd == "/share":
            try:
                import json
                msgs = self._state.get("_messages", [])
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"session_share_{timestamp}.json"
                
                session_data = {
                    "timestamp": timestamp,
                    "model": self._state.get("model", "unknown"),
                    "turns": self._state.get("turns", 0),
                    "messages": msgs
                }
                
                with open(filename, "w", encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                self._log_message("system", f"🔗 Session saved to {filename}")
                self._log_message("system", "💡 Share this file with others to restore the session")
                self._show_toast(f"Session saved to {filename}", kind="success", duration=2.0)
            except Exception as e:
                self._log_message("system", f"❌ Share failed: {e}")
        elif cmd == "/restore" and len(parts) > 1:
            try:
                import json
                from pathlib import Path
                filepath = parts[1].strip()
                
                if not Path(filepath).exists():
                    self._log_message("system", f"❌ Backup file not found: {filepath}")
                    return
                
                with open(filepath, "r", encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # Restore session data
                self._state["_messages"] = session_data.get("messages", [])
                self._state["turns"] = session_data.get("turns", 0)
                self._state["model"] = session_data.get("model", "unknown")
                
                # Clear chat log and reprint
                self._chat_log.clear()
                self._print_history()
                
                self._log_message("system", f"✅ Session restored from {filepath}")
                self._log_message("system", f"📊 Restored {len(session_data.get('messages', []))} messages")
                self._show_toast("Session restored successfully", kind="success", duration=2.0)
            except Exception as e:
                self._log_message("system", f"❌ Restore failed: {e}")
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
        elif cmd == "/debug":
            from core.diagnostics import audit_silent_errors
            r = audit_silent_errors()
            total = sum(r["counts"].values())
            lines = [f"🔍 Silent error audit: {total} found — {r['counts']}"]
            lines += [f"  {f['file']}: {f['loc']}" for f in r["files"][:10]]
            self._log_message("system", "\n".join(lines))
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
        elif cmd == "/branch":
            from core.project.state import list_branches, get_current_branch, set_current_branch, create_branch
            sub = parts[1].strip() if len(parts) > 1 else "list"
            if sub == "list":
                current = get_current_branch()
                branches = list_branches()
                self._log_message("system", f"Available branches (current: {current}):")
                for b in branches:
                    prefix = "  * " if b == current else "    "
                    self._log_message("system", f"{prefix}{b}")
            elif sub.startswith("create"):
                new_name = sub[7:].strip() if len(sub) > 7 else ""
                if new_name:
                    ok = create_branch(new_name)
                    if ok:
                        self._show_toast(f"Branch '{new_name}' created!", kind="success")
                    else:
                        self._log_message("system", "Failed to create branch.")
            elif sub.startswith("switch"):
                target = sub[7:].strip() if len(sub) > 7 else ""
                if target:
                    self._switch_branch(target)
            else:
                self._log_message("system", "Unknown branch command. Use /branch list, /branch create <name>, /branch switch <name>")
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
            # Add use_skill + skill tools + MCP + Workflow
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
            # Add workflow tools
            try:
                wf = WorkflowEngine(pv, td, cfg, self._state)
                td.extend(wf.get_tool_definitions())
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

    @work(thread=True)
    def _run_expert_team(self, pv, td, task, cfg_d):
        """Run ExpertTeam in background thread with live TUI feedback."""
        # ── Redirect ExpertTeam output to TUI chat log ────────────
        import core.ui.ui as ui_mod
        _orig_sys = ui_mod.print_system_msg
        _orig_console = ui_mod.console

        def _tui_sys(msg): self.post_message(ResultMsg(f"⚙️ {msg}"))
        def _tui_phase(num, name, action):
            self._log_message("system", f"👥 [{num}] {name} — {action}...")
        def _tui_phase_done(action, message):
            self._log_message("system", f"✓ {action}: {message}")
        def _tui_summary():
            self._log_message("system", "👥 Expert Team completed")

        try:
            ui_mod.print_system_msg = _tui_sys
            ui_mod.console = type('obj', (object,), {'print': lambda *args, **kwargs: None})()

            from core.agents.expert import ExpertTeam
            cfg_d["_cancel_flag"] = lambda: self._cancel_requested
            team = ExpertTeam(pv, td, cfg_d, self._state)

            # Override print methods to use TUI
            team._print_phase = _tui_phase
            team._print_phase_done = _tui_phase_done
            team._print_team_summary = _tui_summary

            self._log_message("system", "👥 Expert Team activated - running specialized agents...")
            result = team.run(task)
            self._state.setdefault("turns", 0)
            self._state["turns"] += len(team._log)
            self.post_message(ResultMsg(result))
        except Exception as e:
            logger.warning("ExpertTeam execution error: %s", e)
            self.post_message(ErrorMsg(str(e)))
        finally:
            ui_mod.print_system_msg = _orig_sys
            ui_mod.console = _orig_console

    # ── Chat execution ──────────────────

    def _chat(self, text: str) -> None:
        if self._processing:
            return
        self._show_chat()
        try:
            # ── Auto-Skill Suggestion (TUI) ───────────────────────────
            if not text.startswith("!") and not text.startswith("/") and not skill_manager.active:
                suggested_skills = skill_manager.suggest_skills(text)
                if suggested_skills:
                    icons = [s.icon for s in suggested_skills if s.icon]
                    names = [s.name for s in suggested_skills]
                    msg = f"💡 Suggested skills: {', '.join([f'{icon} {name}' for icon, name in zip(icons, names)])}"
                    self._log_message("system", msg)
                    self._log_message("system", f"   Activate with: !{suggested_skills[0].name}")
            
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
            # Add workflow tools
            try:
                wf = WorkflowEngine(pv, td, cfg, self._state)
                td.extend(wf.get_tool_definitions())
            except Exception:
                pass

            # ── UIL routing: auto-detect if task needs agent ──
            try:
                from core.uil import UnifiedIntelligenceLayer, ExecutionMode
                uil = UnifiedIntelligenceLayer(provider=pv)
                uil.set_tool_defs(td)
                result, decision = uil.process(text)
                mode = decision.plan.mode if decision else ExecutionMode.SIMPLE_CHAT
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

            # Feature 1: Inject fresh project context
            try:
                from core.project.scanner import ProjectScanner
                scanner = ProjectScanner()
                ctx = scanner.build_context_block()
                if ctx:
                    msgs = [m for m in msgs if not m.get("_project_context")]
                    msgs.insert(0, {"role": "system", "content": ctx, "_project_context": True})
            except Exception:
                pass

            # Feature 2: Inject relevant memories
            try:
                from core.memory_learner import MemoryLearner
                ml = MemoryLearner(provider=pv)
                mem_ctx = ml.load_relevant(text)
                if mem_ctx:
                    msgs = [m for m in msgs if not m.get("_memory_context")]
                    msgs.insert(0, {"role": "system", "content": mem_ctx, "_memory_context": True})
            except Exception:
                pass

            # Route: complex tasks → agent, simple → single-loop chat
            if mode and mode == ExecutionMode.EXPERT_TEAM:
                self._log_message("system", f"🧠 UIL routed to {mode.value} agent")
                self._run_expert_team(pv, td, text, cfg)
            elif mode and mode == ExecutionMode.AUTONOMOUS:
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
            self._state["turns"] = self._state.get("turns", 0) + 1
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

            # Handle reasoning (if [thinking] tag is present)
            if content and content.startswith(_THINK_START):
                end_idx = content.find(_THINK_END)
                if end_idx > 0:
                    reasoning = content[len(_THINK_START):end_idx].strip()
                    content = content[end_idx + len(_THINK_END):].strip()
                    if reasoning:
                        self._state["_last_reasoning"] = reasoning

            # Strip leading [thinking] tags (alternate format)
            if content and content.startswith("["):
                end_idx = content.find("[/")
                if end_idx > 0:
                    close_bracket = content.find("]", end_idx)
                    if close_bracket > 0:
                        content = content[close_bracket + 1:].strip()

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
            reasoning_chunks: list[str] = []
            err_msg: str | None = None
            tool_calls = None

            for event in pv.stream(msgs, td, cfg_t):
                if event["type"] == "content":
                    content_chunks.append(event["data"])
                    self.post_message(StreamChunkMsg(event["data"]))
                elif event["type"] == "reasoning":
                    reasoning_chunks.append(event["data"])
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
            full_reasoning = "".join(reasoning_chunks)
            if full_reasoning:
                self._state["_last_reasoning"] = full_reasoning

            # Strip leading [thinking] tags (if any)
            if content and content.startswith("["):
                end_idx = content.find("[/")
                if end_idx > 0:
                    close_bracket = content.find("]", end_idx)
                    if close_bracket > 0:
                        content = content[close_bracket + 1:].strip()

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

    @staticmethod
    def _render_thinking(reasoning: str) -> Panel:
        """Render thinking with beautiful, structured formatting like DeepSeek."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        from rich.align import Align
        reasoning = _fix_rtl(reasoning)
        
        lines = reasoning.strip().split('\n')
        structured_items = []
        for line in lines:
            lstrip = line.strip()
            if not lstrip:
                continue
            # Detect step types
            if lstrip.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')) or lstrip[0].isdigit() and (len(lstrip) == 1 or lstrip[1] in '. '):
                structured_items.append(Text(f"  {lstrip}", style="#a78bfa"))
            elif lstrip.startswith(('-', '*', '•')):
                structured_items.append(Text(f"  • {lstrip[1:].strip()}", style="#c084fc"))
            elif any(keyword in lstrip.lower() for keyword in ['search', 'web', 'looking', 'checking', 'found']):
                structured_items.append(Text(f"  🌐 {lstrip}", style="#0ea5e9"))
            elif any(keyword in lstrip.lower() for keyword in ['reading', 'writing', 'editing', 'file']):
                structured_items.append(Text(f"  📄 {lstrip}", style="#8b5cf6"))
            elif any(keyword in lstrip.lower() for keyword in ['thinking', 'analyzing', 'understanding']):
                structured_items.append(Text(f"  💭 {lstrip}", style="#f5a623"))
            else:
                structured_items.append(Text(f"  {lstrip}", style="#e2e8f0"))
        
        content = Group(*structured_items)
        return Panel(
            content,
            title=f" 🧠 Thinking Process ({len(structured_items)} steps) ",
            title_align="left",
            border_style="#6d28d9",
            padding=(1, 2),
        )

    def on_result_msg(self, msg: ResultMsg) -> None:
        self._show_chat()
        raw = msg.text
        display, reasoning = self._parse_thinking(raw)
        # Cache response to prevent data loss
        self._response_cache[f"response_{self._state.get('turns', 0)}"] = raw
        if reasoning and self._chat_log and self._show_thinking:
            self._chat_log.write(self._render_thinking(reasoning))
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
                # Progress notification for long-running tools
                if msg.tool in ("bash", "web_fetch"):
                    self._show_toast(f"⏳ {msg.tool} running...", kind="info", duration=2.0)
            else:
                bar.update(f"[bold #0b0f19]{icon}  Done: [bold]{msg.tool}[/]  ✓  please wait…[/]")
        except Exception:
            pass
        # Log only completed tool steps (not pending)
        if msg.status == "ok":
            from rich.panel import Panel
            from rich.text import Text
            from rich.markdown import Markdown
            tool_icons = {
                "read": "📖", "write": "✏️", "edit": "🔧", "bash": "💻",
                "glob": "🔍", "grep": "🔎", "web_fetch": "🌐",
                "validate": "✅", "use_skill": "⚡",
            }
            icon = tool_icons.get(msg.tool, "🛠")
            
            tool_panel = Panel(
                Markdown(msg.detail[:500]),
                title=f" {icon} Tool: {msg.tool} ",
                title_align="left",
                border_style="#0ea5e9",
                padding=(1, 2),
            )
            if self._chat_log:
                self._chat_log.write(tool_panel)

    def on_stream_chunk_msg(self, msg: StreamChunkMsg) -> None:
        """Live chunk from AI stream — update last line in same chat area."""
        try:
            from rich.panel import Panel
            from rich.text import Text
            from rich.markdown import Markdown

            chat_log = self.query_one("#chat-log", RichLog)
            self._stream_buffer += _fix_rtl(msg.chunk)

            # Cap buffer size
            if len(self._stream_buffer) > 10_000:
                self._stream_buffer = self._stream_buffer[-8_000:]

            # Parse thinking and response
            display_text, thinking_text = self._parse_thinking(self._stream_buffer)

            # Build the live renderable (combined into a single Group)
            from rich.console import Group
            group_items = []
            if thinking_text and self._show_thinking:
                group_items.append(self._render_thinking(thinking_text))
            if display_text:
                response_panel = Panel(
                    Markdown(display_text),
                    title=" 🤖 Assistant ",
                    title_align="left",
                    border_style="#059669",
                    padding=(1, 2),
                )
                group_items.append(response_panel)
            elif not thinking_text and self._stream_buffer:
                # No thinking yet, just show raw buffer
                response_panel = Panel(
                    Text(self._stream_buffer, style="default"),
                    title=" 🤖 Assistant ",
                    title_align="left",
                    border_style="#059669",
                    padding=(1, 2),
                )
                group_items.append(response_panel)

            if group_items:
                combined = Group(*group_items)
                # Always try to remove old live renderable if it exists
                if self._live_response_renderable is not None:
                    try:
                        # Try to remove by identity
                        if self._live_response_renderable in chat_log.lines:
                            chat_log.lines.remove(self._live_response_renderable)
                        else:
                            # If not found by identity, try to remove last panel to be safe
                            if chat_log.lines and len(chat_log.lines) > 0:
                                last_line = chat_log.lines[-1]
                                # Check if it looks like a response panel (Group or Panel)
                                if isinstance(last_line, (Panel, Group)):
                                    chat_log.lines.pop()
                    except Exception:
                        pass
                # Write the new combined renderable
                chat_log.write(combined)
                self._live_response_renderable = combined

                # Scroll to end
                try:
                    chat_log.scroll_end(animate=False)
                except Exception:
                    pass
        except Exception as e:
            logger.debug("UI update skipped: %s", e)

    def on_stream_end_msg(self, msg: StreamEndMsg) -> None:
        """Stream completed — finalize live response: remove live renderable and write final one with _log_message."""
        try:
            chat_log = self.query_one("#chat-log", RichLog)
            self._stream_buffer = ""
            # Remove the live renderable if it's still in the chat log
            if self._live_response_renderable is not None:
                try:
                    if self._live_response_renderable in chat_log.lines:
                        chat_log.lines.remove(self._live_response_renderable)
                except Exception:
                    pass
            self._live_response_renderable = None
        except Exception as e:
            logger.debug("UI update skipped: %s", e)

        # Now write the final assistant response properly using _log_message
        display, reasoning = self._parse_thinking(msg.content)
        if reasoning and self._chat_log and self._show_thinking:
            self._chat_log.write(self._render_thinking(reasoning))
        self._log_message("assistant", display)

        # Bug#4 fix: strip internal _tool_desc messages before saving to state
        # Bug#5 fix: _tool_desc added by OllamaProvider text-mode must not persist
        clean_msgs = [m for m in msg.msgs if not m.get("_tool_desc")]
        clean_msgs.append({"role": "assistant", "content": msg.content})
        self._state["_messages"] = clean_msgs
        self._state["turns"] = self._state.get("turns", 0) + 1
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

    def action_history_prev(self) -> None:
        """Navigate to previous command in history (Ctrl+Up)."""
        if not self._command_history:
            return
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            cmd = self._command_history[-(self._history_index + 1)]
            self.query_one("#input", Input).value = cmd

    def action_history_next(self) -> None:
        """Navigate to next command in history (Ctrl+Down)."""
        if not self._command_history:
            return
        if self._history_index > 0:
            self._history_index -= 1
            cmd = self._command_history[-(self._history_index + 1)]
            self.query_one("#input", Input).value = cmd
        elif self._history_index == 0:
            self._history_index = -1
            self.query_one("#input", Input).value = ""

    def action_msg_prev(self) -> None:
        """Navigate to previous message in chat log (Alt+Up)."""
        msgs = self._state.get("_messages", [])
        if not msgs:
            return
        if self._message_index < len(msgs) - 1:
            self._message_index += 1
            msg = msgs[-(self._message_index + 1)]
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            self._show_toast(f"📜 [{role.upper()}] {content}...", kind="info", duration=2.0)

    def action_msg_next(self) -> None:
        """Navigate to next message in chat log (Alt+Down)."""
        msgs = self._state.get("_messages", [])
        if not msgs:
            return
        if self._message_index > 0:
            self._message_index -= 1
            msg = msgs[-(self._message_index + 1)]
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            self._show_toast(f"📜 [{role.upper()}] {content}...", kind="info", duration=2.0)
        elif self._message_index == 0:
            self._message_index = -1
            self._show_toast("📜 End of messages", kind="info", duration=1.0)

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

        # Feature 2: Auto-extract memories from this turn (TUI)
        try:
            from core.utils import get_last_turn
            msgs = self._state.get("_messages", [])
            last = get_last_turn(msgs)
            if last and self._state.get("turns", 0) % 2 == 0:
                from core.memory_learner import MemoryLearner
                ml = MemoryLearner(provider=self._provider)
                tools_used = list(self._state.get("tools_used", []))
                memories = ml.extract_from_turn(last["user"], last["assistant"], tools_used)
                if memories:
                    ml.store_memories(memories)
                    self._refresh_badges()
                    for m in memories:
                        self._log_message("system", f"Memory: [{m['type']}] {m['content'][:60]}")
        except Exception as e:
            logger.debug("Memory extraction skipped: %s", e)
            
        # Feature 5: Self-Reflection (TUI, every 4 turns)
        try:
            if self._state.get("turns", 0) % 4 == 0 and self._state.get("turns", 0) > 0:
                from core.self_reflection import reflect_on_last_turn
                msgs = self._state.get("_messages", [])
                reflect_on_last_turn(self._provider, msgs, self._state)
                self._log_message("system", "💭 Completed self-reflection and saved lessons!")
        except Exception as e:
            logger.debug("Self-reflection skipped: %s", e)

        # Feature 3: Proactive suggestions (TUI)
        try:
            from core.suggester import ProjectSuggester
            ps = ProjectSuggester()
            suggestions = ps.suggest()
            for s in suggestions[:2]:
                self._show_toast(f"{s.icon}  {s.title}", kind="info", duration=4.0)
        except Exception as e:
            logger.debug("Suggestions skipped: %s", e)

        # Feature 4: Smart command suggestions based on context
        try:
            msgs = self._state.get("_messages", [])
            turns = self._state.get("turns", 0)
            # Suggest /save after long conversation
            if turns >= 5 and turns % 5 == 0:
                self._show_toast("💡 Tip: Use /save to save this session", kind="info", duration=3.0)
            # Suggest /export after code changes
            tools_used = self._state.get("tools_used", [])
            if "write" in tools_used or "edit" in tools_used:
                if len([m for m in msgs if m.get("role") == "assistant"]) >= 3:
                    self._show_toast("💡 Tip: Use /export to export conversation", kind="info", duration=3.0)
            # Suggest /memories after learning
            if turns >= 10:
                self._show_toast("💡 Tip: Use /memories to view learned memories", kind="info", duration=3.0)
        except Exception as e:
            logger.debug("Smart command suggestions skipped: %s", e)

        # Feature 5: Intent prediction for next actions
        try:
            msgs = self._state.get("_messages", [])
            if len(msgs) >= 2:
                last_msg = msgs[-1].get("content", "").lower()
                # Predict next action based on last message
                if "error" in last_msg or "fix" in last_msg:
                    self._show_toast("🎯 Suggestion: Try /doctor to diagnose issues", kind="info", duration=3.0)
                elif "file" in last_msg or "read" in last_msg:
                    self._show_toast("🎯 Suggestion: Use /preview <file> to view files", kind="info", duration=3.0)
                elif "search" in last_msg or "find" in last_msg:
                    self._show_toast("🎯 Suggestion: Use /search <query> to find in conversation", kind="info", duration=3.0)
        except Exception as e:
            logger.debug("Intent prediction skipped: %s", e)

        # Feature 6: Context suggestions for relevant files
        try:
            msgs = self._state.get("_messages", [])
            if len(msgs) >= 2:
                last_msg = msgs[-1].get("content", "").lower()
                # Suggest relevant files based on context
                if "config" in last_msg or "settings" in last_msg:
                    config_files = list(Path(".").glob("*.json")) + list(Path(".").glob("*.yaml")) + list(Path(".").glob("*.toml"))
                    if config_files:
                        self._show_toast(f"📁 Found {len(config_files)} config files", kind="info", duration=2.0)
                elif "test" in last_msg or "spec" in last_msg:
                    test_files = list(Path(".").glob("**/test_*.py")) + list(Path(".").glob("**/*_test.py"))
                    if test_files:
                        self._show_toast(f"📁 Found {len(test_files)} test files", kind="info", duration=2.0)
        except Exception as e:
            logger.debug("Context suggestions skipped: %s", e)

        # Feature 7: Auto-optimization based on usage
        try:
            # Enable compact mode if user prefers short messages
            short_msgs = self._user_patterns.get("short_msgs", 0)
            long_msgs = self._user_patterns.get("long_msgs", 0)
            if short_msgs > long_msgs * 2 and not self._compact_mode:
                self._compact_mode = True
                self._log_message("system", "📐 Auto-enabled compact mode based on your preferences")
            # Disable compact mode if user prefers long messages
            elif long_msgs > short_msgs * 2 and self._compact_mode:
                self._compact_mode = False
                self._log_message("system", "📐 Auto-disabled compact mode based on your preferences")
        except Exception as e:
            logger.debug("Auto-optimization skipped: %s", e)


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

    def on_error(self, event) -> None:
        """Log all uncaught exceptions from the TUI."""
        logger.exception("An uncaught error occurred in the TUI:")


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
    try:
        from core.project.scanner import ProjectScanner
        ctx = ProjectScanner().build_context_block()
    except Exception:
        ctx = None
    if ctx and not sd:
        st["_messages"].append({"role": "system", "content": f"[PROJECT CONTEXT]\n{ctx}", "_project_context": True})
    ins = project_state.load_project_config().get("project_instructions", "")
    if ins:
        st["_messages"].append({"role": "system", "content": f"[INSTRUCTIONS]\n{ins}"})
    WIDDXTUI(state=st, provider=provider, tool_defs=td).run()


if __name__ == "__main__":
    run_tui()

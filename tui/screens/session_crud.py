"""Session CRUD — manage saved chat sessions (list, load, rename, delete)."""

import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("widdx.tui.sessions")

from textual.screen import ModalScreen, Screen
from textual.widgets import Static, Input, Button, Label, RichLog
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from rich.table import Table
from rich.text import Text
from rich.panel import Panel


SESSION_DIR = Path.cwd().resolve()


def _find_sessions() -> list[dict]:
    sessions = []
    for pattern in ["chat_*.json", "chat_export_*.md"]:
        for f in sorted(SESSION_DIR.glob(pattern), reverse=True):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                sessions.append({
                    "path": str(f), "name": f.name, "size": f.stat().st_size,
                    "size_str": f"{f.stat().st_size // 1024}KB" if f.stat().st_size > 1024 else f"{f.stat().st_size}B",
                    "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                    "type": "json" if f.suffix == ".json" else "markdown",
                })
            except Exception as e:
                logger.debug("Session scan skip %s: %s", f.name, e)
    ws = SESSION_DIR / ".widdx" / "session.json"
    if ws.exists():
        try:
            data = json.loads(ws.read_text(encoding="utf-8"))
            sessions.insert(0, {
                "path": str(ws), "name": ".widdx/session.json (auto)",
                "size": ws.stat().st_size, "size_str": "auto",
                "modified": "current", "type": "json",
                "msg_count": len(data.get("messages", [])), "is_auto": True,
            })
        except Exception as e:
            logger.debug("Auto-session load failed: %s", e)
    return sessions


# ── Session List (full-screen) ────────────────

class SessionListScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("l", "load", "Load", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("r", "rename", "Rename", show=False),
        Binding("s", "save_now", "Save Now", show=False),
        Binding("e", "export_md", "Export MD", show=False),
    ]

    def __init__(self, state: dict | None = None, messages: list | None = None):
        super().__init__()
        self._state = state or {}
        self._messages = messages or []
        self._sessions: list[dict] = []

    def compose(self):
        yield Static("  📦  Session Manager", classes="list-title")
        yield Static("", classes="list-status")
        with Horizontal(classes="list-toolbar"):
            yield Button("  💾 Save Now (S)  ", id="sess-save", variant="primary")
            yield Button("  📤 Export MD (E)  ", id="sess-export")
            yield Button("  🔄 Refresh (R)  ", id="sess-refresh")
            yield Button("  🔙 Back (Esc)  ", id="sess-back")
        yield RichLog(highlight=True, markup=True, classes="list-content", id="sess-list")
        with Horizontal(classes="list-footer"):
            yield Static("  [dim][S]ave  [L]oad  [R]ename  [D]elete  [E]xport MD  [/]", classes="list-footer-text")

    def on_mount(self): self._load_sessions()

    def _load_sessions(self):
        log = self.query_one("#sess-list", RichLog)
        log.clear()
        self._sessions = _find_sessions()
        self.query_one(".list-status", Static).update(
            f"  [dim]{len(self._sessions)} session(s) ({sum(1 for s in self._sessions if s.get('is_auto'))} auto)[/]"
        )
        if not self._sessions:
            log.write(Panel(
                Text.from_markup("[dim]No saved sessions found.\n\nPress [bold #0891b2]S[/] to save the current session.[/]"),
                border_style="dim", padding=(2, 4),
            ))
            return
        table = Table(border_style="#0891b2", header_style="bold #818cf8", padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="bold #0891b2", width=34)
        table.add_column("Size", style="#64748b", width=8)
        table.add_column("Modified", style="#64748b", width=16)
        table.add_column("Actions", style="#f5a623", width=14)
        for i, s in enumerate(self._sessions, 1):
            tag = "🟢 " if s.get("is_auto") else ""
            table.add_row(str(i), f"{tag}{s['name']}", s["size_str"], s.get("modified", ""),
                          "[L]oad [D]el" if not s.get("is_auto") else "—")
        log.write(table)

    def action_go_back(self): self.dismiss()
    def action_refresh(self): self._load_sessions()

    def action_save_now(self):
        if not self._messages:
            self.query_one("#sess-list", RichLog).write(Panel(
                Text.from_markup("[bold #ef4444]No messages to save.[/]"), border_style="#ef4444", padding=(1, 2),
            ))
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SESSION_DIR / f"chat_{ts}.json"
        try:
            path.write_text(json.dumps({"messages": self._messages}, indent=2, ensure_ascii=False), encoding="utf-8")
            self._load_sessions()
        except (OSError, PermissionError) as e:
            self._show_error(f"Save failed: {e}")

    def action_export_md(self):
        if not self._messages: return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SESSION_DIR / f"chat_export_{ts}.md"
        try:
            lines = ["# WIDDX Chat Export\n"]
            for m in self._messages:
                lines.append(f"## {m.get('role', '?')}\n\n{(m.get('content') or '')}\n\n---\n")
            path.write_text("\n".join(lines), encoding="utf-8")
            self._load_sessions()
        except Exception as e:
            logger.debug("Export MD failed: %s", e)

    def action_load(self):
        non = [s for s in self._sessions if not s.get("is_auto")]
        if non: self.app.push_screen(SessionPickerScreen([s["name"] for s in non], "load"), self._on_picker_result)

    def action_rename(self):
        non = [s for s in self._sessions if not s.get("is_auto")]
        if non: self.app.push_screen(SessionPickerScreen([s["name"] for s in non], "rename"), self._on_picker_result)

    def action_delete(self):
        non = [s for s in self._sessions if not s.get("is_auto")]
        if non: self.app.push_screen(SessionPickerScreen([s["name"] for s in non], "delete"), self._on_picker_result)

    def _on_picker_result(self, result: tuple | None):
        if not result: return
        name, action = result
        path = SESSION_DIR / name
        if action == "load":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                msgs = data.get("messages", [])
                self._state["_messages"] = msgs
                self._state["turns"] = len(msgs)
                self.dismiss(("loaded", msgs))
            except Exception as e: self._show_error(f"Load failed: {e}")
        elif action == "rename":
            self.app.push_screen(SessionRenameScreen(name), self._on_rename_result)
        elif action == "delete":
            self.app.push_screen(SessionDeleteScreen(name), self._on_delete_result)

    def _on_rename_result(self, r):
        if r:
            old, new = r
            try:
                (SESSION_DIR / old).rename(SESSION_DIR / new)
                self._load_sessions()
            except Exception as e: self._show_error(f"Rename failed: {e}")

    def _on_delete_result(self, r):
        if r: self._load_sessions()

    def _show_error(self, msg):
        self.query_one("#sess-list", RichLog).write(Panel(
            Text.from_markup(f"[bold #ef4444]{msg}[/]"), border_style="#ef4444", padding=(1, 2),
        ))

    def on_button_pressed(self, event: Button.Pressed):
        return {
            "sess-save": self.action_save_now, "sess-export": self.action_export_md,
            "sess-refresh": self.action_refresh, "sess-back": self.action_go_back,
        }.get(event.button.id, lambda: None)()


# ── Session Picker (modal) ────────────────────

class SessionPickerScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, names: list[str], action: str):
        super().__init__()
        self._names = names
        self._action = action

    def compose(self):
        label = {"load": "Load", "rename": "Rename", "delete": "Delete"}.get(self._action, "Select")
        with Vertical(classes="picker-dialog"):
            yield Static(f"  {label} session", classes="picker-title")
            yield ScrollableContainer(classes="picker-list", id="sess-picker-list")
            with Horizontal(classes="picker-actions"):
                yield Button("  Cancel  ", id="sess-picker-cancel")

    def on_mount(self):
        c = self.query_one("#sess-picker-list", ScrollableContainer)
        for name in self._names[:30]:
            c.mount(Button(f"  {name}", id=f"spick-{name}", classes="pick-btn"))

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "sess-picker-cancel": self.dismiss(None)
        elif bid and bid.startswith("spick-"):
            self.dismiss((bid[6:], self._action))


# ── Session Rename (modal) ────────────────────

class SessionRenameScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, old_name: str):
        super().__init__()
        self._old_name = old_name

    def compose(self):
        with Vertical(id="sess-rename-dialog", classes="dialog-box"):
            yield Static("  ✏️  Rename Session", classes="dialog-title")
            yield Label("Current name:")
            yield Static(f"  [dim]{self._old_name}[/]", classes="rename-old")
            yield Label("New name:")
            yield Input(value=self._old_name, id="sess-rename-input", placeholder="chat_20250101_120000.json")
            with Horizontal(classes="dialog-actions"):
                yield Button("  Rename  ", id="sess-rename-do", variant="primary")
                yield Button("  Cancel  ", id="sess-rename-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "sess-rename-do":
            new = self.query_one("#sess-rename-input", Input).value.strip()
            if new and new != self._old_name:
                self.dismiss((self._old_name, new))
        elif event.button.id == "sess-rename-cancel":
            self.dismiss(None)


# ── Session Delete Confirmation (modal) ───────

class SessionDeleteScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel"), Binding("y", "confirm", "Yes", show=False)]

    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def compose(self):
        with Vertical(id="sess-delete-dialog", classes="dialog-box delete-dialog"):
            yield Static("  ⚠️  Delete Session", classes="dialog-title delete-title")
            yield Static(f"\n  Delete:\n\n  [bold #ef4444]{self._name}[/]\n\n  This cannot be undone.\n", classes="delete-msg")
            with Horizontal(classes="dialog-actions-center"):
                yield Button("  ✅ Yes, Delete  ", id="sess-delete-yes", variant="error")
                yield Button("  Cancel  ", id="sess-delete-no")

    def action_confirm(self):
        path = SESSION_DIR / self._name
        try:
            if path.exists(): path.unlink()
            self.dismiss(True)
        except Exception as e:
            logger.debug("Session delete failed: %s", e)
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "sess-delete-yes": self.action_confirm()
        else: self.dismiss(None)

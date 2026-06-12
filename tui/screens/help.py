"""Help screen modal — commands, shortcuts, and navigation reference."""

from textual.screen import ModalScreen
from textual.widgets import Static, RichLog, Button, Label
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from rich.table import Table
from rich.text import Text
from rich.panel import Panel


class HelpScreen(ModalScreen):
    """Shows available commands and shortcuts in a centered modal dialog."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Dismiss"),
    ]

    CATEGORIES = {
        "💬 Commands": [
            ("/help", "This help screen"),
            ("/clear", "Clear chat history"),
            ("/tools", "Show available tools"),
            ("/skills", "List & toggle skills"),
            ("/history", "Review chat history"),
            ("/version", "Show version"),
        ],
        "📦 Sessions & Memory": [
            ("/save", "Save session as JSON"),
            ("/export", "Export as Markdown"),
            ("/memories", "Manage saved memories"),
            ("/remember <msg>", "Save a quick memory"),
        ],
        "⚙️ Settings": [
            ("/settings", "Open settings panel"),
            ("/model", "Change AI model"),
            ("/provider", "Switch provider"),
            ("/doctor", "Run system diagnostics"),
        ],
        "⌨️  Shortcuts": [
            ("Ctrl+Q", "Quit application"),
            ("Ctrl+L", "Clear chat"),
            ("Ctrl+P", "Open this help"),
            ("Esc", "Close modals / Back"),
            ("!name", "Activate skill  (!off to stop)"),
        ],
        "🧭 Navigation": [
            ("Sidebar buttons", "Chat / Tools / Skills / History"),
            ("Sidebar buttons", "Memories / Sessions / Settings"),
            ("Sidebar buttons", "Doctor / Save / Export / Clear"),
        ],
    }

    def compose(self):
        with Vertical(id="help-dialog", classes="dialog-box"):
            yield Static("❓  Help & Reference", classes="dialog-title")
            yield Label("All available commands grouped by category:", classes="dialog-subtitle")
            yield RichLog(highlight=True, markup=True, classes="dialog-body")
            with Horizontal(classes="dialog-actions"):
                yield Button("  Close (Esc)  ", id="btn-close", variant="primary")

    def on_mount(self):
        log = self.query_one(RichLog)
        log.write(Panel(
            Text.from_markup(
                "[bold #818cf8]◈  WIDDX Terminal AI[/]\n"
                "[dim]Type /command or click sidebar buttons[/]"
            ),
            border_style="#6366f1",
            padding=(1, 2),
        ))
        for category, cmds in self.CATEGORIES.items():
            log.write("")
            table = Table(
                title=category,
                border_style="#0891b2",
                header_style="bold #818cf8",
                title_style="bold #64748b",
                padding=(0, 2),
                box=None,
            )
            table.add_column("Command", style="bold #0891b2", width=18)
            table.add_column("Description", style="#cbd5e1")
            for cmd, desc in cmds:
                table.add_row(cmd, desc)
            log.write(table)
        log.write("")
        log.write(Panel(
            Text.from_markup(
                "[dim]Press [bold #0891b2]Esc[/] or [bold #0891b2]q[/] to close  |  "
                "[/][dim]Type any command in the input bar[/]"
            ),
            border_style="dim",
            padding=(0, 1),
        ))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-close":
            self.dismiss()

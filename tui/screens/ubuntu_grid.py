"""Ubuntu-style Application Grid Launcher — شبكة أيقونات على غرار GNOME."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Select, Static
from textual.containers import Horizontal


class UbuntuGrid(Screen):
    """شبكة أيقونات على غرار Ubuntu/GNOME — تفتح عند النقر على زر الشبكة."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("ctrl+q", "app.quit", "Quit", show=False),
    ]

    def __init__(
        self,
        nav_buttons: list | None = None,
        act_buttons: list | None = None,
        help_buttons: list | None = None,
    ):
        super().__init__()
        self._grid_ready = False
        self._nav_buttons = nav_buttons or []
        self._act_buttons = act_buttons or []
        self._help_buttons = help_buttons or []

    def compose(self) -> ComposeResult:
        yield Static(id="grid-overlay")
        yield Static("[bold #6366f1]◈  W I D D X  C O R T E X  ◈[/]", id="grid-title")
        yield Static("", id="grid-search-hint")

        # Provider + Branch inline
        yield Horizontal(
            Static("Provider:", classes="grid-inline-label"),
            Select(options=[
                ("🌐 OpenCode Zen", "opencode-zen"),
                ("🔵 DeepSeek", "deepseek"),
                ("⚪ OpenAI", "openai"),
                ("🟠 Ollama", "ollama"),
                ("📦 GGUF (Local)", "gguf"),
            ], id="grid-provider", classes="grid-inline-select"),
            Static("  Branch:", classes="grid-inline-label"),
            Select(options=[], id="grid-branch", classes="grid-inline-select"),
            id="grid-prov-branch",
        )

        # ── Navigate section ──
        yield Static("NAVIGATE", classes="grid-section-title")
        with Horizontal(id="grid-navigate", classes="grid-row"):
            for _, icon, label, action, _ in self._nav_buttons:
                yield Button(
                    f"{icon}\n{label}",
                    id=f"g{action}",
                    classes="grid-icon-btn",
                )

        # ── Actions section ──
        yield Static("ACTIONS", classes="grid-section-title")
        with Horizontal(id="grid-actions", classes="grid-row"):
            for _, icon, label, action, _ in self._act_buttons:
                yield Button(
                    f"{icon}\n{label}",
                    id=f"g{action}",
                    classes="grid-icon-btn",
                )

        # ── Help section ──
        yield Static("", classes="grid-section-title")
        with Horizontal(id="grid-help", classes="grid-row"):
            for _, icon, label, action, _ in self._help_buttons:
                yield Button(
                    f"{icon}\n{label}",
                    id=f"g{action}",
                    classes="grid-icon-btn",
                )

        # ── Footer ──
        yield Static("", id="grid-footer")

    def on_mount(self) -> None:
        """Populate branch selector."""
        from core.project.state import list_branches, get_current_branch
        branch_sel = self.query_one("#grid-branch", Select)
        current = get_current_branch()
        branches = list_branches()
        branch_sel.set_options([(f"🌿 {b}", b) for b in branches])
        if current in branches:
            branch_sel.value = current
        self._grid_ready = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("g"):
            action = bid[1:]
            self.dismiss(action.lower())

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider/branch switch from grid."""
        if not self._grid_ready:
            return
        value = event.value
        if value is None or value == Select.BLANK:
            return
        sid = event.select.id or ""
        if sid == "grid-provider":
            self.dismiss(f"provider:{value}")
        elif sid == "grid-branch":
            self.dismiss(f"branch:{value}")

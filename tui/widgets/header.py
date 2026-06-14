"""Header widget for WIDDX Cortex TUI."""
from textual.widgets import Static, Button, Select
from textual.containers import Horizontal
from core.project.state import list_branches, get_current_branch
import logging

logger = logging.getLogger("widdx.tui")


class HeaderWidget(Horizontal):
    """Custom header with grid button, title, provider selector, and branch selector."""

    def __init__(self):
        super().__init__()
        self.id = "header"

    def compose(self):
        # Section 1: Logo + Menu button
        with Horizontal(classes="header-left-section"):
            yield Button("☰", id="btn-grid", classes="header-btn")
            yield Static("◈ WIDDX", classes="header-logo")
        
        # Section 2: Info area
        yield Static(id="header-info", classes="header-info")
        
        # Section 3: Selectors
        with Horizontal(classes="header-right-section"):
            yield Static("Provider:", classes="header-selector-label")
            yield Select(
                options=[
                    ("🌐 OpenCode Zen", "opencode-zen"),
                    ("🔵 DeepSeek", "deepseek"),
                    ("⚪ OpenAI", "openai"),
                    ("🟠 Ollama", "ollama"),
                    ("📦 GGUF", "gguf"),
                ],
                id="header-provider",
                classes="header-selector"
            )
            yield Static("Branch:", classes="header-selector-label")
            yield Select(
                options=[],
                id="header-branch",
                classes="header-selector"
            )

    def initialize_provider(self, provider_name: str):
        """Initialize provider selector value."""
        try:
            provider_sel = self.query_one("#header-provider", Select)
            with provider_sel.prevent(Select.Changed):
                provider_sel.value = provider_name
        except Exception as e:
            logger.exception(f"[HeaderWidget] Error initializing provider selector: {e}")

    def on_mount(self):
        """Populate branch selector on mount."""
        self._populate_header_selectors()

    def _populate_header_selectors(self):
        """Populate provider and branch selectors."""
        try:
            # Branch selector
            branch_sel = self.query_one("#header-branch", Select)
            current_branch = get_current_branch()
            branches = list_branches()
            branch_sel.set_options([(f"🌿 {b}", b) for b in branches])
            if current_branch in branches:
                with branch_sel.prevent(Select.Changed):
                    branch_sel.value = current_branch
            logger.info("[HeaderWidget] Header selectors populated successfully")
        except Exception as e:
            logger.exception(f"[HeaderWidget] Error populating header selectors: {e}")

    def update_provider(self, new_provider: str):
        """Update provider selector value without triggering event."""
        try:
            provider_sel = self.query_one("#header-provider", Select)
            with provider_sel.prevent(Select.Changed):
                provider_sel.value = new_provider
        except Exception as e:
            logger.exception(f"[HeaderWidget] Error updating provider selector: {e}")

    def update_branch(self, new_branch: str):
        """Update branch selector value without triggering event."""
        try:
            branch_sel = self.query_one("#header-branch", Select)
            with branch_sel.prevent(Select.Changed):
                branch_sel.value = new_branch
        except Exception as e:
            logger.exception(f"[HeaderWidget] Error updating branch selector: {e}")

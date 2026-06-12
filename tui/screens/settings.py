"""Settings screen — provider/model/key/temperature/system prompt."""

from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button, Label, Select
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding

from core import config
from core.config.keychain import set_key, forget_key, has_key
from core.providers.providers import fetch_free_models, fetch_ollama_models


class SettingsScreen(ModalScreen):
    """Provider, model, API key, temperature, and system prompt config."""

    BINDINGS = [Binding("escape", "dismiss", "Back")]

    PROVIDERS = [
        ("opencode-zen", "OpenCode Zen (free)"),
        ("deepseek", "DeepSeek"),
        ("openai", "OpenAI"),
        ("ollama", "Ollama (local)"),
    ]

    _FALLBACK_MODELS = {
        "opencode-zen": ["deepseek-v4-flash-free", "gemini-3.5-flash", "claude-sonnet-4-6", "gpt-5.4-mini"],
        "deepseek": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-5.4", "gpt-5.4-mini"],
        "ollama": ["llama3", "llama3.1", "mistral", "codellama"],
    }

    @staticmethod
    def _default_base_url_for(provider: str) -> str:
        return {
            "opencode-zen": "https://opencode.ai/zen/v1",
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434",
        }.get(provider, "")

    def _get_models_for(self, provider: str) -> list[str]:
        if provider == "opencode-zen":
            try:
                free = fetch_free_models()
                if free:
                    return free
            except Exception:
                pass
        if provider == "ollama":
            try:
                installed = fetch_ollama_models(
                    base_url=self._current_base_url, force_refresh=True,
                )
                if installed:
                    return [m["name"] for m in installed]
            except Exception:
                pass
        return list(self._FALLBACK_MODELS.get(provider, ["custom"]))

    def __init__(self):
        super().__init__()
        p = config.load().get("provider", {})
        self._current_provider = p.get("name", "opencode-zen")
        self._current_model = p.get("model", "deepseek-v4-flash-free")
        self._current_base_url = p.get("base_url", self._default_base_url_for(self._current_provider))

    def compose(self):
        with Vertical(id="settings-dialog", classes="dialog-box"):
            yield Static("⚙️  Settings", classes="dialog-title")
            with ScrollableContainer(classes="dialog-form"):
                yield Label("Provider:")
                yield Select(
                    options=[(plabel, pid) for pid, plabel in self.PROVIDERS],
                    value=self._current_provider,
                    id="provider-select"
                )
                yield Label("Model:")
                yield Select(options=[], id="model-select")
                yield Label("Temperature:")
                yield Input(value=str(config.load().get("temperature", 0.7)), id="temp-input")
                yield Label("Base URL:")
                yield Input(value=self._current_base_url, id="base-url-input", placeholder="https://api.example.com/v1")
                yield Label("API Key:")
                yield Input(id="api-key-input", password=True, placeholder="Enter API key...")
                yield Label("API Key Status:")
                with Horizontal(id="key-status-row"):
                    yield Static("", id="key-status")
                    yield Button("Forget Key", id="btn-forget", variant="error")
                yield Label("System Prompt:")
                yield Input(value=config.load().get("system_prompt", ""), id="sysprompt-input")
                yield Static()
                from core.config import get_config_path
                yield Label(f"Config: {get_config_path()}", classes="config-path-hint")
            with Horizontal(classes="dialog-actions"):
                yield Button("  💾 Save  ", id="btn-save", variant="primary")
                yield Button("  Cancel  ", id="btn-close")

    def on_mount(self):
        self._update_model_list()
        self._update_key_status()

    def _update_model_list(self):
        models = self._get_models_for(self._current_provider)
        select = self.query_one("#model-select", Select)
        select.set_options([(m, m) for m in models])
        if self._current_model in models:
            select.value = self._current_model
        elif models:
            select.value = models[0]

    def _update_key_status(self):
        status = self.query_one("#key-status", Static)
        forget_btn = self.query_one("#btn-forget", Button)
        if has_key(self._current_provider):
            status.update("✓ Key is set")
            forget_btn.display = True
        else:
            status.update("○ Not set")
            forget_btn.display = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "provider-select":
            provider = event.value
            if provider != self._current_provider:
                self._current_provider = provider
                self._current_base_url = self._default_base_url_for(provider)
                self.query_one("#base-url-input", Input).value = self._current_base_url
                self._update_key_status()
                self._update_model_list()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-close":
            self.dismiss()
            return
        if bid == "btn-forget":
            forget_key(self._current_provider)
            self._update_key_status()
            return
        if bid == "btn-save":
            api = self.query_one("#api-key-input", Input).value.strip()
            if api:
                set_key(self._current_provider, api)
            model_val = self.query_one("#model-select", Select).value
            if model_val is None or model_val == Select.BLANK:
                model = self._current_model
            else:
                model = str(model_val)
            try:
                temp = float(self.query_one("#temp-input", Input).value.strip() or "0.7")
            except ValueError:
                temp = 0.7
            sp = self.query_one("#sysprompt-input", Input).value.strip()
            bu = self.query_one("#base-url-input", Input).value.strip() or self._default_base_url_for(self._current_provider)
            cfg = config.load()
            cfg["provider"] = {"name": self._current_provider, "model": model, "base_url": bu}
            cfg["temperature"] = temp
            if sp:
                cfg["system_prompt"] = sp
            config.save(cfg)
            self.dismiss({"provider": self._current_provider, "model": model, "temperature": temp})

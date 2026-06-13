"""Full-screen settings — configure all providers, switch primary, import GGUF."""

from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, Select, Switch
from textual.containers import Vertical, Horizontal, ScrollableContainer, Container
from textual.binding import Binding
from pathlib import Path

from core import config
from core.config.keychain import set_key, forget_key, has_key
from core.providers.providers import (
    fetch_free_models, fetch_ollama_models,
    _TOOL_CAPABLE_PATTERNS, _REASONING_PATTERNS,
)


# ── Provider definitions ────────────────────────────────
PROVIDER_LIST = [
    {
        "id": "opencode-zen",
        "label": "OpenCode Zen",
        "desc": "Free tier — proxy with rotating models & IPs",
        "default_url": "https://opencode.ai/zen/v1",
        "default_models": ["deepseek-v4-flash-free", "gemini-3.5-flash", "claude-sonnet-4-6"],
        "needs_key": False,
    },
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "desc": "Official API — requires API key from platform.deepseek.com",
        "default_url": "https://api.deepseek.com",
        "default_models": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
        "needs_key": True,
    },
    {
        "id": "openai",
        "label": "OpenAI",
        "desc": "Official API — requires API key from platform.openai.com",
        "default_url": "https://api.openai.com/v1",
        "default_models": ["gpt-4o", "gpt-4o-mini", "gpt-5.4", "gpt-5.4-mini"],
        "needs_key": True,
    },
    {
        "id": "ollama",
        "label": "Ollama",
        "desc": "Local models — run ollama serve first",
        "default_url": "http://localhost:11434",
        "default_models": ["llama3.2", "llama3.1", "mistral", "codellama"],
        "needs_key": False,
    },
]


def _guess_ollama_caps(model_name: str) -> str:
    """Capability badges for Ollama model (name-based)."""
    lower = model_name.lower()
    badges = []
    if any(pat in lower for pat in _TOOL_CAPABLE_PATTERNS):
        badges.append("[bold #00c896]🧰[/]")
    else:
        badges.append("[dim]⚠[/]")
    if any(pat in lower for pat in _REASONING_PATTERNS) or "think" in lower:
        badges.append("[bold #f5a623]🧠[/]")
    return " ".join(badges)


def _fmt(key: str) -> str:
    """Format a key for display — show first 4 and last 4 chars."""
    if not key or key == "public":
        return key or ""
    if len(key) <= 8:
        return "•" * len(key)
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


class SettingsScreen(Screen):
    """Full-screen provider configuration."""

    BINDINGS = [Binding("escape", "dismiss", "Back")]

    def __init__(self):
        super().__init__()
        cfg = config.load()
        p = cfg.get("provider", {})
        self._active_provider = p.get("name", "opencode-zen")
        self._saved = False
        # Cache current model from config so it can be pre-selected
        self._current_model = p.get("model", "")
        # Cache saved URL for active provider
        self._current_url = p.get("base_url", "")

    def compose(self):
        # ── Header (docked top) ─────────────────────────
        yield Static("  ⚙️  Settings  —  Configure Providers", id="settings-header")

        # ── Scrollable content ──────────────────────────
        with ScrollableContainer(id="settings-body"):
            # Active provider selector
            yield Label("Active Provider:")
            yield Select(
                options=[(pi["label"], pi["id"]) for pi in PROVIDER_LIST],
                value=self._active_provider,
                id="active-provider",
            )
            yield Static("", id="active-desc", classes="hint")

            # Provider sections
            for pi in PROVIDER_LIST:
                pid = pi["id"]
                yield Static(f"── {pi['label']} ──", classes="section-title")
                yield Static(pi["desc"], classes="hint")

                yield Label("Model:")
                with Horizontal(id=f"model-row-{pid}"):
                    yield Select(options=[], id=f"model-{pid}")
                    yield Button("↻", id=f"btn-refresh-{pid}", tooltip="Refresh model list")
                yield Static("", id=f"model-status-{pid}", classes="hint")

                yield Label("Base URL:")
                yield Input(
                    value=pi["default_url"],
                    id=f"url-{pid}",
                    placeholder="https://api.example.com/v1",
                )

                yield Label("API Key:")
                with Horizontal(id=f"key-row-{pid}"):
                    yield Input(
                        id=f"key-{pid}",
                        password=True,
                        placeholder="Enter API key..." if pi["needs_key"] else "public (no key needed)",
                    )
                    yield Button("Set", id=f"btn-key-{pid}")
                    yield Button("Forget", id=f"btn-forget-{pid}", variant="error")
                yield Static("", id=f"key-status-{pid}", classes="hint")

                # Thinking toggle (only for DeepSeek)
                if pid == "deepseek":
                    yield Label("Reasoning (thinking):")
                    yield Switch(value=config.load().get("thinking", True), id="thinking-switch")
                    yield Static("Enable deep thinking/reasoning mode", classes="hint")

                # Ollama capabilities
                if pid == "ollama":
                    yield Static("", id="ollama-caps", classes="hint")

                yield Static("")  # spacer

            # ── GGUF Import section ─────────────────────
            yield Static("── 📦 GGUF Model Import ──", classes="section-title")
            yield Label("GGUF file path:")
            with Horizontal(id="gguf-import-row"):
                yield Input(
                    id="gguf-path",
                    placeholder="E:\\Models\\...\\model.gguf",
                )
                yield Button("📥 Import", id="btn-gguf-import")
            yield Button("📋 List imported models", id="btn-gguf-list")
            yield Static("", id="gguf-status", classes="hint")

            yield Static("")  # bottom spacer

        # ── Footer (docked bottom) ──────────────────────
        with Horizontal(id="settings-footer"):
            from core.config import get_config_path
            yield Static(f"Config: {get_config_path()}", id="footer-path")
            yield Button("  💾 Save & Switch  ", id="btn-save", variant="primary")
            yield Button("  Cancel  ", id="btn-close")

    def on_mount(self):
        self._refresh_all()

    # ── Refresh ─────────────────────────────────────────

    def _refresh_all(self):
        """Refresh all provider sections from current config."""
        cfg = config.load()
        prov_cfg = cfg.get("provider", {})

        for pi in PROVIDER_LIST:
            pid = pi["id"]
            self._fill_models(pid)
            self._fill_key_status(pid)

            # Fill current values from config
            if pid == prov_cfg.get("name", ""):
                url = prov_cfg.get("base_url", pi["default_url"])
                model = prov_cfg.get("model", pi["default_models"][0])
            else:
                url = pi["default_url"]
                model = pi["default_models"][0]

            self.query_one(f"#url-{pid}", Input).value = url
            select = self.query_one(f"#model-{pid}", Select)
            try:
                select.value = model
            except Exception:
                pass  # model not in list — keep default

        # Active provider description
        self._update_active_desc()
        # Ollama caps
        self._update_ollama_caps()

    def _update_active_desc(self):
        for pi in PROVIDER_LIST:
            if pi["id"] == self._active_provider:
                self.query_one("#active-desc", Static).update(f"[dim]{pi['desc']}[/]")
                break

    def _fill_models(self, pid: str, force_refresh: bool = False):
        """Populate the model Select for a given provider (sync — uses defaults first)."""
        select = self.query_one(f"#model-{pid}", Select)
        pi = next((p for p in PROVIDER_LIST if p["id"] == pid), None)

        # Always show defaults immediately so Save works even before fetch completes
        if pid in ("deepseek", "openai"):
            models = list(pi["default_models"]) if pi else []
        elif pid == "opencode-zen":
            # Use cached list if available; schedule a background fetch
            try:
                models = fetch_free_models.__wrapped__() if hasattr(fetch_free_models, "__wrapped__") else []
            except Exception:
                models = []
            if not models and pi:
                models = list(pi["default_models"])
            # Kick off background refresh
            self._fetch_models_bg(pid, force_refresh)
        elif pid == "ollama":
            url = self.query_one(f"#url-{pid}", Input).value
            try:
                installed = fetch_ollama_models(base_url=url, force_refresh=False)
                models = [m["name"] for m in installed]
            except Exception:
                models = []
            if not models and pi:
                models = list(pi["default_models"])
            if force_refresh:
                self._fetch_models_bg(pid, True)
        else:
            models = []

        if not models and pi:
            models = list(pi["default_models"])

        if models:
            if pid == "ollama":
                opts = [(f"{m}  {_guess_ollama_caps(m)}", m) if _guess_ollama_caps(m) else (m, m) for m in models]
            else:
                opts = [(m, m) for m in models]
            select.set_options(opts)
            # Pre-select current model if it matches
            cfg_model = self._current_model if pid == self._active_provider else ""
            matched = False
            if cfg_model:
                for _, val in opts:
                    if val == cfg_model:
                        select.value = val
                        matched = True
                        break
            if not matched and opts:
                select.value = opts[0][1]

    def _fetch_models_bg(self, pid: str, force_refresh: bool = False):
        """Background worker: fetch real model list and update Select."""
        import threading

        def _run():
            pi = next((p for p in PROVIDER_LIST if p["id"] == pid), None)
            try:
                self.call_from_thread(
                    lambda: self.query_one(f"#model-status-{pid}", Static).update("[dim]Fetching models...[/]")
                )
            except Exception:
                pass

            try:
                if pid == "opencode-zen":
                    models = fetch_free_models()
                elif pid == "ollama":
                    url = self.query_one(f"#url-{pid}", Input).value
                    installed = fetch_ollama_models(base_url=url, force_refresh=force_refresh)
                    models = [m["name"] for m in installed]
                else:
                    models = []
            except Exception:
                models = []

            if not models and pi:
                models = list(pi["default_models"])

            def _apply():
                try:
                    select = self.query_one(f"#model-{pid}", Select)
                    if models:
                        if pid == "ollama":
                            opts = [(f"{m}  {_guess_ollama_caps(m)}", m) if _guess_ollama_caps(m) else (m, m) for m in models]
                        else:
                            opts = [(m, m) for m in models]
                        select.set_options(opts)
                        cfg_model = self._current_model if pid == self._active_provider else ""
                        matched = False
                        if cfg_model:
                            for _, val in opts:
                                if val == cfg_model:
                                    select.value = val
                                    matched = True
                                    break
                        if not matched and opts:
                            select.value = opts[0][1]
                    status = self.query_one(f"#model-status-{pid}", Static)
                    status.update(f"[dim]{len(models)} models[/]")
                except Exception:
                    pass

            self.call_from_thread(_apply)

        threading.Thread(target=_run, daemon=True).start()

    def _fill_key_status(self, pid: str):
        """Update key status display for a provider."""
        status = self.query_one(f"#key-status-{pid}", Static)
        forget_btn = self.query_one(f"#btn-forget-{pid}", Button)
        key_input = self.query_one(f"#key-{pid}", Input)

        pi = next((p for p in PROVIDER_LIST if p["id"] == pid), None)
        if has_key(pid):
            status.update("[bold #10b981]✓ Key is set[/]")
            forget_btn.display = True
            # Show masked key
            from core.config.keychain import get_key
            k = get_key(pid) or ""
            key_input.value = _fmt(k) if k else ""
        else:
            if pi and pi["needs_key"]:
                status.update("[bold #e74c3c]⚠ No key — required for this provider[/]")
            else:
                status.update("[dim]○ No key set[/]")
            forget_btn.display = False
            key_input.value = ""

    def _update_ollama_caps(self):
        """Update Ollama model capabilities display."""
        try:
            caps_widget = self.query_one("#ollama-caps", Static)
            model_select = self.query_one("#model-ollama", Select)
            if model_select.value and model_select.value != Select.BLANK:
                caps = _guess_ollama_caps(str(model_select.value))
                if caps:
                    caps_widget.update(f"Capabilities: {caps}")
                else:
                    caps_widget.update("[dim]Capabilities: auto-detected on first use[/]")
        except Exception:
            pass

    # ── Events ──────────────────────────────────────────

    def on_select_changed(self, event: Select.Changed):
        sid = event.select.id or ""
        if sid == "active-provider":
            if event.value and event.value != Select.BLANK:
                self._active_provider = str(event.value)
                self._update_active_desc()
        elif sid.startswith("model-"):
            pid = sid.replace("model-", "")
            if pid == "ollama":
                self._update_ollama_caps()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""

        # ── Key + Refresh buttons ────────────────────
        for pi in PROVIDER_LIST:
            pid = pi["id"]
            if bid == f"btn-key-{pid}":
                k = self.query_one(f"#key-{pid}", Input).value.strip()
                if k:
                    set_key(pid, k)
                    self._fill_key_status(pid)
                return
            if bid == f"btn-forget-{pid}":
                forget_key(pid)
                self._fill_key_status(pid)
                return
            if bid == f"btn-refresh-{pid}":
                self._fill_models(pid, force_refresh=True)
                return

        # ── GGUF buttons ────────────────────────────
        if bid == "btn-gguf-import":
            self._do_gguf_import()
            return
        if bid == "btn-gguf-list":
            self._do_gguf_list()
            return

        # ── Save ─────────────────────────────────────
        if bid == "btn-save":
            self._do_save()
            return

        # ── Cancel ───────────────────────────────────
        if bid == "btn-close":
            self.dismiss()
            return

    # ── Save logic ─────────────────────────────────────

    def _do_save(self):
        """Collect all settings and save to config.json."""
        try:
            new_cfg = config.load()

            # Collect provider configs
            all_providers: dict[str, dict] = {}
            for pi in PROVIDER_LIST:
                pid = pi["id"]

                # Guard against Select.BLANK — fall back to first default
                try:
                    raw_model = self.query_one(f"#model-{pid}", Select).value
                    if raw_model is None or str(raw_model) in ("", "BLANK") or raw_model == Select.BLANK:
                        model = pi["default_models"][0]
                    else:
                        model = str(raw_model)
                except Exception:
                    model = pi["default_models"][0]

                try:
                    url = self.query_one(f"#url-{pid}", Input).value.strip() or pi["default_url"]
                except Exception:
                    url = pi["default_url"]

                # Include API key so switching providers preserves keys in config
                try:
                    from core.config.keychain import get_key
                    key = get_key(pid) or ("public" if not pi["needs_key"] else "")
                except Exception:
                    key = "public" if not pi["needs_key"] else ""

                all_providers[pid] = {"model": model, "base_url": url, "api_key": key}

            # Set the active provider
            active = self._active_provider
            ap = all_providers.get(active, {})
            pi_active = next((p for p in PROVIDER_LIST if p["id"] == active), {})
            new_cfg["provider"] = {
                "name": active,
                "model": ap.get("model") or (pi_active.get("default_models", ["deepseek-v4-flash-free"])[0]),
                "base_url": ap.get("base_url") or pi_active.get("default_url", "https://opencode.ai/zen/v1"),
                "api_key": ap.get("api_key", "public"),
            }

            # Temperature
            new_cfg["temperature"] = config.load().get("temperature", 0.7)

            # Thinking
            try:
                new_cfg["thinking"] = self.query_one("#thinking-switch", Switch).value
            except Exception:
                pass

            # Store all provider configs for future switching
            new_cfg["all_providers"] = all_providers

            config.save(new_cfg)
            self._saved = True

            final_model = new_cfg["provider"]["model"]
            self.dismiss({
                "provider": active,
                "model": final_model,
                "base_url": new_cfg["provider"]["base_url"],
                "api_key": new_cfg["provider"]["api_key"],
                "all_providers": all_providers,
            })
        except Exception as e:
            try:
                self.query_one("#gguf-status", Static).update(f"[bold #e74c3c]❌ Save failed: {e}[/]")
            except Exception:
                pass

    # ── GGUF ────────────────────────────────────────────

    def _do_gguf_import(self):
        path = self.query_one("#gguf-path", Input).value.strip()
        status = self.query_one("#gguf-status", Static)
        if not path:
            status.update("[bold #e74c3c]❌ Please enter a .gguf file path[/]")
            return
        if not Path(path).exists():
            status.update(f"[bold #e74c3c]❌ File not found:[/] {path}")
            return
        if Path(path).is_dir():
            status.update(f"[bold #e74c3c]❌ This is a directory, not a .gguf file[/]")
            return

        status.update(f"[dim]Reading {Path(path).name} ...[/]")
        try:
            from core.providers.gguf import import_gguf, suggest_model_name, read_gguf_metadata
            meta = read_gguf_metadata(path)
            name = suggest_model_name(path, meta)
            status.update(f"[dim]Importing as '{name}' ... (may take minutes)[/]")

            # Run in thread
            import asyncio
            asyncio.create_task(self._async_import(path, name, meta, status))
        except Exception as e:
            status.update(f"[bold #e74c3c]❌ Error: {e}[/]")

    async def _async_import(self, path, name, meta, status):
        import asyncio
        from core.providers.gguf import import_gguf, log_import
        try:
            result = await asyncio.to_thread(import_gguf, path, name)
            if result["success"]:
                log_import(result)
                fetch_ollama_models(force_refresh=True)
                self._fill_models("ollama")
                self.query_one("#gguf-path", Input).value = ""
                status.update(
                    f"[bold #00c896]✅ Imported: {result['model_name']}[/] "
                    f"({meta.get('architecture', '?')})"
                )
            else:
                status.update(f"[bold #e74c3c]❌ {result.get('error', 'unknown')}[/]")
        except Exception as e:
            status.update(f"[bold #e74c3c]❌ {e}[/]")

    def _do_gguf_list(self):
        status = self.query_one("#gguf-status", Static)
        try:
            from core.providers.gguf import list_imports
            from datetime import datetime
            imports = list_imports()
            if not imports:
                status.update("[dim]No GGUF models imported yet.[/]")
                return
            lines = ["[bold]Imported GGUF Models:[/]"]
            for e in imports:
                meta = e.get("metadata", {})
                ds = datetime.fromtimestamp(e.get("imported_at", 0)).strftime("%Y-%m-%d")
                lines.append(f"  • [bold]{e['model_name']}[/] ({meta.get('architecture','?')}) [dim]{ds}[/]")
            status.update("\n".join(lines))
        except Exception as e:
            status.update(f"[bold #e74c3c]❌ {e}[/]")

    # ── Dismiss cleanup ─────────────────────────────────

    def action_dismiss(self):
        self.dismiss()

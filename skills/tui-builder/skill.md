---
name: tui-builder
description: Build professional Textual TUI interfaces for WIDDX — complete, fast, error-free
icon: 🖥️
---

# TUI Builder — Textual Framework Skill for WIDDX

## Architecture Overview

```
WIDDXApp (textual.app.App)
  ├── MODES:
  │   ├── "chat"      → ChatScreen (default)
  │   ├── "settings"  → SettingsScreen
  │   ├── "skills"    → SkillsScreen
  │   ├── "memories"  → MemoriesScreen
  │   ├── "help"      → HelpScreen
  │   └── "tools"     → ToolsScreen
  │
  ├── SCREENS (modals):
  │   ├── ConfirmDialog  → ModalScreen[bool]
  │   └── ProxyScreen    → ModalScreen
  │
  └── Workers:
      ├── run_chat(prompt)         → thread worker (sync backend)
      ├── stream_chat(prompt)      → async worker (streaming)
      └── load_history()           → thread worker
```

## Core Patterns

### 1. App Class Pattern

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual import work

class WIDDXApp(App):
    CSS_PATH = "widdux.tcss"
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+d", "toggle_dark", "Dark mode"),
        Binding("ctrl+s", "show_settings", "Settings"),
        Binding("ctrl+h", "show_help", "Help"),
        Binding("ctrl+m", "show_memories", "Memories"),
        Binding("ctrl+t", "show_tools", "Tools"),
        Binding("ctrl+k", "show_skills", "Skills"),
    ]
    
    MODES = {
        "chat": ChatScreen,
        "settings": SettingsScreen,
        "help": HelpScreen,
        "memories": MemoriesScreen,
        "tools": ToolsScreen,
        "skills": SkillsScreen,
    }
    
    DEFAULT_MODE = "chat"

    def on_mount(self) -> None:
        self.switch_mode("chat")
```

### 2. Chat Screen Pattern

```python
class ChatScreen(Screen):
    """Main chat interface."""
    
    BINDINGS = [
        Binding("escape", "app.switch_mode('chat')", "Back to chat"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ChatLog(id="chat-log")           # RichLog-based
        yield Input(placeholder="Type a message...", id="chat-input")
        yield Footer()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if not event.value.strip():
            return
        self.add_user_message(event.value)
        self.query_one(Input).clear()
        self.run_chat(event.value)
    
    def add_user_message(self, text: str) -> None:
        """Add a user message to the chat."""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"\n[bold #7b7bff]You:[/] {text}")
    
    def add_assistant_message(self, text: str) -> None:
        """Add an AI response to the chat."""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"\n[bold #00c896]Assistant:[/] {text}")
    
    def add_system_message(self, text: str) -> None:
        """Add a system message to the chat."""
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"\n[bold #f5a623]System:[/] {text}")
    
    @work(thread=True, exclusive=True)
    def run_chat(self, prompt: str) -> None:
        """Run the WIDDX UIL pipeline in a thread worker."""
        worker = get_current_worker()
        app_state = self.app._app_state
        
        # Use synchronous provider (opencode-zen)
        result, decision = app_state["uil"].process(
            prompt,
            messages=app_state["_messages"],
            executors=app_state["executors"],
        )
        
        if worker.is_cancelled:
            return
        
        app_state["_messages"].append(
            {"role": "assistant", "content": result.summary}
        )
        self.call_from_thread(self.add_assistant_message, result.summary)
```

### 3. RichLog for Chat Display

```python
class ChatLog(RichLog):
    """Custom RichLog for chat messages with auto-scroll and max lines."""
    
    def __init__(self, **kwargs):
        super().__init__(
            highlight=True,
            markup=True,
            max_lines=1000,
            auto_scroll=True,
            wrap=True,
            **kwargs,
        )
```

### 4. Settings Screen Pattern

```python
class SettingsScreen(Screen):
    """Settings screen with provider/model configuration."""
    
    def compose(self) -> ComposeResult:
        yield Header(title="Settings")
        yield Vertical(
            Label("Provider:"),
            Select([("opencode-zen", "opencode-zen"), 
                    ("deepseek", "deepseek"),
                    ("openai", "openai")],
                   id="provider-select"),
            Label("Model:"),
            Input(id="model-input", placeholder="deepseek-v4-flash-free"),
            Label("API Key:"),
            Input(id="api-key-input", password=True),
            Button("Save", id="save-btn", variant="primary"),
            Button("Back", id="back-btn"),
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.switch_mode("chat")
```

### 5. Modal Dialog Pattern

```python
class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog."""
    
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure?", id="question"),
            Button("Yes", variant="error", id="yes"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
```

## Performance Rules

### 1. Workers ONLY for async/threaded operations
- Use `@work(thread=True)` for synchronous WIDDX backend calls
- Use `@work(exclusive=True)` for API calls to prevent race conditions
- ALWAYS check `worker.is_cancelled` before UI updates

### 2. RichLog optimization
- Set `max_lines` to prevent memory growth (1000 max)
- Use `markup=True` for Rich formatting, `highlight=True` for auto-highlighting
- Use `auto_scroll=True` for new messages
- DO NOT use RichLog for streaming content (use Static with update())

### 3. CSS: use `$` color variables
```css
Screen { background: $surface; }
ChatLog { border: solid $primary; }
#chat-input { dock: bottom; height: 3; }
```

### 4. Screen transitions
- Use `switch_mode()` for navigation (not push/pop)
- Use `push_screen()` ONLY for modals
- Pre-load screens in `MODES` dict (not dynamic `install_screen`)

### 5. Avoid blocking the UI
- Never call `time.sleep()` — use `set_interval()` or workers
- Never do I/O in compose() or on_mount() — use workers
- Never update UI from thread workers directly — use `call_from_thread()`

## Backend Integration

### Connecting to WIDDX core:

```python
def on_mount(self) -> None:
    """Initialize WIDDX backend."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    
    from core import config, tools
    from core.uil import UnifiedIntelligenceLayer, ExecutionMode
    from core.providers.providers import create_provider
    from core.mcp.client import get_mcp_manager
    from core.project import state as project_state
    from core.skills import skill_manager
    from core.proxy import proxy_manager
    
    # Load config and create provider
    cfg = config.load()
    provider = create_provider(cfg)
    tools.configure(cfg.get("sandbox_path"))
    
    # Initialize UIL
    uil = Unified IntelligenceLayer(provider=provider)
    
    # Initialize MCP (lazy)
    mcp_mgr = get_mcp_manager()
    mcp_mgr.load_from_config(cfg)
    
    # Build tool definitions
    tool_defs = list(tools.TOOL_DEFINITIONS)
    
    # Set up executors
    executors = {
        ExecutionMode.SIMPLE_CHAT: self._simple_chat_exec,
        ExecutionMode.AUTONOMOUS: self._autonomous_exec,
        ExecutionMode.EXPERT_TEAM: self._expert_team_exec,
        ExecutionMode.DIRECT_TOOL: self._direct_tool_exec,
    }
    
    # Store in app state
    self._app_state = {
        "cfg": cfg,
        "provider": provider,
        "uil": uil,
        "tool_defs": tool_defs,
        "executors": executors,
        "_messages": [],
        "model": f"{provider.name}/{provider.model}",
        "cost": 0.0,
        "turns": 0,
    }
```

### Executor wrappers (thread-safe):

```python
def _simple_chat_exec(self, decision, inp, msgs):
    from core.chat import run_stream_turn
    msgs, _ = run_stream_turn(
        self._app_state["provider"], msgs, 
        self._app_state, decision.tool_defs, 
        self._app_state["cfg"]
    )
    for m in reversed(msgs):
        if m["role"] == "assistant":
            return m["content"]
    return ""
```

## CSS Architecture

```css
/* Main layout */
Screen {
    layout: vertical;
}

/* Chat area */
ChatLog {
    height: 1fr;
    border: solid $primary;
    margin: 1;
    padding: 1;
}

/* Input bar */
Input {
    dock: bottom;
    height: 3;
    margin: 0 1;
}

/* Settings screen */
#settings-grid {
    layout: grid;
    grid-size: 2;
    padding: 2;
}

/* Modals */
#dialog {
    width: 40;
    height: 8;
    border: thick $primary;
    padding: 1;
    background: $surface;
}

/* Dark mode defaults */
Screen {
    background: $surface;
    color: $text;
}
```

## Error Handling

```python
@work(thread=True, exclusive=True)
def run_chat(self, prompt: str) -> None:
    """Safe execution wrapper."""
    worker = get_current_worker()
    try:
        result, decision = self._app_state["uil"].process(
            prompt,
            messages=self._app_state["_messages"],
            executors=self._app_state["executors"],
        )
        if not worker.is_cancelled:
            self.call_from_thread(self._on_result, result)
    except Exception as e:
        if not worker.is_cancelled:
            self.call_from_thread(self._on_error, str(e))

def _on_result(self, result) -> None:
    self.add_assistant_message(result.summary)

def _on_error(self, error: str) -> None:
    self.add_system_message(f"Error: {error}")
```

## File Structure

```
core/ui/textual_app.py       — Main app (entry point)
core/ui/textual_widgets.py   — Custom widgets (ChatLog, ChatMessage, etc.)
core/ui/textual_screens.py   — All screen classes
core/ui/textual.tcss         — Main stylesheet
```

## Testing Rules

- Test each Screen in isolation
- Use `pytest-textual` for widget testing
- Test worker cancellation paths
- Test with mock provider (no API calls)
- Verify no `time.sleep()` anywhere in production code

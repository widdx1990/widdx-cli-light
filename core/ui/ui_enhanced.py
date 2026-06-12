"""Enhanced UI rendering functions for WIDDX — Premium CLI Experience.

This module provides an improved user interface with:
- Refined visual hierarchy
- Better contextual information
- Enhanced streaming and real-time feedback
- Improved color scheme and typography
- Better tool call visualization
- Enhanced status indicators
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

from .. import tools
from .. import config
from ..proxy import proxy_manager
from ..skills import skill_manager

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich.console import Group
from rich.syntax import Syntax
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.box import ROUNDED, HEAVY, SQUARE

# Color scheme
COLORS = {
    "brand": "#00c896",      # Primary green
    "accent": "#f5a623",     # Orange/gold
    "user": "#7b7bff",       # Blue/purple
    "success": "#00c896",    # Green
    "error": "#ff6b6b",      # Red
    "warning": "#ffd93d",    # Yellow
    "dim": "dim",            # Dim/gray
    "white": "white",        # White
}

# Detect syntax highlighting support
_HAS_PYGMENTS = True
try:
    from pygments.lexers import get_lexer_by_name
except ImportError:
    _HAS_PYGMENTS = False

# Detect prompt_toolkit for enhanced input
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    _PROMPT_TOOLKIT_OK = True
except Exception:
    _PROMPT_TOOLKIT_OK = False

console = Console(highlight=False, force_terminal=True)
_session = None


# ─────────────────────────────────────────────────────────────────
# Header & Status Bar
# ─────────────────────────────────────────────────────────────────

def print_header_enhanced(state: dict):
    """Print an enhanced header with rich contextual information."""
    console.clear()
    
    # Extract state information
    model = state.get("model", "unknown")
    cost = state.get("cost", 0.0)
    turns = state.get("turns", 0)
    proxy_status = proxy_manager.status()
    
    # Build status items
    status_items = []
    
    # WIDDX branding
    status_items.append(Text("  WIDDX  ", style=f"bold {COLORS['brand']} on #001a0f"))
    
    # Model info
    status_items.append(Text(f"  {model}  ", style=f"bold {COLORS['accent']} on #1a0f00"))
    
    # Cost
    cost_text = f"${cost:.4f}" if cost > 0 else "Free"
    status_items.append(Text(f"  Cost: {cost_text}  ", style=f"{COLORS['dim']}"))
    
    # Turns
    status_items.append(Text(f"  Turns: {turns}  ", style=f"{COLORS['dim']}"))
    
    # Proxy status
    proxy_icon = "✓" if "working" in proxy_status.lower() else "○"
    status_items.append(Text(f"  {proxy_icon} Proxy  ", style=f"{COLORS['dim']}"))
    
    # Active skill if any
    if skill_manager.active:
        skill_icon = skill_manager.active.icon or "⚡"
        status_items.append(Text(f"  {skill_icon} {skill_manager.active.name}  ", 
                                style=f"bold {COLORS['user']}"))
    
    # Create header panel
    header_content = Text()
    for i, item in enumerate(status_items):
        header_content.append(item)
        if i < len(status_items) - 1:
            header_content.append(Text("│", style=f"{COLORS['dim']}"))
    
    console.print(Panel(
        Align.center(header_content),
        style=COLORS['brand'],
        padding=(0, 1),
        box=ROUNDED,
    ))
    console.print()


# ─────────────────────────────────────────────────────────────────
# User Input
# ─────────────────────────────────────────────────────────────────

def print_user_msg_enhanced(text: str):
    """Print user message with enhanced styling."""
    ts = datetime.now().strftime("%H:%M")
    char_count = len(text)
    
    # Header
    header = Text()
    header.append("  👤 You  ", style=f"bold {COLORS['user']}")
    header.append(f"{ts}", style=f"{COLORS['dim']}")
    
    console.print()
    console.print(header)
    
    # Content panel
    console.print(Panel(
        Text(text, style=COLORS['white']),
        border_style=COLORS['user'],
        padding=(1, 1),
        box=ROUNDED,
        subtitle=f"[{COLORS['dim']}]{char_count} characters[/]",
        subtitle_align="right",
    ))


# ─────────────────────────────────────────────────────────────────
# AI Output Streaming
# ─────────────────────────────────────────────────────────────────

def print_ai_stream_enhanced():
    """Return (live, update_fn, done_fn) for enhanced streaming AI response."""
    ts = datetime.now().strftime("%H:%M")
    
    # Header
    header = Text()
    header.append("  🤖 Assistant  ", style=f"bold {COLORS['brand']} on #001a0f")
    header.append(f"{ts}", style=f"{COLORS['dim']}")
    
    console.print()
    console.print(header)
    
    accumulated = [""]
    
    def get_panel():
        text = "".join(accumulated)
        if not text:
            return Panel(
                Text("▊", style=f"dim {COLORS['brand']}"),
                border_style=COLORS['brand'],
                padding=(0, 1),
                box=ROUNDED,
            )
        return Panel(
            _render_markdown_syntax(text),
            border_style=COLORS['brand'],
            padding=(0, 1),
            box=ROUNDED,
        )
    
    live = Live(get_panel(), console=console, refresh_per_second=15, transient=True)
    
    def update(chunk: str):
        accumulated.append(chunk)
    
    def done():
        text = "".join(accumulated)
        if text:
            console.print(Panel(
                _render_markdown_syntax(text),
                border_style=COLORS['brand'],
                padding=(0, 1),
                box=ROUNDED,
            ))
    
    return live, update, done


# ─────────────────────────────────────────────────────────────────
# Tool Calls & Results
# ─────────────────────────────────────────────────────────────────

def print_tool_call_enhanced(name: str, args_json: str):
    """Show tool call with enhanced visualization."""
    console.print()
    
    # Header
    header = Text()
    header.append("  🛠️  ", style=f"bold {COLORS['accent']}")
    header.append(f"Calling: {name}", style=f"bold {COLORS['accent']}")
    console.print(header)
    
    # Arguments
    try:
        parsed = json.loads(args_json)
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        formatted = args_json
    
    console.print(Panel(
        Text(formatted, style=f"{COLORS['accent']}"),
        border_style=COLORS['accent'],
        padding=(0, 1),
        box=ROUNDED,
    ))


def print_tool_result_enhanced(name: str, result: str, success: bool = True):
    """Show tool result with status indicator."""
    console.print()
    
    # Determine styling based on success
    icon = "✅" if success else "❌"
    color = COLORS['success'] if success else COLORS['error']
    
    # Header
    header = Text()
    header.append(f"  {icon}  ", style=f"bold {color}")
    header.append(f"Result: {name}", style=f"bold {color}")
    ts = datetime.now().strftime("%H:%M")
    header.append(f" {ts}", style=f"{COLORS['dim']}")
    console.print(header)
    
    # Result preview
    preview = result[:1500]
    if len(result) > 1500:
        preview += "\n[...truncated...]"
    
    console.print(Panel(
        Text(preview, style=color),
        border_style=color,
        padding=(0, 1),
        box=ROUNDED,
    ))


# ─────────────────────────────────────────────────────────────────
# Reasoning/Thinking
# ─────────────────────────────────────────────────────────────────

def print_reasoning_enhanced(text: str):
    """Show thinking process in a collapsible panel."""
    console.print()
    
    summary = text[:200] + "..." if len(text) > 200 else text
    n_lines = text.count("\n") + 1
    
    title = f"[{COLORS['dim']}]  🧠 Thinking  ({n_lines} lines)[/]"
    
    console.print(Panel(
        Text.from_markup(f"[{COLORS['dim']}]{summary}[/]"),
        border_style=COLORS['dim'],
        title=title,
        title_align="left",
        padding=(0, 1),
        box=ROUNDED,
    ))
    
    if len(text) > 200:
        console.print(Text(f"     [italic {COLORS['dim']}]Type /reasoning to expand[/]", 
                          style=f"italic {COLORS['dim']}"))


# ─────────────────────────────────────────────────────────────────
# System Messages
# ─────────────────────────────────────────────────────────────────

def print_system_msg_enhanced(text: str, msg_type: str = "info"):
    """Print system message with type-specific styling."""
    console.print()
    
    # Determine icon and color based on type
    icons = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✕",
        "system": "⚙",
    }
    colors = {
        "info": COLORS['accent'],
        "success": COLORS['success'],
        "warning": COLORS['warning'],
        "error": COLORS['error'],
        "system": COLORS['accent'],
    }
    
    icon = icons.get(msg_type, "•")
    color = colors.get(msg_type, COLORS['accent'])
    
    console.print(Panel(
        Text.from_markup(f"[{color}]{text}[/]"),
        border_style=color,
        title=f"[{color}]  {icon}  {msg_type.upper()}[/]",
        title_align="left",
        padding=(0, 1),
        box=ROUNDED,
    ))


# ─────────────────────────────────────────────────────────────────
# Markdown & Syntax Highlighting
# ─────────────────────────────────────────────────────────────────

def _render_markdown_syntax(text: str):
    """Render text with syntax-highlighted code blocks."""
    parts = []
    remaining = text
    
    while remaining:
        idx = remaining.find("```")
        if idx == -1:
            parts.append(Markdown(remaining))
            break
        
        before = remaining[:idx]
        if before.strip():
            parts.append(Markdown(before))
        
        remaining = remaining[idx + 3:]
        end_line = remaining.find("\n")
        if end_line == -1:
            parts.append(Text(remaining))
            break
        
        lang = remaining[:end_line].strip()
        code_start = end_line + 1
        close = remaining.find("```", code_start)
        
        if close == -1:
            code = remaining[code_start:]
            remaining = ""
        else:
            code = remaining[code_start:close]
            remaining = remaining[close + 3:]
        
        if _HAS_PYGMENTS and lang:
            try:
                syntax = Syntax(code.rstrip("\n"), lang or "text",
                              theme="monokai", line_numbers=False,
                              word_wrap=True, background_color="default")
                parts.append(syntax)
                continue
            except Exception:
                pass
        
        parts.append(Markdown(f"```{lang}\n{code}\n```"))
    
    if len(parts) == 1:
        return parts[0]
    return Group(*parts)


# ─────────────────────────────────────────────────────────────────
# Agent Execution Summary
# ─────────────────────────────────────────────────────────────────

def print_agent_summary_enhanced(steps: list, summary: str):
    """Show enhanced agent execution summary with step details."""
    console.print()
    
    if not steps:
        console.print(Panel(
            Text(summary, style=COLORS['white']),
            border_style=COLORS['brand'],
            title=f"[bold {COLORS['brand']}]  🎯 Complete[/]",
            title_align="left",
            padding=(1, 1),
            box=ROUNDED,
        ))
        return
    
    # Calculate statistics
    done = sum(1 for s in steps if s.status == "done")
    failed = sum(1 for s in steps if s.status == "failed")
    total = len(steps)
    
    # Build step list
    lines = [f"[bold]Steps: {done}/{total} succeeded[/]"]
    if failed:
        lines.append(f"[bold {COLORS['error']}]Failed: {failed}[/]")
    lines.append("")
    
    for s in steps:
        icon = f"[bold {COLORS['success']}]✓[/]" if s.status == "done" else f"[bold {COLORS['error']}]✕[/]"
        preview = s.result[:100].replace("\n", " ")
        if len(s.result) > 100:
            preview += "..."
        lines.append(f"  {icon} Step {s.step_num}: [bold]{s.tool_name}[/] → {preview}")
    
    lines.append("")
    lines.append(f"[bold]Summary:[/] {summary}")
    
    console.print(Panel(
        Text.from_markup("\n".join(lines)),
        border_style=COLORS['brand'],
        title=f"[bold {COLORS['brand']}]  🎯 Agent Complete[/]",
        title_align="left",
        padding=(1, 1),
        box=ROUNDED,
    ))


# ─────────────────────────────────────────────────────────────────
# Input Prompt
# ─────────────────────────────────────────────────────────────────

def _bottom_toolbar_enhanced():
    """Enhanced bottom toolbar with contextual information."""
    from prompt_toolkit.formatted_text import HTML as _HTML
    from ..config import load as load_config

    try:
        cfg = load_config()
        p = cfg.get("provider", {})
        model = p.get("model", "?")
        proxy = proxy_manager.status()[:20]
        return _HTML(
            f'<b><style bg="ansibrightgreen"> ❯ </style></b> '
            f'<b>model</b>: {model}  |  '
            f'<b>proxy</b>: {proxy}  |  '
            f'<b>Ctrl+D</b>: exit'
        )
    except Exception:
        return _HTML("")


def get_input_enhanced(state: dict | None = None) -> str:
    """Enhanced input prompt with history, auto-suggest, and toolbar."""
    global _session
    history_file = str(Path.cwd() / ".widdx" / "input_history")
    
    if _PROMPT_TOOLKIT_OK:
        try:
            if _session is None:
                _session = PromptSession(
                    history=FileHistory(history_file),
                    auto_suggest=AutoSuggestFromHistory(),
                    enable_history_search=True,
                    complete_while_typing=False,
                )
            
            style = PTStyle.from_dict({
                "prompt": f"{COLORS['brand']} bold",
                "status.title": f"bold {COLORS['accent']}",
                "status.field": f"{COLORS['dim']}",
            })
            
            text = _session.prompt(
                HTML(f"<ansigreen><b> ❯ </b></ansigreen>"),
                style=style,
                bottom_toolbar=_bottom_toolbar_enhanced,
            )
            return text.strip()
        except Exception:
            pass
    
    # Fallback
    console.print(Text(" ❯ ", style=f"bold {COLORS['brand']}"), end="")
    sys.stdout.flush()
    return input().strip()


# ─────────────────────────────────────────────────────────────────
# Progress Indicator
# ─────────────────────────────────────────────────────────────────

def show_progress_enhanced(description: str = "Processing..."):
    """Show a transient progress indicator (auto-removes on exit)."""
    with Progress(
        SpinnerColumn(style=COLORS['brand']),
        TextColumn(f"[{COLORS['brand']}]{description}[/]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)


# ─────────────────────────────────────────────────────────────────
# Divider
# ─────────────────────────────────────────────────────────────────

def print_divider_enhanced():
    """Print an enhanced visual divider."""
    console.print(Text("  " + chr(9472) * 70, style=f"{COLORS['dim']}"))


# ── Standard-name aliases (main.py / chat.py / agents call these) ──

print_header = print_header_enhanced
print_user_msg = print_user_msg_enhanced
print_ai_stream = print_ai_stream_enhanced
print_tool_call = print_tool_call_enhanced
print_reasoning = print_reasoning_enhanced
print_divider = print_divider_enhanced
get_input = get_input_enhanced
show_thinking = show_progress_enhanced
print_system_msg = print_system_msg_enhanced
print_agent_done = print_agent_summary_enhanced


def print_tool_msg(name: str, result: str):
    """Alias: tool result display."""
    success = not result.startswith("Error") and "Failed" not in result
    print_tool_result_enhanced(name, result, success=success)


def print_ai_msg(text: str, tool_info: str = ""):
    """Alias: AI message display."""
    from .ui import print_ai_msg as _fb
    _fb(text, tool_info)


# ── Commands without dedicated enhanced versions ──
from .ui import (
    handle_help, handle_tools_list, handle_skills_list,
    handle_history, handle_proxy, handle_save,
)


"""UI rendering functions for the WIDDX terminal chat tool."""

import sys, time, json
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

console = Console(highlight=False)


def print_header(state):
    console.clear()
    cost_str = "$%.4f" % state["cost"]
    proxy_str = proxy_manager.status()
    skill_name = ""
    if skill_manager.active:
        icon = skill_manager.active.icon + " " if skill_manager.active.icon else ""
        skill_name = f"skill: {icon}{skill_manager.active.name}"

    # Build a compact one-line status bar
    left = Text(" WIDDX ", style="bold #00c896")
    center = Text(f" {state['model']} ", style="bold #f5a623")
    right_parts = [f"cost: {cost_str}", f"turns: {state['turns']}"]
    if skill_name:
        right_parts.append(skill_name)
    right = Text(" | ".join(right_parts), style="dim")

    grid = Table.grid(padding=(0, 2))
    grid.add_row(left, center, right)
    console.print(Panel(grid, style="#00c896", padding=(0, 1)))


def print_user_msg(text):
    ts = datetime.now().strftime("%H:%M")
    console.print()
    console.print(Text(f"  \U0001f464 You  {ts}", style="bold #7b7bff"))
    console.print(Panel(
        Text(text, style="white"),
        border_style="#7b7bff",
        padding=(0, 1),
        subtitle=f"[dim]{len(text)} chars[/]",
        subtitle_align="right",
    ))


def print_ai_msg(text, tool_info=""):
    ts = datetime.now().strftime("%H:%M")
    title = "assistant"
    if tool_info:
        title += f" [{tool_info}]"
    header = Text()
    header.append(f" {title} ", style="bold #00c896 on #001a0f")
    header.append(f" {ts}", style="dim")
    console.print()
    console.print(header)
    console.print(Panel(_render_markdown_syntax(text), border_style="#00c896", padding=(0, 1)))


def print_ai_stream():
    """Return a (live, update_fn, done_fn) tuple for streaming AI response."""
    ts = datetime.now().strftime("%H:%M")
    header = Text()
    header.append(" assistant ", style="bold #00c896 on #001a0f")
    header.append(f" {ts}", style="dim")
    console.print()
    console.print(header)
    accumulated = [""]

    def get_panel():
        text = "".join(accumulated)
        if not text:
            return Panel(Text("\u258a", style="dim #00c896"), border_style="#00c896", padding=(0, 1))
        return Panel(_render_markdown_syntax(text), border_style="#00c896", padding=(0, 1))

    live = Live(get_panel(), console=console, refresh_per_second=15, transient=True)

    def update(chunk: str):
        accumulated.append(chunk)

    def done():
        """Finalize — print the complete response panel."""
        text = "".join(accumulated)
        if text:
            console.print(Panel(
                _render_markdown_syntax(text),
                border_style="#00c896",
                padding=(0, 1),
            ))
        # Print a small visual done indicator
        ts = datetime.now().strftime("%H:%M")
        console.print(Text(f"  ✓ done  {ts}", style="dim #00c896"))

    return live, update, done


def _render_markdown_syntax(text):
    """Render text with syntax-highlighted code blocks.
    Falls back to plain Markdown if pygments is not available."""
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
                              word_wrap=True)
                parts.append(syntax)
                continue
            except Exception:
                pass
        parts.append(Markdown(f"```{lang}\n{code}\n```"))
    if len(parts) == 1:
        return parts[0]
    return Group(*parts)


def print_divider():
    """Thin separator between conversation turns."""
    console.print(Text(" " + "─" * 60, style="dim #333333"))


def print_system_msg(text):
    console.print()
    console.print(Panel(
        Text.from_markup(f"[#f5a623]{text}[/]"),
        border_style="#f5a623",
        title="[#f5a623]  ⚙  system[/]",
        title_align="left",
        padding=(0, 1),
    ))


def print_tool_msg(name, result):
    header = Text()
    header.append(f" {name} ", style="bold #f5a623 on #1a0f00")
    ts = datetime.now().strftime("%H:%M")
    header.append(f" {ts}", style="dim")
    console.print()
    console.print(header)
    preview = result[:1000]
    if len(result) > 1000:
        preview += "\n...[truncated]"
    console.print(Panel(Text(preview, style="#f5a623"), border_style="#f5a623", padding=(0, 1)))


def print_tool_call(name, args_json):
    """Show what tool the AI wants to call, before execution."""
    console.print()
    console.print(Text(f"  \U0001f6e0  {name}", style="bold #f5a623"))
    # Pretty-print JSON if possible
    try:
        parsed = json.loads(args_json)
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        formatted = args_json
    console.print(Panel(
        Text(formatted, style="bold #f5a623"),
        border_style="#f5a623",
        padding=(0, 1),
    ))


def print_reasoning(text):
    """Show thinking process — always collapsed to save space."""
    console.print()
    summary = text[:197] + "..." if len(text) > 197 else text
    n_lines = text.count("\n") + 1
    title = f"[dim]  \U0001f9e0 thinking  ({n_lines} lines)[/]"
    console.print(Panel(
        Text.from_markup(f"[dim]{summary}[/]\n" if len(text) > 197 else f"[dim]{text}[/]\n"),
        border_style="dim",
        title=title,
        title_align="left",
        padding=(0, 1),
    ))
    if len(text) > 197:
        console.print(Text(f"     /reasoning to expand", style="italic #888888"))


def show_thinking():
    """Show a quick transient spinner before processing starts.
    Actual work is shown live via the streaming AI response panel."""
    with Live(
        Spinner("dots", text=Text(" Processing...", style="dim"), style="#00c896"),
        console=console, refresh_per_second=12, transient=True
    ):
        pass  # transient=True removes it as soon as the block exits


def handle_help():
    table = Table(title="[bold #00c896]Commands[/]", border_style="dim", header_style="bold #f5a623")
    table.add_column("Command", style="bold #00c896", min_width=14)
    table.add_column("Description", style="white")
    cmds = [
        ("/help", "Show help"),
        ("/clear", "Clear screen"),
        ("/model", "Change AI model"),
        ("/provider", "Change provider (opencode-zen/ollama/openai/deepseek)"),
        ("/apikey", "Set/forget API key for current provider (hidden input)"),
        ("/skills", "List available skills"),
        ("/proxy", "Show proxy status or refresh list"),
        ("/history", "Show conversation history"),
        ("/save", "Save conversation to file"),
        ("/tools", "Show available tools"),
        ("/sandbox", "Set sandbox directory for safe writes"),
        ("/manifest", "Regenerate MANIFEST.json project structure"),
        ("/reasoning", "Show full reasoning from last turn"),
        ("/mcp", "List connected MCP servers and their tools"),
        ("/agent", "Autonomous agent mode (Expert Team is default)"),
        ("/doctor", "Run system health check"),
        ("/permissions", "Manage tool permissions (level, forget, status)"),
        ("/export", "Export conversation as markdown file"),
        ("/version", "Show version info"),
        ("/remember", "Save a fact to persistent memory (e.g. /remember prefers Python)"),
        ("/memories", "List/search saved memories (/memories or /memories query)"),
        ("/exit or /quit", "Exit"),
    ]
    for cmd, desc in cmds:
        table.add_row(cmd, desc)
    console.print(table)
    console.print()
    shortcuts = [s.name for s in skill_manager.list_all()[:6]]
    if shortcuts:
        console.print(Text(f"  Skill shortcuts: {'  '.join('!' + s for s in shortcuts)}  |  !off", style="dim"))


def handle_tools_list():
    table = Table(title="[bold #00c896]Tools[/]", border_style="dim", header_style="bold #f5a623")
    table.add_column("Tool", style="bold #00c896", min_width=14)
    table.add_column("Description", style="white")
    for t in tools.TOOL_DEFINITIONS:
        params = ", ".join(t.get("parameters", {}).keys())
        table.add_row(t["name"], f"{t['description']} ({params})")
    console.print(table)


def handle_skills_list():
    all_skills = skill_manager.list_all()
    if not all_skills:
        print_system_msg("No skills found. Add skill.md files to skills/ directory.")
        return
    active_name = skill_manager.active.name if skill_manager.active else None
    table = Table(title="[bold #00c896]Available Skills[/]", border_style="dim", header_style="bold #f5a623")
    table.add_column("Command", style="bold #00c896", min_width=18)
    table.add_column("Icon", style="", width=4)
    table.add_column("Description", style="white")
    table.add_column("Status", style="", width=12)
    for s in all_skills:
        status = "[#00c896 bold]\u25cf active[/]" if s.name == active_name else "[dim]\u25cb[/]"
        table.add_row(f"!{s.name}", s.icon, s.description, status)
    console.print(table)
    examples = "  ".join(f"!{s.name}" for s in all_skills[:5])
    if examples:
        console.print(Text(f"  Type !name to activate  |  !off to deactivate", style="dim"))
        console.print(Text(f"  Shortcuts: {examples}", style="dim"))


def handle_history(messages):
    if not messages:
        print_system_msg("No messages")
        return
    table = Table(title=f"[bold #00c896]History ({len(messages)} messages)[/]", border_style="dim")
    table.add_column("#", style="dim", width=3)
    table.add_column("Role", style="bold", width=10)
    table.add_column("Content", style="white")
    for i, m in enumerate(messages, 1):
        role = m.get("role", "")
        content = m.get("content", "")[:80]
        if m.get("tool_calls"):
            names = ", ".join(tc.get("function", {}).get("name", "") for tc in m["tool_calls"])
            content = f"[tools: {names}]"
        table.add_row(str(i), role, content)
    console.print(table)


def handle_proxy():
    table = Table(title="[bold #00c896]Proxy Status[/]", border_style="dim", header_style="bold #f5a623")
    table.add_column("Info", style="bold #00c896", min_width=18)
    table.add_column("Value", style="white")
    current = proxy_manager.current_proxy() or "No proxy (direct connection)"
    table.add_row("Current proxy", current)
    table.add_row("Status", proxy_manager.status())
    console.print(table)

    from rich.prompt import Prompt as RPrompt
    action = RPrompt.ask("Action: [r]efresh / [n]ext / [enter] to cancel", default="")
    if action.lower() == "r":
        proxy_manager.force_refresh()
        print_system_msg("\U0001f504 Refreshing proxy list in the background...")
    elif action.lower() == "n":
        proxy_manager.rotate()
        print_system_msg(f"\u2705 Switched to: {proxy_manager.current_proxy() or 'direct connection'}")


def print_agent_done(steps, summary):
    """Show the final agent summary panel with step log."""
    if not steps:
        console.print(Panel(
            Text(summary, style="white"),
            border_style="#00c896",
            title="[bold #00c896]Agent Complete[/]",
            title_align="left",
        ))
        return
    done = sum(1 for s in steps if s.status == "done")
    failed = sum(1 for s in steps if s.status == "failed")
    total = len(steps)
    lines = [f"Steps: {done}/{total} succeeded"]
    if failed:
        lines.append(f"Failed: {failed}")
    lines.append("")
    for s in steps:
        icon = "[bold #00c896]\u2705[/]" if s.status == "done" else "[bold red]\u274c[/]"
        preview = s.result[:150].replace("\n", " ")
        if len(s.result) > 150:
            preview += "..."
        lines.append(f"  {icon} Step {s.step_num}: [bold]{s.tool_name}[/] \u2192 {preview}")
    lines.append("")
    lines.append(f"[bold]Summary:[/] {summary}")
    console.print()
    console.print(Panel(
        Text.from_markup("\n".join(lines)),
        border_style="#00c896",
        title="[bold #00c896]Agent Complete[/]",
        title_align="left",
    ))


def handle_save(messages):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"chat_history_{ts}.json")
    data = {"model": config.get("provider", {}).get("model"), "timestamp": ts, "messages": messages}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print_system_msg(f"\u2705 Conversation saved to {path}")


# Global prompt session (reused across turns for history)
_session = None


def _bottom_toolbar():
    """Dynamic toolbar showing model, cost, proxy status."""
    from ..proxy import proxy_manager
    from .. import config as cfg_mod
    cfg = cfg_mod.load()
    p = cfg.get("provider", {})
    model = p.get("model", "?")
    proxy = proxy_manager.status()[:20]
    return HTML(
        f'<b><style bg="ansibrightgreen"> \u2776 </style></b> '
        f'<b>exit</b>: Ctrl+D  |  '
        f'<b>model</b>: {model}  |  '
        f'<b>proxy</b>: {proxy}'
    )


def get_input(state: dict | None = None) -> str:
    """Enhanced input with persistent history, toolbar, and auto-suggest."""
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
                "prompt": "#00c896 bold",
                "status.title": "bold #f5a623",
                "status.field": "#888888",
            })

            # Minimal prompt \u2014 print_user_msg() handles the formatted display
            text = _session.prompt(
                HTML("<style fg='ansigreen'> </style>"),
                style=style,
                bottom_toolbar=_bottom_toolbar,
            )
            return text.strip()
        except Exception:
            pass  # fallback

    # fallback \u2014 plain input with ANSI clear
    console.print(Text(" \u2776  ", style="bold #00c896"), end="")
    sys.stdout.flush()
    text = input().strip()
    sys.stdout.write("\033[A\033[2K")  # clear the input line
    sys.stdout.flush()
    return text

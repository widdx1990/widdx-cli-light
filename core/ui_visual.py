"""Shared CLI/TUI visual helpers and theme primitives.

Consolidates theme palette, rich `console`, panel builders, and
common `show_*` helpers so `cli` and `tui` share a single implementation.
"""

from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.align import Align
from rich.text import Text
from rich.syntax import Syntax
from rich import box as rich_box
from rich.style import Style
from rich.box import ROUNDED, MINIMAL
import unicodedata


@dataclass(frozen=True)
class Theme:
    name: str
    green: str
    orange: str
    dim: str
    red: str
    blue: str
    white: str
    bg: str
    purple: str
    cyan: str
    gold: str


# Built-in palettes (copied from cli.theme)
DARK = Theme(
    name="dark",
    green="#00d4aa",
    orange="#f5a623",
    dim="#636e7a",
    red="#ff5370",
    blue="#82aaff",
    white="#cdd6f4",
    bg="#0b0f19",
    purple="#c792ea",
    cyan="#89dceb",
    gold="#ffd700",
)

LIGHT = Theme(
    name="light",
    green="#007550",
    orange="#b56800",
    dim="#7a8999",
    red="#c0392b",
    blue="#2a5ab5",
    white="#1e2030",
    bg="#eff1f5",
    purple="#7c3aed",
    cyan="#0077aa",
    gold="#b8860b",
)


_REGISTRY = {"dark": DARK, "light": LIGHT}


def get_current_theme():
    try:
        from core.config import settings
        name = settings.get("cli_theme", "dark")
        return _REGISTRY.get(str(name).lower(), DARK)
    except Exception:
        return DARK


# Active theme singleton
T: Theme = get_current_theme()

# Color aliases
GREEN = T.green
ORANGE = T.orange
DIM = T.dim
RED = T.red
BLUE = T.blue
WHITE = T.white
BG = T.bg
PURPLE = T.purple
CYAN = T.cyan
GOLD = T.gold


# Rich Style objects
HEADER = Style(bold=True, color=GREEN)
MODEL = Style(bold=True, color=ORANGE)
USER = Style(color=GREEN)
ASSISTANT = Style(color=ORANGE)
SYSTEM = Style(color=CYAN)
ERROR = Style(bold=True, color=RED)
DIM_STYLE = Style(color=DIM)
TOOL = Style(color=PURPLE)
GOLD_STYLE = Style(color=GOLD)


# Role metadata
ROLE_META_ASCII = {
    "user":      ("▸",  "You",      GREEN),
    "assistant": ("◆",  "WIDDX",    ORANGE),
    "system":    ("⊙",  "System",   CYAN),
    "tool":      ("⚙",  "Tool",     PURPLE),
}


# Shared console
console = Console(highlight=False, markup=True, emoji=True, soft_wrap=True)


def _has_rtl(text: str) -> bool:
    for c in text:
        try:
            if unicodedata.bidirectional(c) in ("R", "AL", "RLE", "RLI"):
                return True
        except Exception:
            continue
    return False


def role_panel(role: str, content: str, timestamp: str = "") -> Panel:
    icon, label, color = ROLE_META_ASCII.get(role, ("•", role.capitalize(), WHITE))
    title = f"[bold {color}] {icon} {label} [/]"
    subtitle = f"[{DIM}] {timestamp} [/]" if timestamp else ""
    body = content[:4000] if content else ""
    return Panel(
        body,
        title=title,
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style=color,
        box=ROUNDED,
        padding=(0, 2),
    )


def reasoning_panel(content: str, elapsed: float | None = None) -> Panel:
    subtitle = f"[{DIM}] {elapsed:.1f}s [/]" if elapsed is not None else ""
    return Panel(
        Text(content[:1000], style=f"{DIM}"),
        title=f"[bold {PURPLE}] 󰙚  Thinking [/]",
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style=PURPLE,
        box=MINIMAL,
        padding=(0, 2),
    )


def header_bar(model: str, cost: float, turns: int) -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(justify="left",  ratio=3)
    grid.add_column(justify="center", ratio=5)
    grid.add_column(justify="right",  ratio=3)

    brand  = f"[bold {GREEN}] ◆ WIDDX[/]"
    model_ = f"[{ORANGE}]{model}[/]"
    meta   = f"[{DIM}]turns:[/][bold {WHITE}]{turns}[/]  [{DIM}]cost:[/][bold {GOLD}]${cost:.4f}[/]"

    grid.add_row(brand, model_, meta)

    return Panel(
        grid,
        border_style=DIM,
        box=ROUNDED,
        padding=(0, 1),
    )


def tool_call_text(name: str, args: dict) -> str:
    args_str = "  ".join(f"[{DIM}]{k}=[/][{PURPLE}]{str(v)[:40]}[/]" for k, v in list(args.items())[:4])
    return f"[bold {PURPLE}] ⚙  {name}[/]  {args_str}"


def tool_result_text(result: str) -> str:
    return f"[{DIM}]    └─ {result[:200]}[/]"


def show_panel(title: str, content: str) -> None:
    console.print(Panel(
        content[:2000],
        title=f"[bold {ORANGE}] {title} [/]",
        title_align="left",
        border_style=DIM,
        box=rich_box.ROUNDED,
        padding=(0, 2),
    ))


def show_reasoning(text: str, elapsed: float | None = None) -> None:
    text = text if not _has_rtl(text) else text
    console.print(reasoning_panel(text, elapsed))


def show_thinking() -> None:
    console.print(f"[{PURPLE}]  󰙚  Thinking…[/]")


def show_tool_call(name: str, args: dict) -> None:
    console.print(tool_call_text(name, args))


def show_tool_result(name: str, result: str) -> None:
    console.print(tool_result_text(result))


def show_markdown(text: str) -> None:
    try:
        from rich.markdown import Markdown
        console.print(Markdown(text, code_theme="monokai"))
    except Exception:
        console.print(text)


def show_code(code: str, lang: str = "python") -> None:
    try:
        from pygments.lexers import get_lexer_by_name  # noqa: F401
        console.print(Syntax(
            code, lang,
            theme="one-dark",
            line_numbers=True,
            word_wrap=True,
            background_color="default",
        ))
        return
    except Exception:
        pass
    console.print(Panel(code, border_style=DIM, box=rich_box.ROUNDED))


def show_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    table = Table(
        title=f"[bold {ORANGE}]{title}[/]",
        border_style=DIM,
        header_style=f"bold {GREEN}",
        box=rich_box.ROUNDED,
        show_lines=False,
        padding=(0, 1),
    )
    for col in columns:
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(*[str(c) for c in row])
    console.print()
    console.print(table)
    console.print()


def show_list(items: list[str], title: str = "") -> None:
    if title:
        console.print(f"[bold {ORANGE}]{title}[/]")
    for item in items:
        console.print(f"  [{GREEN}]▸[/]  {item}")


def show_divider(label: str = "") -> None:
    if label:
        console.print(Rule(f"[{DIM}]{label}[/]", style=DIM))
    else:
        console.print(Rule(style=DIM))


def show_error(text: str) -> None:
    console.print(Panel(
        f"[bold {RED}]{text}[/]",
        title=f"[bold {RED}] ✗  Error [/]",
        border_style=RED,
        box=rich_box.ROUNDED,
        padding=(0, 2),
    ))


def show_success(text: str) -> None:
    console.print(f"  [{GREEN}]✓[/]  {text}")

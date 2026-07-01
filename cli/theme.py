"""Compatibility shim — re-export theme primitives from `core.ui_visual`.

CLI-specific additions only — no duplication with `core.ui_visual`.
"""

from rich.style import Style

from core.ui_visual import (
    CYAN, DIM, GOLD, GREEN, ORANGE, PURPLE, RED,
)


# ── Rich Style Objects (CLI-specific overrides) ──────────────

HEADER    = Style(bold=True, color=GREEN)
MODEL     = Style(bold=True, color=ORANGE)
USER      = Style(color=GREEN)
ASSISTANT = Style(color=ORANGE)
SYSTEM    = Style(color=CYAN)
ERROR     = Style(bold=True, color=RED)
DIM_STYLE = Style(color=DIM)
TOOL      = Style(color=PURPLE)
GOLD_STYLE = Style(color=GOLD)


# ── Role metadata tables (CLI-specific) ───────────────────────────

ROLE_META: dict[str, tuple[str, str, str]] = {
    "user":      ("󰀄",  "You",      GREEN),
    "assistant": ("󱙺",  "WIDDX",    ORANGE),
    "system":    ("",   "System",   CYAN),
    "tool":      ("󰠵",  "Tool",     PURPLE),
}

ROLE_META_ASCII: dict[str, tuple[str, str, str]] = {
    "user":      ("▸",  "You",      GREEN),
    "assistant": ("◆",  "WIDDX",    ORANGE),
    "system":    ("⊙",  "System",   CYAN),
    "tool":      ("⚙",  "Tool",     PURPLE),
}

ROLE_LABELS = {
    role: (f"{icon} {label}", color)
    for role, (icon, label, color) in ROLE_META_ASCII.items()
}

ROLE_ICONS = {role: icon for role, (icon, _, _) in ROLE_META_ASCII.items()}

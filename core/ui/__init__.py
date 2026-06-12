"""UI subpackage — terminal rendering.

Supports standard UI (ui.py) and enhanced UI (ui_enhanced.py).
Switch with /theme command or WIDDX_THEME=enhanced env var.

Usage:
    from core.ui import console, print_header, use_enhanced_ui
    use_enhanced_ui(True)   # switch to enhanced at runtime
"""

import os as _os
import importlib as _il

_USE_ENHANCED = _os.environ.get("WIDDX_THEME", "").lower() in ("enhanced", "1", "yes")
_CACHE = {}


def _get_mod():
    key = "enhanced" if _USE_ENHANCED else "standard"
    if key not in _CACHE:
        name = "core.ui.ui_enhanced" if _USE_ENHANCED else "core.ui.ui"
        _CACHE[key] = _il.import_module(name)
    return _CACHE[key]


def use_enhanced_ui(enabled: bool):
    """Switch between standard (False) and enhanced (True) UI at runtime."""
    global _USE_ENHANCED, _CACHE
    _USE_ENHANCED = enabled
    _CACHE.clear()  # force re-import on next access


def is_enhanced() -> bool:
    return _USE_ENHANCED


def __getattr__(name):
    """Delegate all unknown attributes to the active UI module."""
    mod = _get_mod()
    return getattr(mod, name)

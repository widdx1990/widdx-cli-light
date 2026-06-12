"""UI subpackage — terminal rendering.

Two modes:
- standard (ui.py) — Rich-based console rendering
- enhanced (ui_enhanced.py) — Rich-based with premium styling

Switch with /theme command.
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
    _CACHE.clear()


def is_enhanced() -> bool:
    return _USE_ENHANCED


def __getattr__(name):
    """Delegate all unknown attributes to the active UI module."""
    mod = _get_mod()
    return getattr(mod, name)

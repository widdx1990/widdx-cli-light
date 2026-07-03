"""Sandbox safety layer — path checks and configuration."""

from pathlib import Path

_SAFE_DIR: str | None = None


def configure(sandbox_dir: str | None):
    """Set a sandbox directory for safe file writes."""
    global _SAFE_DIR
    _SAFE_DIR = str(Path(sandbox_dir).resolve()) if sandbox_dir else None


def get_safe_dir() -> str | None:
    return _SAFE_DIR


def is_safe_path(p: Path) -> bool:
    """Check if a resolved path is inside the configured sandbox directory."""
    if _SAFE_DIR is None:
        return True
    try:
        p.resolve().relative_to(Path(_SAFE_DIR).resolve())
        return True
    except ValueError:
        return False

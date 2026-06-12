"""Configuration loader / saver — JSON config file with automatic secret stripping.

Resolution order (first found wins):
  1. .widdx/config.json   (project-local, in CWD)
  2. config.json           (bare in CWD)
  3. <install>/config.json (bundled default — read-only)
"""

import json, os
from pathlib import Path

_INSTALL_DIR = Path(__file__).resolve().parent.parent.parent


def _find_config() -> tuple[Path, bool]:
    """Find the first existing config file.

    Returns (path, is_writable).
    The bundled config at install location is read-only.
    """
    cwd = Path.cwd().resolve()

    # 1. Project-local config (.widdx/)
    local = cwd / ".widdx" / "config.json"
    if local.exists():
        return local, True

    # 2. Bare config.json in CWD
    bare = cwd / "config.json"
    if bare.exists():
        return bare, True

    # 3. Bundled default (read-only — copy to CWD to modify)
    bundled = _INSTALL_DIR / "config.json"
    if bundled.exists():
        return bundled, False

    # No config exists yet — return writable path in CWD
    return cwd / ".widdx" / "config.json", True


def _resolve_placeholders(cfg: dict) -> dict:
    """Replace {PROJECT_ROOT}, {USER_HOME}, and {CWD} placeholders.

    {PROJECT_ROOT} now resolves to CWD (the user's working directory),
    NOT the install directory. This makes MCP server paths etc. work
    even when the tool is installed via pip.
    """
    project_root = os.getcwd().replace("\\", "/")
    user_home = os.environ.get("USERPROFILE", "").replace("\\", "/") or os.environ.get("HOME", "")
    cwd = project_root  # same as PROJECT_ROOT

    def _walk(val):
        if isinstance(val, str):
            return (val.replace("{PROJECT_ROOT}", project_root)
                       .replace("{USER_HOME}", user_home)
                       .replace("{CWD}", cwd))
        elif isinstance(val, dict):
            return {k: _walk(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_walk(v) for v in val]
        return val
    return _walk(cfg)


# ── Module-level cache ──────────────────────────────
_config_path: Path | None = None
_config_writable: bool = False


def _get_config_path() -> tuple[Path, bool]:
    """Cached lookup of config path."""
    global _config_path, _config_writable
    if _config_path is None:
        _config_path, _config_writable = _find_config()
    return _config_path, _config_writable


def load() -> dict:
    path, _ = _get_config_path()
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return _resolve_placeholders(cfg)
    return {}


def get(key: str, default=None):
    return load().get(key, default)


def get_config_path() -> Path:
    """Return the path to the active config file."""
    path, _ = _get_config_path()
    return path


def _strip_secrets(cfg: dict) -> dict:
    """Remove sensitive fields before persisting to disk."""
    safe = json.loads(json.dumps(cfg))
    provider = safe.get("provider", {})
    if "api_key" in provider:
        del provider["api_key"]
    return safe


def save(cfg: dict) -> None:
    """Save config to a writable location.

    Writes to CWD/.widdx/config.json if the current config is
    the bundled read-only default. Otherwise writes in-place.
    """
    path, writable = _get_config_path()
    if not writable:
        # Bundled default → copy to project-local location
        path = Path.cwd().resolve() / ".widdx" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Update cache
        global _config_path, _config_writable
        _config_path = path
        _config_writable = True

    safe = _strip_secrets(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")

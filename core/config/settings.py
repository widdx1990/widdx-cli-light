"""Configuration loader / saver — JSON config file with automatic secret stripping."""

import json, os
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
CONFIG_FILE = BASE / "config.json"


def _resolve_placeholders(cfg: dict) -> dict:
    """Replace {PROJECT_ROOT}, {USER_HOME}, and {CWD} placeholders in config values.

    Recursively walks all string values in the config dict.
    {CWD} resolves to the directory where WIDDX was launched.
    """
    project_root = str(BASE.resolve()).replace("\\", "/")
    user_home = os.environ.get("USERPROFILE", "").replace("\\", "/") or os.environ.get("HOME", "")
    cwd = os.getcwd().replace("\\", "/")

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


def load() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
            return _resolve_placeholders(cfg)
    return {}

def get(key: str, default=None):
    return load().get(key, default)


def _strip_secrets(cfg: dict) -> dict:
    """Remove sensitive fields before persisting to disk."""
    safe = json.loads(json.dumps(cfg))  # deep copy
    provider = safe.get("provider", {})
    if "api_key" in provider:
        del provider["api_key"]
    return safe


def save(cfg: dict) -> None:
    safe = _strip_secrets(cfg)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)

"""Secure API key management using session-scoped environment variables.

Keys are:
- Stored in os.environ for the current process
- Persisted to .widdx/apikeys.json (XOR-obfuscated) for survival across restarts
- Input via getpass (hidden typing) for security
- NEVER stored in config.json (shared/public)
"""

import os
import json
import getpass
import base64
from pathlib import Path
from typing import Optional

# Prefix for all environment variables we set
_ENV_PREFIX = "WIDDX_API_KEY_"

# Providers that need API keys — loaded from config first, then fallback
_KEY_PROVIDERS: dict[str, str] = {}

# Persistence file (in .gitignore via .widdx/*)
def _key_file() -> Path:
    """Get path to persisted API keys file — ALWAYS in package root, never in CWD.

    The API key stays in the main project folder and does NOT follow
    the user to other directories. Uses the install location of this file.
    """
    # Use the directory where this module is installed (package root)
    pkg_dir = Path(__file__).resolve().parent.parent.parent  # core/config/ → root
    widdx_dir = pkg_dir / ".widdx"
    widdx_dir.mkdir(exist_ok=True)
    return widdx_dir / "apikeys.json"


def _xor_obfuscate(text: str) -> str:
    """Simple XOR obfuscation with a fixed key — prevents casual reading only."""
    key = b"WIDDX_NEXUS_KEY_2026"
    data = text.encode("utf-8")
    result = bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))
    return base64.b64encode(result).decode("ascii")


def _xor_deobfuscate(encoded: str) -> str:
    """Reverse _xor_obfuscate."""
    key = b"WIDDX_NEXUS_KEY_2026"
    data = base64.b64decode(encoded.encode("ascii"))
    result = bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))
    return result.decode("utf-8")


def _load_persisted_keys() -> dict[str, str]:
    """Load persisted API keys from disk."""
    kf = _key_file()
    if not kf.exists():
        return {}
    try:
        with open(kf, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: _xor_deobfuscate(v) for k, v in data.items()}
    except Exception:
        return {}


def _save_persisted_keys(keys: dict[str, str]) -> None:
    """Save API keys to disk (XOR-obfuscated)."""
    kf = _key_file()
    kf.parent.mkdir(parents=True, exist_ok=True)
    obfuscated = {k: _xor_obfuscate(v) for k, v in keys.items() if v}
    with open(kf, "w", encoding="utf-8") as f:
        json.dump(obfuscated, f)
    # Restrict file permissions — owner read/write only
    kf.chmod(0o600)


def _get_providers() -> dict[str, str]:
    """Lazy-load provider list from config on first access."""
    global _KEY_PROVIDERS
    if not _KEY_PROVIDERS:
        try:
            from .settings import load as _load_cfg
            cfg = _load_cfg()
            p = cfg.get("provider", {})
            name = p.get("name", "")
            if name:
                _KEY_PROVIDERS[name] = name.upper().replace("-", "_")
                _KEY_PROVIDERS[name.replace("-zen", "")] = name.upper().replace("-", "_")
        except Exception:
            pass
        # Fallback defaults
        if not _KEY_PROVIDERS:
            _KEY_PROVIDERS.update({
                "deepseek": "DEEPSEEK",
                "openai": "OPENAI",
                "opencode-zen": "OPENCODE_ZEN",
                "opencode": "OPENCODE_ZEN",
            })
    return _KEY_PROVIDERS


def _env_name(provider_name: str) -> str:
    """Convert a provider name to its canonical env-var name."""
    providers = _get_providers()
    key = providers.get(provider_name, provider_name.upper())
    return f"{_ENV_PREFIX}{key}"


def get_key(provider_name: str) -> Optional[str]:
    """Retrieve an API key.

    Checks (in order):
      1. WIDDX_API_KEY_<PROVIDER> (set by set_key during this session)
      2. <PROVIDER>_API_KEY (e.g. DEEPSEEK_API_KEY — pre-existing env var)
      3. Persisted .widdx/apikeys.json (survives restarts)
      4. WIDDX_API_KEY (fallback generic key)

    Returns None if no key is found.
    """
    # 1. Session key set via set_key()
    session_var = _env_name(provider_name)
    val = os.environ.get(session_var)
    if val:
        return val

    # 2. Pre-existing provider-specific env var (e.g. DEEPSEEK_API_KEY)
    providers = _get_providers()
    standard_var = providers.get(provider_name, provider_name.upper()) + "_API_KEY"
    val = os.environ.get(standard_var)
    if val:
        return val

    # 3. Persisted key file (survives restarts)
    persisted = _load_persisted_keys()
    val = persisted.get(provider_name)
    if val:
        # Load into session env for faster access next time
        os.environ[session_var] = val
        return val

    # 4. Generic fallback
    val = os.environ.get("WIDDX_API_KEY")
    return val


def set_key(provider_name: str, api_key: str) -> None:
    """Store an API key in the session AND persist to disk.

    The key is set in os.environ for the current process
    AND saved to .widdx/apikeys.json (XOR-obfuscated) to survive restarts.
    NEVER written to config.json.
    """
    # Session (immediate)
    os.environ[_env_name(provider_name)] = api_key
    # Persist to disk
    persisted = _load_persisted_keys()
    persisted[provider_name] = api_key
    _save_persisted_keys(persisted)


def has_key(provider_name: str) -> bool:
    """Check if a key exists for the given provider (checks env + persisted)."""
    return get_key(provider_name) is not None


def prompt_key(provider_name: str, message: Optional[str] = None) -> str:
    """Prompt the user to enter an API key with hidden input.

    Uses getpass so the typed key is NOT shown on screen.
    Automatically stores the key in session + persisted.
    Returns the key.
    """
    if message is None:
        message = f"\U0001f511 Enter {provider_name.title()} API Key"
    key = getpass.getpass(f"{message}: ").strip()
    if key:
        set_key(provider_name, key)
    return key


def forget_key(provider_name: str) -> None:
    """Remove a key from session AND persisted storage."""
    var = _env_name(provider_name)
    os.environ.pop(var, None)
    persisted = _load_persisted_keys()
    if provider_name in persisted:
        del persisted[provider_name]
        _save_persisted_keys(persisted)


def list_providers_with_keys() -> list[str]:
    """Return names of providers that have keys set."""
    providers = _get_providers()
    return [p for p in providers if has_key(p)]


def sanitized_environ() -> dict[str, str]:
    """Return the current environment with WIDDX API keys stripped.

    Use this when spawning subprocesses to prevent leaking
    API keys to child processes (e.g. bash commands).
    """
    clean = dict(os.environ)
    keys_to_remove = [k for k in clean if k.startswith(_ENV_PREFIX)]
    for k in keys_to_remove:
        del clean[k]
    return clean

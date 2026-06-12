"""Secure API key management using session-scoped environment variables.

Keys are:
- Stored in os.environ for the current process only (NEVER in config.json)
- Input via getpass (hidden typing) for security
- Readable only during the current session
"""

import os
import getpass
from typing import Optional

# Prefix for all environment variables we set
_ENV_PREFIX = "WIDDX_API_KEY_"

# Providers that need API keys — loaded from config first, then fallback
_KEY_PROVIDERS: dict[str, str] = {}


def _load_providers_from_config():
    """Dynamically load provider names from config.json."""
    if _KEY_PROVIDERS:
        return
    try:
        from pathlib import Path
        import json
        cfg_path = Path(__file__).parent.parent.parent / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
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


def _get_providers() -> dict[str, str]:
    """Lazy-load provider list from config on first access."""
    if not _KEY_PROVIDERS:
        _load_providers_from_config()
    return _KEY_PROVIDERS


def _env_name(provider_name: str) -> str:
    """Convert a provider name to its canonical env-var name."""
    providers = _get_providers()
    key = providers.get(provider_name, provider_name.upper())
    return f"{_ENV_PREFIX}{key}"


def get_key(provider_name: str) -> Optional[str]:
    """Retrieve an API key from the environment.

    Checks (in order):
      1. WIDDX_API_KEY_<PROVIDER> (set by this module during the session)
      2. <PROVIDER>_API_KEY    (e.g. DEEPSEEK_API_KEY — pre-existing env var)
      3. WIDDX_API_KEY         (fallback generic key)

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

    # 3. Generic fallback
    val = os.environ.get("WIDDX_API_KEY")
    return val


def set_key(provider_name: str, api_key: str) -> None:
    """Store an API key in the session environment variable.

    The key is only accessible to the current process
    and is NOT written to config.json or any file.
    """
    os.environ[_env_name(provider_name)] = api_key


def has_key(provider_name: str) -> bool:
    """Check if a key exists for the given provider."""
    return get_key(provider_name) is not None


def prompt_key(provider_name: str, message: Optional[str] = None) -> str:
    """Prompt the user to enter an API key with hidden input.

    Uses getpass so the typed key is NOT shown on screen.
    Automatically stores the key in the session environment.
    Returns the key.
    """
    if message is None:
        message = f"\U0001f511 Enter {provider_name.title()} API Key"
    key = getpass.getpass(f"{message}: ").strip()
    if key:
        set_key(provider_name, key)
    return key


def forget_key(provider_name: str) -> None:
    """Remove a key from the session environment."""
    var = _env_name(provider_name)
    os.environ.pop(var, None)


def list_providers_with_keys() -> list[str]:
    """Return names of providers that have keys set in this session."""
    providers = _get_providers()
    return [p for p in providers if has_key(p)]

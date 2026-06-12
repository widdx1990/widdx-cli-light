"""Command handlers for WIDDX slash commands."""

import json, subprocess, sys, os
from pathlib import Path
from datetime import datetime
from rich.prompt import Prompt as RPrompt

from core.ui.ui import print_system_msg, console
from rich.text import Text
from core.providers.providers import create_provider, fetch_free_models, fetch_ollama_models
from core.config.keychain import prompt_key, forget_key
from core import config


def handle_model(provider, state):
    """Handle /model command — change AI model."""
    # ── Ollama: auto-discover local models ──────────────────────
    if provider.name == "ollama":
        return _handle_ollama_model(provider, state)

    free_list = fetch_free_models()
    print_system_msg(f"Available free models: {', '.join(free_list)}")
    new = RPrompt.ask("Model name", default=provider.model)
    provider.model = new
    state["model"] = f"{provider.name}/{new}"
    print_system_msg(f"Model changed to {new}")
    return provider, state


def _handle_ollama_model(provider, state):
    """Let the user pick from locally-installed Ollama models."""
    from rich.table import Table

    models = fetch_ollama_models(base_url=provider.base_url, force_refresh=True)
    if not models:
        print_system_msg("⚠️  No Ollama models found — is 'ollama serve' running?")
        new = RPrompt.ask("Model name (manual)", default=provider.model)
        provider.model = new
        state["model"] = f"ollama/{new}"
        print_system_msg(f"Model changed to {new}")
        return provider, state

    # Display model table
    table = Table(title=f"Installed Ollama Models ({len(models)})",
                  border_style="dim", header_style="bold #00c896")
    table.add_column("#", style="dim", width=4)
    table.add_column("Model", style="bold white")
    table.add_column("Size", style="#f5a623")
    for i, m in enumerate(models, 1):
        size_str = f"{m['size'] / 1e9:.1f} GB" if m["size"] > 1e9 else f"{m['size'] / 1e6:.0f} MB"
        table.add_row(str(i), m["name"], size_str)
    console.print(table)

    # Let user pick by number or name
    choice = RPrompt.ask(
        "Pick model (# or name)",
        default=provider.model or models[0]["name"],
    )
    # If user typed a number, map to model name
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            choice = models[idx]["name"]
    except ValueError:
        pass  # user typed a name directly

    provider.model = choice
    state["model"] = f"ollama/{choice}"
    print_system_msg(f"Model changed to {choice}")
    return provider, state


def handle_provider(provider, state, cfg):
    """Handle /provider command — switch provider type."""
    print_system_msg(f"Current provider: {provider.name}")
    new_p = RPrompt.ask("Provider (from config / opencode-zen / ollama / openai / deepseek)", default=provider.name)
    if new_p != provider.name:
        if new_p == "openai":
            url = RPrompt.ask("Base URL", default="https://api.openai.com/v1")
            key = prompt_key(new_p) if not new_p == provider.name else ""
            if not key:
                key = RPrompt.ask("API Key (optional)", default="")
            provider = create_provider({
                "provider": {"name": "openai", "model": provider.model,
                             "base_url": url}
            })
        elif new_p == "opencode-zen":
            free_list = fetch_free_models()
            print_system_msg(f"Available: {', '.join(free_list)}")
            model = RPrompt.ask("Free model", default=free_list[0] if free_list else "deepseek-v4-flash-free")
            provider = create_provider({"provider": {"name": "opencode-zen", "model": model}})
        elif new_p == "deepseek":
            key = prompt_key(new_p)
            if not key:
                print_system_msg("No API key provided — check DEEPSEEK_API_KEY env var")
            model = RPrompt.ask("Model", default="deepseek-v4-flash")
            provider = create_provider({
                "provider": {"name": "deepseek", "model": model}
            })
        elif new_p == "ollama":
            url = RPrompt.ask("Ollama URL", default="http://localhost:11434")
            # Auto-discover installed models
            models = fetch_ollama_models(base_url=url, force_refresh=True)
            if models:
                from rich.table import Table
                table = Table(title=f"Installed Ollama Models ({len(models)})",
                              border_style="dim", header_style="bold #00c896")
                table.add_column("#", style="dim", width=4)
                table.add_column("Model", style="bold white")
                table.add_column("Size", style="#f5a623")
                for i, m in enumerate(models, 1):
                    size_str = f"{m['size'] / 1e9:.1f} GB" if m["size"] > 1e9 else f"{m['size'] / 1e6:.0f} MB"
                    table.add_row(str(i), m["name"], size_str)
                console.print(table)
                choice = RPrompt.ask("Pick model (# or name)", default=models[0]["name"])
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        choice = models[idx]["name"]
                except ValueError:
                    pass
                model = choice
                print_system_msg(f"Using model: {model}")
            else:
                print_system_msg("⚠️  No Ollama models found — is 'ollama serve' running?")
                model = RPrompt.ask("Model name (manual)", default="llama3")
            provider = create_provider({
                "provider": {"name": "ollama", "model": model, "base_url": url}
            })
        else:
            # Try to load from config's default
            print_system_msg(f"Unknown provider '{new_p}'. Keeping {provider.name}")
            return provider, state
        state["model"] = f"{provider.name}/{provider.model}"
        print_system_msg(f"Provider changed to {provider.name}")
    return provider, state


def handle_sandbox(tools):
    """Handle /sandbox command — set safe write directory."""
    from pathlib import Path
    path = RPrompt.ask("Path", default=".")
    p = Path(path).resolve()
    tools.configure(str(p))
    print_system_msg(f"Sandbox set to: {p}")
    return str(p)


def handle_mcp():
    """Handle /mcp command — manage MCP servers.

    Usage:
      /mcp              — list servers and tools
      /mcp discover     — auto-discover servers from system
      /mcp add <name> <command> [args...] — add a new server
      /mcp remove <name> — remove a server
    """
    from core.mcp.client import get_mcp_manager, discover_mcp_servers, load_mcp_tokens
    from rich.table import Table
    from rich.prompt import Prompt as RPrompt

    mgr = get_mcp_manager()
    parts = [p.strip() for p in (getattr(handle_mcp, '_last_input', '')).split(None, 1)]
    # We access the actual args from the caller context through a hack
    # Better: parse from the global user input

    # For now, rely on the sub-action being passed
    action = getattr(handle_mcp, '_pending_action', None)

    if action == "discover":
        discovered = discover_mcp_servers(force_refresh=True)
        if not discovered:
            print_system_msg("No MCP servers discovered.")
            return
        table = Table(title=f"Discovered {len(discovered)} MCP servers",
                      border_style="dim", header_style="bold #f5a623")
        table.add_column("Name", style="bold #00c896")
        table.add_column("Command", style="white")
        table.add_column("Status", style="dim")
        for s in discovered:
            name = s["name"]
            exists = "✅" if mgr.get_server(name) else "⬜"
            table.add_row(name, f"{s['command']} {' '.join(s.get('args', []))[:40]}", exists)
        console.print(table)
        return

    # Default: show current servers
    mgr.start()
    servers = mgr.get_servers()

    if not servers:
        print_system_msg("No MCP servers configured. Use '!mcp discover' to find available ones.")
        return

    for conn in servers:
        if conn.is_connected:
            status = "✅ connected"
        elif conn._proc is None:
            status = "⏸️  pending (lazy)"
        else:
            status = f"❌ {conn.error or 'disconnected'}"
        tools_list = conn.get_tool_definitions()
        table = Table(title=f"MCP Server: {conn.name} [{status}]",
                      border_style="dim", header_style="bold #f5a623")
        table.add_column("Tool", style="bold #00c896")
        table.add_column("Description", style="white")
        for td in tools_list:
            desc = td.get("description", "").replace(f"[MCP {conn.name}] ", "")
            table.add_row(td["name"], desc)
        console.print(table)
    console.print()
    print_system_msg("Sub-commands: /mcp discover, /mcp add <name> <cmd> [args], /mcp remove <name>")


def handle_agent(_state):
    """Handle /agent command — Expert Team is now always active."""
    print_system_msg("Expert Team is always active — type your task and it will be handled automatically")
    return _state


def handle_load(provider, state, messages, args: str):
    """Handle /load command — load session from another project directory."""
    from pathlib import Path
    from core.project.state import load_session

    path = args.strip() if args else ""
    if not path:
        path = RPrompt.ask("Project path", default=".")
    p = Path(path).resolve()
    if not p.is_dir():
        print_system_msg(f"Directory not found: {p}")
        return provider, state, messages

    session = load_session(p)
    if not session:
        print_system_msg(f"No session found in {p}")
        return provider, state, messages

    new_messages = session.get("messages", [])
    new_state_data = session.get("state", {})
    new_state = dict(state)
    new_state["cost"] = new_state_data.get("cost", 0.0)
    new_state["turns"] = new_state_data.get("turns", 0)
    if new_state_data.get("model"):
        new_state["model"] = new_state_data["model"]

    msg_count = len(new_messages)
    print_system_msg(f"Loaded session from {p} ({msg_count} messages, ${new_state['cost']:.4f}, {new_state['turns']} turns)")
    return provider, new_state, new_messages


def handle_undo():
    """Handle /undo command — undo last WIDDX commit."""
    from pathlib import Path
    from core.project.git import undo_last_commit
    msg = undo_last_commit(Path().resolve())
    print_system_msg(msg)
    return msg


def handle_doctor():
    """Run a system health check and display results."""
    from rich.table import Table
    from core.mcp.client import get_mcp_manager, discover_mcp_servers

    table = Table(title="WIDDX System Health",
                  border_style="dim", header_style="bold #f5a623")
    table.add_column("Check", style="bold #00c896")
    table.add_column("Status", style="white")
    table.add_column("Detail", style="dim")

    checks = []

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 10)
    checks.append(("Python", "✅" if ok else "❌", f"{py_ver} (need >= 3.10)"))

    # Git
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        git_ver = r.stdout.strip() if r.returncode == 0 else "not found"
        checks.append(("Git", "✅" if r.returncode == 0 else "❌", git_ver[:40]))
    except Exception:
        checks.append(("Git", "❌", "not found"))

    # Node.js
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        node_ver = r.stdout.strip() if r.returncode == 0 else "not found"
        checks.append(("Node.js", "✅" if r.returncode == 0 else "❌", node_ver))
    except Exception:
        checks.append(("Node.js", "❌", "not found"))

    # uvx (needed for fetch + sqlite MCP)
    try:
        r = subprocess.run(["uvx", "--version"], capture_output=True, text=True, timeout=5)
        uvx_ver = r.stdout.strip()[:30] if r.returncode == 0 else "not found"
        checks.append(("uvx", "✅" if r.returncode == 0 else "❌", uvx_ver))
    except Exception:
        checks.append(("uvx", "❌", "not found (pip install uv)"))

    # MCP servers
    mgr = get_mcp_manager()
    checks.append(("MCP registered", "ℹ️", f"{mgr.server_count} server(s)"))
    checks.append(("MCP connected", "ℹ️", f"{mgr.tool_count} tool(s) available"))

    # Memory system
    from core.memory import MemoryStore
    mem = MemoryStore()
    checks.append(("Memory", "ℹ️", f"{mem.total()} fact(s) stored"))

    # Config
    from core.config.settings import load as load_cfg
    cfg = load_cfg()
    provider_name = cfg.get("provider", {}).get("name", "?")
    provider_model = cfg.get("provider", {}).get("model", "?")
    checks.append(("Provider", "ℹ️", f"{provider_name}/{provider_model}"))

    # Skills
    from core.skills import skill_manager
    checks.append(("Skills", "ℹ️", f"{len(skill_manager.list_all())} skill(s) loaded"))

    # Tests
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--ignore=test_features.py", "--tb=no", "-q"],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )
        if r.returncode == 0:
            last = [l for l in r.stdout.strip().splitlines() if l][-1]
            checks.append(("Tests", "✅", last))
        else:
            checks.append(("Tests", "❌", f"{r.returncode} failure(s)"))
    except Exception as e:
        checks.append(("Tests", "❌", str(e)))

    for name, status, detail in checks:
        table.add_row(name, status, detail)
    console.print(table)


def handle_export(messages):
    """Export the current conversation as a Markdown file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"chat_export_{ts}.md")

    from core import config as cfg_mod
    cfg = cfg_mod.load()
    model = cfg.get("provider", {}).get("model", "unknown")

    lines = [
        f"# WIDDX Chat Export — {ts}",
        f"Model: {model}",
        f"Messages: {len(messages)}",
        "",
        "---",
        "",
    ]

    for m in messages:
        role = m.get("role", "?").upper()
        content = m.get("content", "")
        if m.get("tool_calls"):
            names = ", ".join(tc.get("function", {}).get("name", "?")
                            for tc in m["tool_calls"])
            content = f"[Tool calls: {names}]"

        if role == "SYSTEM":
            lines.append(f"> **{role}**: {content[:200]}")
        else:
            lines.append(f"### {role}")
            lines.append("")
            lines.append(content)
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print_system_msg(f"Exported {len(messages)} messages to {path}")
    return path


def handle_version():
    """Show version information."""
    from rich.table import Table

    # Read version from pyproject.toml
    try:
        import tomllib  # Python 3.11+
        p = Path(__file__).parent.parent.parent / "pyproject.toml"
        if p.exists():
            with open(p, "rb") as f:
                ver = tomllib.load(f).get("project", {}).get("version", "3.0.0")
        else:
            ver = "3.0.0"
    except ImportError:
        try:
            import tomli as tomllib
            p = Path(__file__).parent.parent.parent / "pyproject.toml"
            if p.exists():
                with open(p, "rb") as f:
                    ver = tomllib.load(f).get("project", {}).get("version", "3.0.0")
            else:
                ver = "3.0.0"
        except Exception:
            ver = "3.0.0"
    except Exception:
        ver = "3.0.0"

    table = Table(title="WIDDX", border_style="dim", header_style="bold #f5a623")
    table.add_column("Field", style="bold #00c896")
    table.add_column("Value", style="white")
    table.add_row("Version", ver)
    table.add_row("Python", f"{sys.version_info.major}.{sys.version_info.minor}")
    table.add_row("Platform", sys.platform)
    table.add_row("CWD", os.getcwd())
    from core.config.settings import get_config_path
    table.add_row("Config", str(get_config_path()))
    console.print(table)


def handle_permissions(cmd: str = ""):
    """Handle /permissions command — view/change permission level."""
    from core.permissions import get_permission_manager, PermissionLevel
    from rich.table import Table

    pm = get_permission_manager()
    parts = cmd.strip().split(None, 1) if cmd else []

    if not parts:
        # Show current status
        table = Table(title="Permissions", border_style="dim", header_style="bold #f5a623")
        table.add_column("Field", style="bold #00c896")
        table.add_column("Value", style="white")
        table.add_row("Level", pm.level.value)
        table.add_row("Status", pm.status())
        remembered = pm._remembered
        if remembered:
            allowed = [k for k, v in remembered.items() if v]
            denied = [k for k, v in remembered.items() if not v]
            if allowed:
                table.add_row("Allowed", ", ".join(allowed))
            if denied:
                table.add_row("Denied", ", ".join(denied))
        console.print(table)
        console.print(Text(
            "  Usage: /permissions level <name>  |  /permissions forget [tool]",
            style="dim",
        ))
        return

    action = parts[0]
    if action == "level" and len(parts) > 1:
        try:
            pm.level = PermissionLevel(parts[1])
            print_system_msg(f"Permission level set to {parts[1]}")
        except ValueError:
            valid = [lvl.value for lvl in PermissionLevel]
            print_system_msg(f"Invalid level. Choose: {', '.join(valid)}")
    elif action == "forget":
        tool = parts[1] if len(parts) > 1 else None
        pm.forget(tool)
        print_system_msg(f"Forgot permissions{' for ' + tool if tool else ' (all)'}")
    else:
        print_system_msg(f"Unknown: /permissions {action}")

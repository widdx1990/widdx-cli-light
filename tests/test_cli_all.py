"""Comprehensive non-interactive connectivity test for the WIDDX CLI.

Runs every slash command without starting the main loop, using
CLIApp internals directly. All interactive prompts are bypassed
by passing explicit arguments.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Command test matrix ───────────────────────────────────────────
# Each entry: (command, should_exit)
COMMANDS = [
    ("/help", False),
    ("/clear", False),
    ("/model", False),
    ("/provider opencode-zen", False),   # preset bypasses interactive prompt
    ("/tools", False),
    ("/skills", False),
    ("/history", False),
    ("/save", False),
    ("/load .", False),
    ("/export", False),
    ("/remember test-fact-from-cli-test", False),
    ("/memories", False),
    ("/manifest", False),
    ("/reasoning", False),
    ("/debug", False),
    ("/doctor", False),
    ("/undo", False),
    ("/proxy", False),
    ("/sandbox .", False),
    ("/mcp", False),
    ("/gguf", False),
    ("/branch list", False),
    ("/version", False),
    ("/permissions", False),
    ("/apikey show", False),
]


@pytest.fixture(scope="module")
def cli_app():
    """Create ONE CLIApp for the entire test module to save startup time."""
    from cli.app import CLIApp
    app = CLIApp()
    app.startup()
    return app


@pytest.mark.parametrize("cmd,should_exit", COMMANDS)
def test_cli_command(cmd, should_exit, cli_app):
    """Each slash command runs without error."""
    try:
        cli_app.cmds.handle(cmd.strip(), cli_app.provider, cli_app.state, cli_app.messages)
    except SystemExit:
        if should_exit:
            return  # expected exit
        pytest.fail(f"Unexpected SystemExit from command: {cmd}")
    except Exception as exc:
        pytest.fail(f"Command '{cmd}' raised {type(exc).__name__}: {exc}")


def test_exit_command(cli_app):
    """Exit command raises SystemExit (expected)."""
    with pytest.raises(SystemExit):
        cli_app.cmds.handle("/exit", cli_app.provider, cli_app.state, cli_app.messages)

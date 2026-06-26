"""CLI health-check tests — verifies CLIApp doctor command and module loading."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from cli.app import CLIApp


@pytest.fixture(scope="module")
def cli_app():
    """Create ONE CLIApp for the test module to save startup time."""
    app = CLIApp()
    app.startup()
    return app


def test_doctor_runs_without_error(cli_app):
    """Doctor command runs and produces diagnostic output."""
    try:
        cli_app.cmds.handle("/doctor", cli_app.provider, cli_app.state, cli_app.messages)
    except SystemExit:
        pytest.fail("/doctor raised unexpected SystemExit")
    except Exception as exc:
        pytest.fail(f"/doctor raised {type(exc).__name__}: {exc}")


def test_cli_app_has_provider(cli_app):
    """CLI app has a provider after startup."""
    assert cli_app.provider is not None, "Provider must be set after startup"


def test_cli_app_has_state(cli_app):
    """CLI app has initialized state after startup."""
    assert isinstance(cli_app.state, dict), "State must be a dict"
    assert "model" in cli_app.state or "turns" in cli_app.state, \
        "State should have model or turns keys"


def test_cli_app_cmds_registered(cli_app):
    """Command handler is properly registered."""
    assert cli_app.cmds is not None, "Command handler must be set"
    assert hasattr(cli_app.cmds, 'handle'), "Command handler must have handle method"

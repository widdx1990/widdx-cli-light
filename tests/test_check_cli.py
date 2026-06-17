"""CLI health-check tests — verifies CLIApp doctor command and module loading."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from cli.app import CLIApp

def test_doctor():
    app = CLIApp()
    # Initialize without full run loop
    app.cfg = None  # placeholder, will be set in __init__
    # Actually instantiate properly
    app = CLIApp()
    # Run startup to initialize components
    app.startup()
    # Invoke doctor command via CLICommands
    app.cmds.handle("/doctor", app.provider, app.state, app.messages)

if __name__ == "__main__":
    test_doctor()

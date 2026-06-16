"""Entry point to run WIDDX with Textual TUI (script).

Moved under `scripts/` and adjusted `sys.path` to reference project root.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tui.app import run_tui

if __name__ == "__main__":
    run_tui()

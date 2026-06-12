"""Entry point to run WIDDX with Textual TUI.

Usage:
    python run_textual.py
    python -m core.ui.textual_app
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tui.app import run_tui

if __name__ == "__main__":
    run_tui()

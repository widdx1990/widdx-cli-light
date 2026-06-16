"""Entry point to run WIDDX with Textual TUI.

This file forwards execution into the scripts/ package while preserving the old root entrypoint.
"""

from scripts.run_textual import run_tui

if __name__ == "__main__":
    run_tui()

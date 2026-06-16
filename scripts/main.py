"""WIDDX — Terminal AI Chat Tool (script entrypoint).

This script was moved into `scripts/` to keep top-level tidy.
It ensures the repo root is on `sys.path` so package imports work.
"""

import sys
from pathlib import Path

# Ensure project root (parent of this scripts/ dir) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.app import run

if __name__ == "__main__":
    run()

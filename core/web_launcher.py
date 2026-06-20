"""Launcher for Web UI — called by the widdx-web entry point."""

import sys
from pathlib import Path

# Add project root and scripts dir to sys.path
ROOT = str(Path(__file__).resolve().parent.parent)
SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")
for p in [ROOT, SCRIPTS]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.web.server import run

if __name__ == "__main__":
    run()

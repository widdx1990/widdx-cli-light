"""Launcher for Web UI — called by the widdx-web entry point."""

import sys
from pathlib import Path

try:
    from core._path import ensure_project_root
except ImportError:
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from core._path import ensure_project_root

from scripts.web.server import run

if __name__ == "__main__":
    run()

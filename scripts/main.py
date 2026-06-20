"""WIDDX — Terminal AI Chat Tool (script entrypoint).

This script was moved into `scripts/` to keep top-level tidy.
It ensures the repo root is on `sys.path` so package imports work.
"""

import sys
try:
    from core._path import ensure_project_root
except ImportError:
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from core._path import ensure_project_root
from cli.app import run

if __name__ == "__main__":
    run()

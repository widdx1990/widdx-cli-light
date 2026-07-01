"""CLI launcher for `python -m core` and `widdx` command."""
import sys
try:
    from core._path import ensure_project_root  # noqa: F401
except ImportError:
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

from scripts.web_app import main as run

if __name__ == "__main__":
    run()

"""CLI entry point for the `widdx` command.

Bridges the installed package to the new ``cli.app`` runner.
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

from cli.app import run as _run

def run():
    """Main CLI entry point."""
    _run()

if __name__ == "__main__":
    run()

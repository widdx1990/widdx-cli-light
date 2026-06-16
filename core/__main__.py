"""CLI launcher for `python -m core` and `widdx` command."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
if root not in sys.path:
    sys.path.insert(0, str(root))

from cli.app import run

if __name__ == "__main__":
    run()

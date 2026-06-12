"""CLI launcher for `python -m core` and `widdx` command."""
import sys
from pathlib import Path

# Ensure project root is on path (works both installed and from source)
root = Path(__file__).resolve().parent.parent
if root not in sys.path:
    sys.path.insert(0, str(root))

from main import run
run()

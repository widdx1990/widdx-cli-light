"""CLI entry point for the `widdx` command.

This file bridges the installed package to the `main.py` runner.
It ensures the project root is on sys.path whether running from
source or from an installed package.
"""
import sys
from pathlib import Path

# When installed, add the source root so main.py can find its relatives
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from main import run

if __name__ == "__main__":
    run()

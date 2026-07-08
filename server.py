"""WIDDX Nexus — Web Server entry point.

A thin wrapper around ``scripts.web.server``.
Usage::

    python server.py              # → http://localhost:8000
    python server.py --port 9000  # → http://localhost:9000
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from scripts.web_app import main  # noqa: E402

if __name__ == "__main__":
    main()

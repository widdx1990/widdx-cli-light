"""WIDDX Nexus — Web UI launcher.

Usage:
    python scripts/web_app.py             # → http://localhost:8000
    widdx-web                              # بعد التثبيت
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

host = "0.0.0.0"
port = 8000

for i, arg in enumerate(sys.argv):
    if arg == "--host" and i + 1 < len(sys.argv):
        host = sys.argv[i + 1]
    elif arg == "--port" and i + 1 < len(sys.argv):
        port = int(sys.argv[i + 1])

from scripts.web.server import run as _run

# Enable diagnostics
try:
    from core.diagnostics import error_collector
    error_collector.enable()
except Exception:
    pass

if __name__ == "__main__":
    _run(host=host, port=port)

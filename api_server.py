"""WIDDX Cortex — REST API Server.

This root entrypoint forwards to `scripts/api_server.py`, keeping the project
layout tidy while preserving backward compatibility.
"""

from scripts.api_server import main

if __name__ == "__main__":
    main()

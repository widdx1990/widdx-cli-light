"""WIDDX — Terminal AI Chat Tool.

This file forwards execution into the scripts/ package while preserving the old root entrypoint.
"""

from scripts.main import run

if __name__ == "__main__":
    run()

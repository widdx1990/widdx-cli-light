"""Centralized logging setup — consistent format and level across all entry points.

Usage in entry points::

    from core.log_setup import setup_logging
    setup_logging("widdx.cli")
"""

import logging
import sys

_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(name: str = "widdx", level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with stdout handler and return a named logger.

    Safe to call multiple times — only adds one handler.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)
    return logging.getLogger(name)

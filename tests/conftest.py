"""Pytest configuration — path setup + KnowledgeBase cleanup."""
import sys
from pathlib import Path

# Ensure project root is in sys.path for ALL tests in this directory
_project_root = Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest


@pytest.fixture(autouse=True)
def clear_knowledge():
    """Clear persistent KnowledgeBase before each test to avoid cross-test contamination."""
    try:
        from core.uil.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.clear()
    except Exception:
        pass  # knowledge module may not be importable — that's fine
    yield

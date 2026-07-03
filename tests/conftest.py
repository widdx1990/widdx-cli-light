"""Pytest configuration — path setup + KnowledgeBase cleanup + shared fixtures."""
import sys
from pathlib import Path

# Ensure project root is in sys.path for ALL tests in this directory
_project_root = Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest


def pytest_configure(config):
    """Register asyncio markers for Textual-based TUI tests."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test (Textual, etc.)"
    )


class MockProvider:
    """Duck-typed mock LLM provider for tests.

    Attributes:
        chat_response: What ``chat()`` returns as (content, tool_calls).
        stream_events: What ``stream()`` yields (list of event dicts).
    """

    def __init__(self):
        self.name = "mock"
        self.model = "mock-model"
        self.chat_response: tuple[str, list] = ("Mock reply", [])
        self.stream_events: list[dict] = []
        self.api_key = "test-key"

    def chat(self, messages: list, tools: list | None = None,
             temperature: float = 0.7) -> tuple[str, list]:
        return self.chat_response

    def stream(self, messages: list, tools: list | None = None,
               temperature: float = 0.7):
        yield from self.stream_events


@pytest.fixture
def mock_provider():
    """Create a fresh MockProvider for each test."""
    return MockProvider()


@pytest.fixture(autouse=True)
def permissive_for_tests():
    """Pre-seed permission singleton to PERMISSIVE for all tests.

    Without this, any test that triggers a tool execution (bash, write,
    browser, etc.) will hit an interactive Rich prompt and fail with
    ``OSError: reading from stdin while output is captured`` because
    pytest captures stdin/stdout.
    """
    try:
        import core.permissions as _perms
        if _perms._permission_manager is None:
            pm = _perms.PermissionManager()
            pm._level = _perms.PermissionLevel.PERMISSIVE
            _perms._permission_manager = pm
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def clear_knowledge():
    """Clear persistent KnowledgeBase before each test to avoid cross-test contamination.

    .. note::
       Kept as ``autouse=True`` because the KnowledgeBase is a process-level
       singleton and many UIL/Brain tests depend on a clean slate.
       Removing autouse causes ~16 test regressions.
    """
    try:
        from core.uil.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.clear()
    except Exception:
        pass
    yield

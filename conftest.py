"""Pytest configuration — ensures clean KnowledgeBase before each test."""
import pytest
import os
from pathlib import Path


@pytest.fixture(autouse=True)
def clear_knowledge():
    """Clear persistent KnowledgeBase before each test to avoid cross-test contamination."""
    from core.uil.knowledge import KnowledgeBase
    kb = KnowledgeBase()
    kb.clear()
    yield

"""Shared utilities used across the WIDDX codebase.

Centralizes helpers that were previously duplicated between modules.
"""

import re
from typing import Optional


def parse_frontmatter(text: str, nested_metadata: bool = False) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown text.

    Args:
        text: Full markdown text with optional frontmatter.
        nested_metadata: If True, parse nested ``metadata:`` keys under a
            ``metadata`` sub-dict. Used by MemoryStore for type/classification.
            If False, return all keys as flat top-level entries.
            Used by SkillManager.

    Returns:
        (metadata_dict, body_text).
    """
    meta: dict = {}
    body = text
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if not m:
        return meta, body.strip()

    front = m.group(1)
    body = m.group(2)

    if nested_metadata:
        # MemoryStore-style: nested metadata block
        current_key: Optional[str] = None
        meta["metadata"] = {}
        for line in front.splitlines():
            if line.startswith("metadata:"):
                current_key = "metadata"
            elif current_key == "metadata":
                mm = re.match(r'\s+(\w+):\s*(.*)', line)
                if mm:
                    meta["metadata"][mm.group(1)] = mm.group(2).strip()
            else:
                mm = re.match(r'(\w+):\s*(.*)', line)
                if mm:
                    key, val = mm.group(1), mm.group(2).strip()
                    if key not in ("metadata",):
                        meta[key] = val
    else:
        # SkillManager-style: flat key: value only
        for line in front.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()

    return meta, body.strip()


def strip_frontmatter(text: str) -> str:
    """Remove frontmatter, return only the body."""
    m = re.match(r'^---\s*\n.*?\n---\s*\n(.*)', text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def to_slug(name: str, max_len: int = 80) -> str:
    """Convert a name to a kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:max_len]


def get_last_turn(messages: list) -> dict | None:
    """Extract the last user+assistant exchange from messages.

    Used by MemoryLearner and other modules that need the most
    recent turn for analysis or extraction.
    """
    last_user = None
    last_assistant = None
    for m in reversed(messages):
        if m.get("role") == "assistant" and last_assistant is None:
            content = (m.get("content") or "").strip()
            if content and not content.startswith("[Agent completed"):
                last_assistant = content
        elif m.get("role") == "user":
            last_user = m.get("content")
            break
    if last_user and last_assistant:
        return {"user": last_user, "assistant": last_assistant}
    return None

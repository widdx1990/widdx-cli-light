"""Persistent Memory System for WIDDX.

Two-tier architecture:
  1. **Global memory** — ``~/.widdx/memory/`` — shared across ALL projects.
     Facts learned in one project are available in every other project.
     This is the DEFAULT when ``MemoryStore()`` is called without arguments.

  2. **Project memory** — ``<project>/.widdx/memory/`` — facts specific to one
     project.  Created by passing ``project_dir=...``.

This means WIDDX learns once and remembers everywhere — continuous
self-improvement across sessions, projects, and even users (when deployed).

Each memory is a markdown file with frontmatter:
  ---
  name: <short-kebab-case>
  description: <one-line summary>
  metadata:
    type: user | feedback | project | reference
  ---
  <the fact>

MEMORY.md serves as the index with one-line pointers.
"""

import os, json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .utils import parse_frontmatter, strip_frontmatter, to_slug


MEMORY_DIR_NAME = "memory"
INDEX_FILE = "MEMORY.md"


class MemoryStore:
    """Persistent memory store backed by markdown files with frontmatter.

    Args:
        project_dir: If given, stores memory in ``<project>/.widdx/memory/``.
                     If ``None`` (default), stores in ``~/.widdx/memory/``
                     (global — shared across all projects).
    """

    def __init__(self, project_dir: str | Path | None = None):
        if project_dir is None:
            # Global memory — shared across ALL projects
            self.root = Path.home() / ".widdx"
        else:
            self.root = Path(project_dir).resolve()
        self.widdx_dir = self.root / ".widdx" if project_dir else self.root
        self.memory_dir = self.widdx_dir / MEMORY_DIR_NAME
        self.index_path = self.widdx_dir / INDEX_FILE
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ── CRUD ───────────────────────────────────────────────────────────

    def save(self, name: str, content: str, metadata: dict | None = None) -> Path:
        """Save a memory. Updates MEMORY.md index."""
        slug = to_slug(name)
        filepath = self.memory_dir / f"{slug}.md"

        meta = metadata or {}
        meta_str = ""
        if meta:
            meta_lines = ["metadata:"]
            for k, v in meta.items():
                meta_lines.append(f"  {k}: {v}")
            meta_str = "\n" + "\n".join(meta_lines)

        frontmatter = (
            f"---\n"
            f"name: {slug}\n"
            f"description: {content[:80].strip()}\n"
            f"{meta_str}\n"
            f"---\n"
        )
        full = frontmatter + "\n" + content
        filepath.write_text(full, encoding="utf-8")

        # Update index
        self._update_index(slug, content[:60])

        return filepath

    def get(self, name: str) -> str | None:
        """Read a memory by name/slug. Returns None if not found."""
        slug = to_slug(name)
        filepath = self.memory_dir / f"{slug}.md"
        if not filepath.exists():
            return None
        text = filepath.read_text(encoding="utf-8")
        # Strip frontmatter
        body = strip_frontmatter(text)
        return body

    def delete(self, name: str) -> bool:
        """Delete a memory. Returns True if deleted."""
        slug = to_slug(name)
        filepath = self.memory_dir / f"{slug}.md"
        if not filepath.exists():
            return False
        filepath.unlink()
        self._rebuild_index()
        return True

    def list_all(self) -> list[dict]:
        """Return all memories as [{name, description, type, path}, ...]."""
        memories = []
        for f in sorted(self.memory_dir.glob("*.md")):
            meta, _ = parse_frontmatter(f.read_text(encoding="utf-8"), nested_metadata=True)
            memories.append({
                "name": meta.get("name", f.stem),
                "description": meta.get("description", ""),
                "type": meta.get("metadata", {}).get("type", "unknown"),
                "path": str(f.relative_to(self.root)),
            })
        return memories

    def search(self, query: str, semantic: bool = False) -> list[dict]:
        """Search memory contents by keyword. Set semantic=True for vector similarity search."""
        # ── Semantic search (vector_memory) ─────────────────
        if semantic:
            try:
                from core.vector_memory import VectorMemoryStore
                vstore = VectorMemoryStore()
                results = vstore.search(query, top_k=10)
                if results:
                    return [{
                        "name": r.get("name", "?"),
                        "description": r.get("content", "")[:80],
                        "snippet": r.get("content", "")[:200],
                        "score": r.get("score", 0.0),
                    } for r in results]
            except Exception:
                pass

        # ── Keyword fallback ────────────────────────────────
        query_lower = query.lower()
        results = []
        for f in self.memory_dir.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            if query_lower in text.lower():
                meta, _ = parse_frontmatter(text, nested_metadata=True)
                body = strip_frontmatter(text)
                results.append({
                    "name": meta.get("name", f.stem),
                    "description": meta.get("description", "")[:80],
                    "snippet": body[:200],
                })
        return results

    def total(self) -> int:
        """Number of stored memories."""
        return len(list(self.memory_dir.glob("*.md")))

    # ── Index management ──────────────────────────────────────────────

    def _update_index(self, slug: str, description: str):
        """Append or update one line in MEMORY.md."""
        line = f"- [{slug}]({MEMORY_DIR_NAME}/{slug}.md) — {description.strip()}"
        if self.index_path.exists():
            text = self.index_path.read_text(encoding="utf-8")
            # Replace existing line for this slug
            for i, existing in enumerate(text.splitlines()):
                if existing.strip().startswith(f"- [{slug}]"):
                    lines = text.splitlines()
                    lines[i] = line
                    self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    return
            # Append
            with self.index_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            self.index_path.write_text(line + "\n", encoding="utf-8")

    def _rebuild_index(self):
        """Regenerate MEMORY.md from all memory files."""
        lines = []
        for f in sorted(self.memory_dir.glob("*.md")):
            meta, _ = parse_frontmatter(f.read_text(encoding="utf-8"), nested_metadata=True)
            desc = meta.get("description", "")
            lines.append(f"- [{meta.get('name', f.stem)}]({MEMORY_DIR_NAME}/{f.name}) — {desc}")
        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


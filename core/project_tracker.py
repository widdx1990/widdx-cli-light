"""Project Tracker — persistent project plan, design, tasks, and roadmap.

Stores four markdown files in ``.widdx/``:
  - **PLAN.md**    — current implementation plan (what's being worked on now)
  - **DESIGN.md**  — architecture decisions, design patterns, rationale
  - **TASKS.md**   — task list with status (todo / in-progress / done)
  - **ROADMAP.md** — milestones, progress, what's next

On startup these are loaded into system context so WIDDX always knows
where it is and what it's doing.  An ``update_project_doc`` tool lets the
AI update them as work progresses.
"""

from pathlib import Path
import logging

logger = logging.getLogger("widdx.project_tracker")

_DOC_NAMES = ("PLAN.md", "DESIGN.md", "TASKS.md", "ROADMAP.md")

_TEMPLATES: dict[str, str] = {
    "PLAN.md": """# Project Plan

> Auto-managed by WIDDX. Updated as the project evolves.

## Current Goal

*Describe what you're working on right now.*

## Implementation Steps

1. *Step 1 — description*
2. *Step 2 — description*
3. *Step 3 — description*

## Completed Milestones

- *Milestone 1*
""",
    "DESIGN.md": """# Design Decisions

> Architecture and design rationale, automatically tracked.

## Architecture

*Overall architecture description.*

## Key Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| *choice* | *why* | *date* |

## Data Flow

*How data moves through the system.*
""",
    "TASKS.md": """# Tasks

> Auto-managed by WIDDX. Update via `update_project_doc` tool.

## In Progress

- [ ] *Task description*

## Todo

- [ ] *Task description*

## Done

- [x] *Task description*
""",
    "ROADMAP.md": """# Roadmap

> Project milestones and progress, automatically tracked.

## Current Status

- **Phase:** *current phase*
- **Progress:** *0%*

## Milestones

- [ ] *Milestone 1*
- [ ] *Milestone 2*

## Completed

- *What was done*
""",
}


def _widdx_dir(project_dir: Path) -> Path:
    p = project_dir.resolve() / ".widdx"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─── Initialisation ────────────────────────────────────────────────────────

def ensure_docs(project_dir: Path) -> list[str]:
    """Create any missing doc files from templates.

    Returns a list of doc names that were created (empty if all existed).
    """
    created: list[str] = []
    wd = _widdx_dir(project_dir)
    for name in _DOC_NAMES:
        path = wd / name
        if not path.exists():
            template = _TEMPLATES.get(name, f"# {name.replace('.md', '')}\n\n"
                                             f"Auto-managed by WIDDX.\n")
            path.write_text(template, encoding="utf-8")
            created.append(name)
    if created:
        logger.info("Created project docs: %s", ", ".join(created))
    return created


# ─── Read ──────────────────────────────────────────────────────────────────

def load_docs(project_dir: Path) -> dict[str, str]:
    """Load all four doc files as a dict of ``{name: content}``.

    Missing files are silently skipped.
    """
    result: dict[str, str] = {}
    wd = _widdx_dir(project_dir)
    for name in _DOC_NAMES:
        path = wd / name
        if path.exists():
            try:
                result[name] = path.read_text(encoding="utf-8")
            except Exception as e:
                logger.debug("Failed to read %s: %s", name, e)
    return result


def build_context_block(project_dir: Path) -> str | None:
    """Build a ``[PROJECT DOCS]`` string for injection as system message.

    Returns None if no docs exist yet.
    Augmented with RAG-relevant project context when available.
    """
    docs = load_docs(project_dir)
    if not docs:
        return None

    lines: list[str] = []
    for name in _DOC_NAMES:
        content = docs.get(name, "").strip()
        if not content:
            continue
        # Use first line (title) as heading, next few non-empty lines as preview
        title_line = content.split("\n")[0].lstrip("#").strip()
        lines.append(f"\n=== {title_line} ===")
        # Keep the full content (it's all relevant context)
        body = content.strip()
        lines.append(body)

    # ── RAG augmentation: search project docs ─────────────────
    try:
        from core.rag import RAGStore
        rag = RAGStore(str(project_dir))
        # Build a query from the concatenated docs
        query = " ".join(docs.get(n, "")[:200] for n in _DOC_NAMES if docs.get(n, "").strip())
        if query:
            rags = rag.search(query, top_k=3)
            if rags:
                lines.append("\n=== RAG Context ===")
                for _score, doc in rags:
                    snippet = doc.get("content", "")[:300]
                    if snippet:
                        lines.append(f"  • {snippet}")
    except Exception:
        pass

    if not lines:
        return None
    return "\n".join(lines)


# ─── Write ─────────────────────────────────────────────────────────────────

def update_doc(project_dir: Path, doc_name: str, content: str) -> bool:
    """Update one of the project docs.

    Args:
        project_dir: Project root.
        doc_name: One of ``PLAN.md``, ``DESIGN.md``, ``TASKS.md``, ``ROADMAP.md``.
        content: New markdown content.

    Returns:
        True on success, False if the doc name is invalid.
    """
    name = doc_name.strip()
    if name not in _DOC_NAMES:
        return False
    path = _widdx_dir(project_dir) / name
    try:
        path.write_text(content.strip() + "\n", encoding="utf-8")
        logger.info("Updated %s (%d chars)", name, len(content))
        return True
    except Exception as e:
        logger.warning("Failed to update %s: %s", name, e)
        return False


# ─── Tool definition for the AI ────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "update_project_doc",
    "description": (
        "Update the project's PLAN, DESIGN, TASKS, or ROADMAP. "
        "Use this when you make progress, change direction, complete tasks, "
        "or make design decisions — so WIDDX never loses track of the project."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "doc": {
                "type": "string",
                "enum": ["PLAN.md", "DESIGN.md", "TASKS.md", "ROADMAP.md"],
                "description": "Which document to update",
            },
            "content": {
                "type": "string",
                "description": "Full new markdown content for the document",
            },
        },
        "required": ["doc", "content"],
    },
}


def handle_update_project_doc(doc: str, content: str) -> str:
    """Handler for the ``update_project_doc`` tool."""
    from pathlib import Path
    ok = update_doc(Path.cwd().resolve(), doc, content)
    if ok:
        return f"✅ Updated {doc}"
    return f"❌ Invalid doc name: {doc}. Use one of: {', '.join(_DOC_NAMES)}"

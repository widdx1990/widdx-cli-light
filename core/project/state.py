"""Project state management — session persistence, auto-indexing, and context recovery.

Saves/loads from <project-dir>/.widdx/ :
  session.json  — conversation messages + state
  index.json    — file tree + function/class definitions
"""

import json
import re, logging
from pathlib import Path

logger = logging.getLogger("widdx.project.state")


# ── paths ────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "exclude_from_index": [],
    "project_instructions": "",
    "auto_commit": True,
}


def _widdx_dir(project_dir: str | Path) -> Path:
    p = Path(project_dir).resolve() / ".widdx"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _session_path(project_dir: str | Path) -> Path:
    return _widdx_dir(project_dir) / "session.json"


def _index_path(project_dir: str | Path) -> Path:
    return _widdx_dir(project_dir) / "index.json"


def _config_path(project_dir: str | Path) -> Path:
    return _widdx_dir(project_dir) / "config.json"


# ── project config (.widdx/config.json) ───────────────────────────────────

def load_project_config(project_dir: str | Path | None = None) -> dict:
    """Load per-project config from .widdx/config.json. Returns defaults if missing."""
    if project_dir is None:
        project_dir = Path().resolve()
    path = _config_path(project_dir)
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except Exception as e:
        logger.warning("Failed to load project config from %s: %s", path, e)
        return dict(DEFAULT_CONFIG)


def save_project_config(config: dict, project_dir: str | Path | None = None):
    """Save per-project config to .widdx/config.json."""
    if project_dir is None:
        project_dir = Path().resolve()
    path = _config_path(project_dir)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


# ── session persistence ──────────────────────────────────────────────────

def save_session(messages: list, state: dict, project_dir: str | Path | None = None):
    """Save conversation messages + runtime state to .widdx/session.json."""
    if project_dir is None:
        project_dir = Path().resolve()
    data = {
        "messages": _serializable_messages(messages),
        "state": {
            "model": state.get("model", ""),
            "cost": state.get("cost", 0.0),
            "turns": state.get("turns", 0),
        },
    }
    path = _session_path(project_dir)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session(project_dir: str | Path | None = None) -> dict | None:
    """Load previous session. Returns None if no session exists."""
    if project_dir is None:
        project_dir = Path().resolve()
    path = _session_path(project_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load session from %s: %s", path, e)
        return None


def has_session(project_dir: str | Path | None = None) -> bool:
    """Check if a previous session exists."""
    if project_dir is None:
        project_dir = Path().resolve()
    return _session_path(project_dir).exists()


# ── project indexing ─────────────────────────────────────────────────────

IGNORE_DIRS = {".widdx", ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
               ".idea", ".vscode", ".DS_Store"}
IGNORE_EXTS = {".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin"}


def build_index(project_dir: str | Path, extra_ignore: list | None = None) -> dict:
    """Scan the project directory and build a searchable index.

    Args:
        project_dir: Root directory to scan.
        extra_ignore: Additional directory names to skip (from .widdx/config.json).
    """
    root = Path(project_dir).resolve()
    files = []
    symbols: list[dict] = []

    ignore_dirs = set(IGNORE_DIRS)
    if extra_ignore:
        ignore_dirs.update(extra_ignore)

    for p in sorted(root.rglob("*")):
        # Skip ignored dirs
        rel = p.relative_to(root)
        parts = rel.parts
        if any(part in ignore_dirs for part in parts):
            continue
        if not p.is_file():
            continue
        if p.suffix in IGNORE_EXTS:
            continue

        files.append({
            "path": str(rel.as_posix()),
            "size": p.stat().st_size,
            "ext": p.suffix,
        })

        # Extract symbols from text files
        if p.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                symbols.extend(_extract_symbols(text, str(rel.as_posix()), p.suffix))
            except Exception as e:
                logger.debug("Symbol extraction failed for %s: %s", p.name, e)

    return {
        "file_count": len(files),
        "files": files,
        "symbols": symbols,
        "symbol_count": len(symbols),
    }


def _extract_symbols(text: str, file_path: str, ext: str) -> list[dict]:
    """Extract function/class definitions from source code."""
    symbols = []
    _KEYWORD_BLACKLIST = frozenset({
        "if", "else", "for", "while", "return", "import", "from",
        "switch", "case", "catch", "finally", "with", "yield",
        "print", "console", "this", "super", "self", "it",
        "describe", "it", "test", "expect", "assert",
        "export", "default", "new", "delete", "typeof",
        "try", "throw", "await",
    })

    # Classes
    for m in re.finditer(r'^\s*(?:public\s+|private\s+|protected\s+|static\s+|abstract\s+)*(?:class|interface|struct|trait|type|enum)\s+(\w+)', text, re.MULTILINE):
        name = m.group(1)
        if name not in _KEYWORD_BLACKLIST:
            symbols.append({
                "kind": "class",
                "name": name,
                "file": file_path,
            })

    # Functions/methods — only explicit definition keywords
    patterns = [
        r'^\s*(?:async\s+)?(?:public\s+|private\s+|protected\s+|static\s+)?(?:def|function|fun|fn)\s+(\w+)',
        r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[=:]\s*(?:async\s*)?\(.*\)\s*(?:=>|->)',
        r'^\s*(\w+)\s*\([^)]*\)\s*\{',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.MULTILINE):
            name = m.group(1)
            if name and name not in _KEYWORD_BLACKLIST:
                symbols.append({
                    "kind": "function",
                    "name": name,
                    "file": file_path,
                })

    return symbols


def save_index(project_dir: str | Path, extra_ignore: list | None = None):
    """Scan and save project index to .widdx/index.json."""
    index = build_index(project_dir, extra_ignore=extra_ignore)
    path = _index_path(project_dir)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(project_dir: str | Path | None = None) -> dict | None:
    """Load project index. Returns None if no index exists."""
    if project_dir is None:
        project_dir = Path().resolve()
    path = _index_path(project_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load index from %s: %s", path, e)
        return None


# ── context builder for AI ───────────────────────────────────────────────

def build_project_context(project_dir: str | Path | None = None) -> str | None:
    """Build a rich context string from session + index for the AI.

    Returns None if no project state exists (fresh directory).
    """
    if project_dir is None:
        project_dir = Path().resolve()

    parts: list[str] = []

    # Load index
    index = load_index(project_dir)
    if index:
        parts.append("=== PROJECT INDEX ===")
        parts.append(f"Files: {index['file_count']}")
        if index.get("symbols"):
            # Group by category
            classes = [s for s in index["symbols"] if s["kind"] == "class"]
            funcs = [s for s in index["symbols"] if s["kind"] == "function"]
            if classes:
                parts.append(f"Classes/Interfaces ({len(classes)}):")
                for s in classes[:30]:
                    parts.append(f"  - {s['name']}  ({s['file']})")
            if funcs:
                parts.append(f"Functions/Methods ({len(funcs)}):")
                for s in funcs[:40]:
                    parts.append(f"  - {s['name']}  ({s['file']})")
        # File tree (recent first, top 30)
        files = index.get("files", [])
        if files:
            parts.append(f"\nFiles ({len(files)} total):")
            for f in files[:30]:
                parts.append(f"  {f['path']}  ({f['size']}B)")

    # Load session summary
    session = load_session(project_dir)
    if session:
        msg_count = len(session.get("messages", []))
        st = session.get("state", {})
        parts.append(f"\n=== PREVIOUS SESSION ===")
        parts.append(f"Messages: {msg_count} | Cost: ${st.get('cost', 0):.4f} | Turns: {st.get('turns', 0)}")
        # Show last exchange
        msgs = session["messages"]
        if msgs:
            last_user = None
            for m in reversed(msgs):
                if m.get("role") == "user":
                    last_user = m["content"][:200]
                    break
            if last_user:
                parts.append(f"Last request: {last_user}")

    if not parts:
        return None

    return "\n".join(parts)


# ── conversation summarizer — sliding window ────────────────────────────

SUMMARY_THRESHOLD = 40   # messages — summarize if above this
KEEP_LAST = 10           # full messages to keep at the end
HEAD_CHARS = 500         # chars to keep from the start of each old message
TAIL_CHARS = 200         # chars to keep from the end of each old message


def _summarize_message(content: str) -> str:
    """Compress a single message: keep head + tail, preserve structure.

    'head tail' is better than truncate because code often has the
    important part at the end (result, error, summary).
    """
    if len(content) < HEAD_CHARS + TAIL_CHARS + 50:
        return content[:HEAD_CHARS + TAIL_CHARS + 50].replace("\n", " ").strip()

    head = content[:HEAD_CHARS]
    tail = content[-TAIL_CHARS:]
    # Count newlines in head portion to include structure hint
    n_lines = content[:HEAD_CHARS].count("\n")
    return f"{head}\n[... {n_lines} lines ... {len(content)} chars ...]\n{tail}"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


def summarize_conversation(messages: list, keep_last: int = 10) -> list:
    """Compress old messages with a sliding window.

    Strategy:
      - Keep the last `keep_last` user/assistant/tool messages FULL.
      - Compress older messages by keeping head + tail of each.
      - Preserve ALL system messages (skill prompts, config, instructions).
      - Return the new list only if compression actually saved messages.

    This preserves far more context than the old 150-char truncation.
    """
    if len(messages) <= SUMMARY_THRESHOLD:
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system_msgs = [m for m in messages if m.get("role") != "system"]

    tail = non_system_msgs[-keep_last:] if non_system_msgs else []
    end_idx = -keep_last if keep_last < len(non_system_msgs) else len(non_system_msgs)
    middle = non_system_msgs[:end_idx] if end_idx != 0 else []

    if not middle:
        return messages

    # Build a smart summary: keep head+tail of each old message
    summary_lines = ["Previous conversation (compressed):"]
    for m in middle:
        role = m.get("role", "?").upper()
        content = m.get("content", "")
        if not isinstance(content, str) or not content:
            continue
        compressed = _summarize_message(content)
        tok = _estimate_tokens(content)
        summary_lines.append(f"  [{role}] ({tok} tokens) {compressed}")

    summary_text = "\n".join(summary_lines)

    new_msgs = list(system_msgs)
    new_msgs.append({"role": "system", "content": summary_text, "_summary": True})
    new_msgs.extend(tail)
    return new_msgs

def _serializable_messages(messages: list) -> list:
    """Strip non-serializable fields from messages for JSON storage.

    Preserves role, content, tool_calls, and internal flags
    (_skill_prompt, _summary) so that session reload is lossless.
    """
    cleaned = []
    for m in messages:
        entry = {"role": m["role"]}
        if m.get("content"):
            entry["content"] = m["content"]
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        if m.get("_skill_prompt"):
            entry["_skill_prompt"] = True
        if m.get("_summary"):
            entry["_summary"] = True
        cleaned.append(entry)
    return cleaned

"""Project Scanner — auto-detect project structure, languages, frameworks, git state.

Provides a lightweight ProjectCard that is injected as system context before
each AI call, giving the model fresh awareness of the project state.
"""

import time, hashlib, subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ProjectCard:
    """Snapshot of current project state."""
    file_count: int = 0
    total_size: int = 0
    languages: dict = field(default_factory=dict)   # ext → count
    frameworks: list = field(default_factory=list)   # ["react", "flask"]
    git_branch: str = ""
    git_has_changes: bool = False
    recent_commits: list = field(default_factory=list)
    has_uncommitted: bool = False
    todos_found: int = 0
    last_indexed: float = 0.0
    root_name: str = ""

    # ── Cache ─────────────────────────────────────
    _cache: dict = field(default_factory=dict, repr=False, init=False)
    _last_hash: str = field(default="", repr=False, init=False)
    _last_check: float = field(default=0.0, repr=False, init=False)


# ── Constants ──────────────────────────────────────────────

_IGNORE_DIRS = {".git", "__pycache__", ".pytest_cache", ".widdx",
                "node_modules", ".venv", "venv", "env",
                ".idea", ".vscode", ".DS_Store", ".mypy_cache"}

_FRAMEWORK_MARKERS = {
    "package.json":        "node",
    "pyproject.toml":      "python",
    "requirements.txt":    "python",
    "Cargo.toml":          "rust",
    "go.mod":              "go",
    "pom.xml":             "java",
    "build.gradle":        "java",
    "build.gradle.kts":    "java",
    "CMakeLists.txt":      "cpp",
    "Makefile":            "cpp",
    "Dockerfile":          "docker",
    "docker-compose.yml":  "docker",
}

_LANG_MAP = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".c": "C", ".cpp": "C++", ".h": "C/C++", ".hpp": "C++",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".md": "Markdown", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".xml": "XML", ".r": "R", ".jl": "Julia",
    ".lua": "Lua", ".zig": "Zig", ".ex": "Elixir", ".exs": "Elixir",
    ".hs": "Haskell", ".elm": "Elm", ".clj": "Clojure", ".dart": "Dart",
}

_THROTTLE_SECONDS = 30
_MAX_FILES = 5000


class ProjectScanner:
    """Scans the project directory and builds a ProjectCard snapshot.

    Uses the existing index.json when available to avoid re-walking
    the tree.  Throttled to once per 30 seconds.
    """

    def __init__(self, project_dir: str | Path | None = None):
        self._root = Path(project_dir).resolve() if project_dir else Path.cwd().resolve()
        self._card: Optional[ProjectCard] = None

    # ── Public API ─────────────────────────────────────

    def quick_check(self) -> bool:
        """Hash-based check: has the project changed since last scan?

        Returns True if a re-scan is needed.
        """
        now = time.time()
        if self._card is not None:
            if (now - self._card._last_check) < _THROTTLE_SECONDS:
                return False
        try:
            entries = []
            count = 0
            for f in sorted(self._root.rglob("*")):
                try:
                    if f.is_file():
                        parts = f.relative_to(self._root).parts
                        if any(p in _IGNORE_DIRS or p.startswith(".") for p in parts):
                            continue
                        st = f.stat()
                        entries.append(f"{f.relative_to(self._root)}:{st.st_size}:{st.st_mtime_ns}")
                        count += 1
                        if count > _MAX_FILES:
                            break
                except (PermissionError, OSError):
                    continue
            current_hash = hashlib.md5("|".join(entries).encode()).hexdigest()
            if current_hash == self._card._last_hash if self._card else "":
                if self._card:
                    self._card._last_check = now
                return False
            if self._card:
                self._card._last_hash = current_hash
                self._card._last_check = now
        except OSError:
            pass
        return True

    def scan(self, extra_ignore: list | None = None) -> ProjectCard:
        """Full project scan.  Returns a fresh ProjectCard."""
        ignore = set(_IGNORE_DIRS)
        if extra_ignore:
            ignore.update(extra_ignore)

        card = ProjectCard(
            root_name=self._root.name,
            last_indexed=time.time(),
        )

        card._last_check = time.time()

        # ── File walk ────────────────────────────────
        files: list[dict] = []
        lang_counts: dict[str, int] = {}
        total_size = 0
        count = 0

        for f in sorted(self._root.rglob("*")):
            try:
                if not f.is_file():
                    continue
                parts = f.relative_to(self._root).parts
                if any(p in ignore or p.startswith(".") for p in parts):
                    continue
                st = f.stat()
                total_size += st.st_size
                ext = f.suffix.lower()
                lang_counts[ext] = lang_counts.get(ext, 0) + 1
                files.append({"path": str(f.relative_to(self._root)), "size": st.st_size,
                              "ext": ext, "mtime": st.st_mtime})
                count += 1
                if count > _MAX_FILES:
                    break
            except (PermissionError, OSError):
                continue

        card.file_count = count
        card.total_size = total_size

        # ── Languages ────────────────────────────────
        card.languages = {}
        for ext, cnt in sorted(lang_counts.items(), key=lambda x: -x[1])[:10]:
            name = _LANG_MAP.get(ext, ext.lstrip(".").upper())
            card.languages[name] = cnt

        # ── Frameworks ───────────────────────────────
        seen_frameworks = set()
        for fdata in files:
            fname = Path(fdata["path"]).name
            if fname in _FRAMEWORK_MARKERS:
                seen_frameworks.add(_FRAMEWORK_MARKERS[fname])
        card.frameworks = sorted(seen_frameworks)

        # ── Git ──────────────────────────────────────
        try:
            r = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self._root, capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                card.git_branch = r.stdout.strip()
        except Exception:
            pass

        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._root, capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                card.has_uncommitted = bool(r.stdout.strip())
        except Exception:
            pass

        try:
            r = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                cwd=self._root, capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                card.recent_commits = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
        except Exception:
            pass

        # ── TODOs ────────────────────────────────────
        todo_count = 0
        import re as _re
        _todo_pattern = _re.compile(r'\b(TODO|FIXME|HACK|XXX)\b', _re.IGNORECASE)
        for fdata in files:
            if fdata["ext"] in {".py", ".js", ".ts", ".jsx", ".tsx", ".java",
                                ".go", ".rs", ".rb", ".php", ".swift", ".kt"}:
                try:
                    text = (self._root / fdata["path"]).read_text(encoding="utf-8", errors="ignore")
                    todo_count += len(_todo_pattern.findall(text))
                except Exception:
                    pass
        card.todos_found = todo_count

        card._last_hash = ""  # will be set by quick_check on next call
        self._card = card
        return card

    def build_context_block(self, extra_ignore: list | None = None) -> str | None:
        """Build a [PROJECT STATE] string for injection as system message.

        Returns None if nothing meaningful to report.
        """
        if self.quick_check() or self._card is None:
            self.scan(extra_ignore)

        card = self._card
        if card is None or card.file_count == 0:
            return None

        lines = [f"[PROJECT STATE — {card.root_name}]"]

        # File summary
        size_str = f"{card.total_size / 1e6:.0f} MB" if card.total_size < 1e9 else f"{card.total_size / 1e9:.1f} GB"
        lines.append(f"  Files: {card.file_count} ({size_str})")

        # Languages
        if card.languages:
            lang_str = ", ".join(f"{name}({cnt})" for name, cnt in list(card.languages.items())[:5])
            lines.append(f"  Languages: {lang_str}")

        # Frameworks
        if card.frameworks:
            lines.append(f"  Frameworks: {', '.join(card.frameworks)}")

        # Git
        if card.git_branch:
            lines.append(f"  Git branch: {card.git_branch}")
        if card.has_uncommitted:
            lines.append(f"  Git: uncommitted changes present")
        if card.recent_commits:
            recent = "; ".join(card.recent_commits[:3])
            lines.append(f"  Recent commits: {recent}")

        # TODOs
        if card.todos_found > 0:
            lines.append(f"  TODOs: {card.todos_found} markers found")

        return "\n".join(lines)

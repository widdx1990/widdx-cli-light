"""Project Structure — DEPRECATED.

Use ``core.project.scanner.ProjectScanner`` instead.
This module is kept for backward compatibility.
"""
import warnings
warnings.warn(
    "core.project_structure is deprecated. Use core.project.scanner instead.",
    DeprecationWarning,
    stacklevel=2,
)

from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402


class FileNode:
    """Backward-compatible FileNode — wraps a file path as a tree node.

    This is a simplified replacement for the original FileNode dataclass
    that was removed. Full tree navigation is no longer supported;
    use ``core.project.scanner.ProjectScanner`` instead.
    """

    def __init__(self, name: str = "", path: str = "", is_dir: bool = False,
                 children: Optional[list] = None, size: int = 0, extension: str = ""):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.children = children or []
        self.size = size
        self.extension = extension

    def __repr__(self):
        return f"<FileNode {self.name!r}>"


# Ignore dirs matching the old ProjectStructureAnalyzer
_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".env", "dist", "build", ".DS_Store", "target", ".idea", ".vscode",
    ".next", "coverage", ".coverage", ".pytest_cache", ".hypothesis",
    ".mypy_cache",
}


class ProjectStructureAnalyzer:
    """Backward-compatible ProjectStructureAnalyzer — DEPRECATED.

    Thin wrapper around the scanner. The original recursive tree-building
    has been removed; use ``ProjectScanner`` for modern code.
    """

    MAX_DEPTH = 5
    MAX_CHILDREN = 50

    def __init__(self, directory: Optional[str] = None):
        self.directory = Path(directory) if directory else Path.cwd()
        self.structure: Optional[FileNode] = None

    def analyze(self, max_depth: int = MAX_DEPTH) -> FileNode:
        """Build a simplified project tree (DEPRECATED)."""
        self.structure = self._build_tree(self.directory, 0, max_depth)
        return self.structure

    def _build_tree(self, path: Path, depth: int, max_depth: int) -> FileNode:
        """Recursively build a lightweight FileNode tree."""
        node = FileNode(
            name=path.name or str(path),
            path=str(path),
            is_dir=path.is_dir(),
        )
        if not path.is_dir():
            try:
                node.size = path.stat().st_size
            except Exception:
                pass
            if "." in node.name:
                node.extension = node.name.split(".")[-1].lower()
            return node
        if depth >= max_depth:
            return node
        try:
            items = []
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name in _IGNORE_DIRS:
                    continue
                items.append(self._build_tree(item, depth + 1, max_depth))
                if len(items) >= self.MAX_CHILDREN:
                    break
            node.children = items
        except Exception:
            pass
        return node

    def get_structure_summary(self, max_depth: int = MAX_DEPTH) -> str:
        """Get a text summary of the project structure (DEPRECATED)."""
        root = self.structure
        if root is None:
            root = self.analyze(max_depth)
        lines = ["<project_structure>", ""]
        self._append_tree(lines, root, "", max_depth)
        lines.extend(["", "</project_structure>"])
        return "\n".join(lines)

    def _append_tree(self, lines: list, node: FileNode, prefix: str,
                     max_depth: int, depth: int = 0):
        if depth > max_depth:
            return
        icon = "📁" if node.is_dir else "📄"
        lines.append(f"{prefix}{icon} {node.name}")
        if node.is_dir and node.children:
            for i, child in enumerate(node.children):
                is_last = i == len(node.children) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._append_tree(lines, child, new_prefix, max_depth, depth + 1)

    def get_file_extensions(self) -> dict:
        """Count file extensions in the project (DEPRECATED)."""
        root = self.structure
        if root is None:
            root = self.analyze()
        extensions: dict = {}
        self._count_extensions(root, extensions)
        return extensions

    def _count_extensions(self, node: FileNode, extensions: dict):
        if not node.is_dir and node.extension:
            extensions[node.extension] = extensions.get(node.extension, 0) + 1
        for child in node.children:
            self._count_extensions(child, extensions)

    def search_files(self, pattern: str) -> list:
        """Search for files matching a pattern (DEPRECATED)."""
        root = self.structure
        if root is None:
            root = self.analyze()
        results: list = []
        self._search_files(root, pattern.lower(), results)
        return results

    def _search_files(self, node: FileNode, pattern: str, results: list):
        if pattern in node.name.lower():
            results.append(node.path)
        for child in node.children:
            self._search_files(child, pattern, results)


# Backward-compatible singleton
_structure_analyzer: Optional[ProjectStructureAnalyzer] = None


def get_structure_analyzer(directory: Optional[str] = None) -> ProjectStructureAnalyzer:
    """Get or create structure analyzer (DEPRECATED)."""
    global _structure_analyzer
    if _structure_analyzer is None or (
        directory and _structure_analyzer.directory != Path(directory)
    ):
        _structure_analyzer = ProjectStructureAnalyzer(directory)
    return _structure_analyzer


__all__ = ["ProjectStructureAnalyzer", "FileNode", "get_structure_analyzer"]

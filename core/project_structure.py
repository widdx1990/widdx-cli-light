
"""
Project Structure Analyzer - Analyzes project file structure
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FileNode:
    """Represents a file or directory in the project"""
    name: str
    path: str
    is_dir: bool
    children: List["FileNode"] = field(default_factory=list)
    size: int = 0
    extension: str = ""


class ProjectStructureAnalyzer:
    """Analyzes project structure"""
    
    # Directories to ignore
    IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".DS_Store",
        "target",
        ".idea",
        ".vscode",
        ".next",
        "coverage",
        ".coverage",
        ".pytest_cache",
        ".hypothesis",
        ".mypy_cache",
    }
    
    # Max depth to explore
    MAX_DEPTH = 5
    
    # Max children to display per directory
    MAX_CHILDREN = 50
    
    def __init__(self, directory: Optional[str] = None):
        self.directory = Path(directory or os.getcwd())
        self.structure: Optional[FileNode] = None
    
    def analyze(self, max_depth: int = MAX_DEPTH) -> FileNode:
        """Analyze project structure"""
        self.structure = self._build_tree(self.directory, 0, max_depth)
        return self.structure
    
    def _build_tree(self, current_path: Path, depth: int, max_depth: int) -> FileNode:
        """Recursively build file tree"""
        name = current_path.name or str(current_path)
        is_dir = current_path.is_dir()
        
        node = FileNode(
            name=name,
            path=str(current_path),
            is_dir=is_dir
        )
        
        if not is_dir:
            try:
                node.size = current_path.stat().st_size
            except Exception:
                pass
            
            if "." in name:
                node.extension = name.split(".")[-1].lower()
            
            return node
        
        if depth >= max_depth:
            return node
        
        try:
            children = []
            for item in current_path.iterdir():
                if item.name in self.IGNORE_DIRS:
                    continue
                
                child_node = self._build_tree(item, depth + 1, max_depth)
                children.append(child_node)
            
            # Sort directories first, then files
            children.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            
            # Limit number of children
            if len(children) > self.MAX_CHILDREN:
                children = children[:self.MAX_CHILDREN]
            
            node.children = children
        except Exception:
            pass
        
        return node
    
    def get_structure_summary(self, max_depth: int = MAX_DEPTH) -> str:
        """Get a text summary of the project structure"""
        if self.structure is None:
            self.analyze(max_depth)
        
        lines = ["<project_structure>", ""]
        self._append_tree(lines, self.structure, "", max_depth)
        lines.append("")
        lines.append("</project_structure>")
        
        return "\n".join(lines)
    
    def _append_tree(self, lines: List[str], node: FileNode, prefix: str, max_depth: int, depth: int = 0):
        """Recursively append tree to lines"""
        if depth > max_depth:
            return
        
        # Add current node
        icon = "📁" if node.is_dir else "📄"
        lines.append(f"{prefix}{icon} {node.name}")
        
        # Add children
        if node.is_dir and node.children:
            for i, child in enumerate(node.children):
                is_last = i == len(node.children) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._append_tree(lines, child, new_prefix, max_depth, depth + 1)
    
    def get_file_extensions(self) -> Dict[str, int]:
        """Get count of file extensions"""
        if self.structure is None:
            self.analyze()
        
        extensions: Dict[str, int] = {}
        self._count_extensions(self.structure, extensions)
        return extensions
    
    def _count_extensions(self, node: FileNode, extensions: Dict[str, int]):
        """Recursively count file extensions"""
        if not node.is_dir and node.extension:
            extensions[node.extension] = extensions.get(node.extension, 0) + 1
        
        for child in node.children:
            self._count_extensions(child, extensions)
    
    def search_files(self, pattern: str) -> List[str]:
        """Search for files matching pattern"""
        if self.structure is None:
            self.analyze()
        
        results: List[str] = []
        self._search_files(self.structure, pattern.lower(), results)
        return results
    
    def _search_files(self, node: FileNode, pattern: str, results: List[str]):
        """Recursively search for files"""
        if pattern in node.name.lower():
            results.append(node.path)
        
        for child in node.children:
            self._search_files(child, pattern, results)


# Singleton instance
_structure_analyzer: Optional[ProjectStructureAnalyzer] = None


def get_structure_analyzer(directory: Optional[str] = None) -> ProjectStructureAnalyzer:
    """Get or create structure analyzer"""
    global _structure_analyzer
    if _structure_analyzer is None or \
       (directory and _structure_analyzer.directory != Path(directory)):
        _structure_analyzer = ProjectStructureAnalyzer(directory)
    return _structure_analyzer


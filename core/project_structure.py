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

from core.project.scanner import ProjectScanner as ProjectStructureAnalyzer, ProjectCard as FileNode

__all__ = ["ProjectStructureAnalyzer", "FileNode"]

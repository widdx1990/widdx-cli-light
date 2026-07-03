"""Tool registration — defines and registers all built-in tools.

Separated from execution logic. This module only calls register().
Importing this module populates the global registry.
"""

from pathlib import Path
import platform

from .registry import register, TOOL_DEFINITIONS
from .handlers.file_ops import (
    _read, _write, _edit, _glob, _grep, _list_files,
)
from .handlers.bash import _bash, _handle_sandbox_exec
from .handlers.web import _web_fetch
from .handlers.validate import _validate, _project_validate
from .handlers.edit_files import _handle_edit_files
from .handlers.spawn import _handle_spawn_agent
from .handlers.linter import _handle_run_linter

# ── Register all built-in tools ──

register(
    "read",
    "Read a file with line numbers. Supports offset/limit for partial reads.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or relative path"},
            "offset": {"type": "integer", "description": "Starting line (1-based, negative = from end, 0 = beginning)"},
            "limit": {"type": "integer", "description": "Max lines (0 = all)"},
        },
        "required": ["file_path"],
    },
    _read,
)

register(
    "write",
    "Write content to a file (creates parent directories).",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to write to"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["file_path", "content"],
    },
    _write,
)

register(
    "edit",
    "Replace text in a file. Shows diff preview. Supports replace_all. Use preview=true to see changes without applying them.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string", "description": "Text to find (must be unique unless replace_all)"},
            "new_string": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "description": "Replace ALL occurrences (default: first only)"},
            "preview": {"type": "boolean", "description": "Show diff without making changes"},
        },
        "required": ["file_path", "old_string", "new_string"],
    },
    _edit,
)

register(
    "glob",
    "Find files by glob pattern (e.g. **/*.py).",
    {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "Root directory (default: current)"},
        },
        "required": ["pattern"],
    },
    _glob,
)

register(
    "grep",
    "Search file contents by regex pattern.",
    {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Root directory"},
            "include": {"type": "string", "description": "Glob filter (e.g. *.py)"},
        },
        "required": ["pattern"],
    },
    _grep,
)

register(
    "bash",
    "Execute a shell command (PowerShell on Windows, bash on Linux/Mac).",
    {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to run"},
            "description": {"type": "string", "description": "Short description"},
        },
        "required": ["command"],
    },
    _bash,
)

register(
    "web_fetch",
    "Fetch and extract text content from a URL.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "format": {
                "type": "string",
                "enum": ["markdown", "text"],
                "description": "Output format (default: markdown)",
            },
        },
        "required": ["url"],
    },
    _web_fetch,
)

register(
    "list_files",
    "List files and directories in a directory.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current)"},
        },
    },
    _list_files,
)

register(
    "validate",
    "Validate syntax of a code file. Supports PHP, Python, JavaScript, JSON, HTML, and more.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file to validate"},
        },
        "required": ["file_path"],
    },
    _validate,
)

register(
    "project_validate",
    "Run project-level build/test validation. Detects Python, Node.js, Rust, Go, Java and runs appropriate test commands.",
    {
        "type": "object",
        "properties": {
            "project_dir": {"type": "string", "description": "Path to project root directory"},
        },
        "required": ["project_dir"],
    },
    _project_validate,
)

# ── Project Tracker tool ──
from core.project_tracker import TOOL_DEFINITION as _PT_TOOL, handle_update_project_doc

register(
    _PT_TOOL["name"],
    _PT_TOOL["description"],
    _PT_TOOL["parameters"],
    handle_update_project_doc,
)

register(
    "run_linter",
    "Run a code linter on the given file.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the file to lint"},
            "language": {"type": "string", "description": "Language override (auto-detect if 'auto')", "default": "auto"},
        },
        "required": ["file_path"],
    },
    _handle_run_linter,
)

register(
    "sandbox_exec",
    "Execute a shell command in a resource-limited sandbox.",
    {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)", "default": 60},
            "cwd": {"type": "string", "description": "Working directory for the command", "default": ""},
        },
        "required": ["command"],
    },
    _handle_sandbox_exec,
)

register(
    "edit_files",
    "Apply multiple surgical file edits in a single atomic operation.",
    {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to edit"},
                        "old_string": {"type": "string", "description": "Text to replace"},
                        "new_string": {"type": "string", "description": "Replacement text"},
                    },
                    "required": ["path", "old_string", "new_string"],
                },
                "description": "List of file edits to apply atomically",
            },
        },
        "required": ["files"],
    },
    _handle_edit_files,
)

register(
    "spawn_agent",
    "Spawn a specialized sub-agent for a subtask.",
    {"type": "object", "properties": {
        "task": {"type": "string", "description": "The subtask for the sub-agent to complete"},
        "role": {"type": "string", "description": "Role: researcher, coder, tester, reviewer, debugger, writer"},
    }, "required": ["task", "role"]},
    _handle_spawn_agent,
)

# ── Browser tools (optional, via Playwright) ──
try:
    from core.tools.browser import (
        _browser_navigate, _browser_screenshot, _browser_click,
        _browser_snapshot, _browser_type, _browser_press,
    )
    _BROWSER_OK = True
except Exception as e:
    import logging
    logging.getLogger("widdx.tools").warning("Browser tools unavailable: %s", e)
    _BROWSER_OK = False

if _BROWSER_OK:
    register("browser_navigate", "Open a URL in the browser.", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, _browser_navigate)
    register("browser_screenshot", "Take a screenshot of the current page.", {"type": "object", "properties": {"url": {"type": "string"}, "selector": {"type": "string"}}}, _browser_screenshot)
    register("browser_click", "Click an element by CSS selector.", {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}, _browser_click)
    register("browser_snapshot", "Get accessibility snapshot.", {"type": "object", "properties": {}}, _browser_snapshot)
    register("browser_type", "Type text into an input field.", {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]}, _browser_type)
    register("browser_press", "Press a keyboard key.", {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}, _browser_press)

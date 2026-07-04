"""Tool dispatch — execute() and execute_with_skills()."""

import logging
from typing import Any

from .registry import get_tool_map

logger = logging.getLogger("widdx.tools.dispatch")


def execute(name: str, args: dict[str, Any]) -> str:
    """Execute a registered tool by name."""
    handler = get_tool_map().get(name)
    if not handler:
        return f"Unknown tool: {name}"
    return handler(**args)


def execute_with_skills(name: str, args: dict) -> str:
    """Execute a tool, routing through skill_manager if a skill is active."""
    from core.skills import skill_manager

    if name == "use_skill":
        skill_name = args.get("skill_name", "")
        if skill_name:
            ok = skill_manager.activate(skill_name)
            return f"Skill '{skill_name}' activated." if ok else f"Unknown skill '{skill_name}'"
        skill_manager.deactivate()
        return "Skill deactivated."

    from core.permissions import get_permission_manager
    from rich.console import Console as _RichConsole
    _console = _RichConsole(highlight=False)
    pm = get_permission_manager()
    if not pm.check(name, console=_console):
        return f"⛔ Permission denied: {name}"

    if skill_manager.active and name in skill_manager.active.tools:
        return skill_manager.execute_tool(name, args)

    if name in ("create_agent", "run_parallel"):
        from core.workflow import WorkflowEngine
        try:
            from core.config.settings import load as load_config
            cfg = load_config()
            from core.providers.providers import create_provider
            provider = create_provider(cfg)
            wf = WorkflowEngine(provider, [], cfg, {})
            return wf.execute_workflow_tool(name, args)
        except Exception as e:
            return f"Workflow execution error: {e}"

    if name.startswith("mcp__"):
        from core.mcp.client import get_mcp_manager
        mcp = get_mcp_manager()
        if name in mcp.get_tools():
            return mcp.execute(name, args)
        return f"MCP tool not available: {name}"

    return execute(name, args)

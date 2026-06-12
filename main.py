"""WIDDX — Terminal AI Chat Tool (entry point)."""

import sys, json, hashlib, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import config, tools
from core.uil import UnifiedIntelligenceLayer, ExecutionMode
from core.providers.providers import create_provider, fetch_free_models
from core.proxy import proxy_manager
from core.skills import skill_manager
from core.commands import handle_model, handle_provider, handle_sandbox, handle_mcp, handle_load, handle_undo, handle_doctor, handle_export, handle_version
from core.config.keychain import prompt_key, has_key
from core.mcp.client import get_mcp_manager
from core.project import state as project_state
from core.project import git as git_utils
from core.ui import (
    console, print_header, print_user_msg, print_divider,
    print_system_msg, print_reasoning,
    show_thinking, handle_help, handle_tools_list,
    handle_skills_list, handle_history, handle_proxy,
    handle_save, get_input, use_enhanced_ui, is_enhanced,
)
from rich.rule import Rule
from rich.align import Align
from rich.text import Text

SYSTEM_PROMPT = """You are an intelligent assistant that helps users with software engineering tasks on Windows/PowerShell. Use the instructions below and the tools available to you to assist the user.

# Tone and style
You should be concise, direct, and to the point. When you run a non-trivial command, you should explain what the command does and why you are running it.

# Doing tasks
Use the tools available to you to complete tasks. You can read files, write files, search for patterns, run commands, and fetch web content.

# Tool usage
- When doing file search, prefer to use the glob/grep tools
- You can call multiple tools in a single response when there are no dependencies
- Use specialized tools instead of bash commands when possible
- When running bash commands, use PowerShell syntax

# Code quality — ALWAYS validate after writing
After creating or editing a code file, ALWAYS run the `validate` tool on it.
This checks syntax for PHP, Python, JavaScript, JSON, and HTML.
Fix any errors found, then re-validate until clean.

# Skills
You can activate specialized skills using the `use_skill` tool. Available skills: {skills_list}
When a task matches a skill's purpose, call `use_skill` to activate it. After activation, follow that skill's instructions.
"""


_last_index_hash: str | None = None
_last_index_check: float = 0.0
_INDEX_THROTTLE_SECONDS = 30  # minimum seconds between full scans

IGNORE_DIRS = {".git", "__pycache__", ".pytest_cache", ".widdx",
               "node_modules", ".venv", "venv", "env",
               ".idea", ".vscode", ".DS_Store"}


def _project_changed(project_dir: Path, extra_ignore: list) -> bool:
    """Check if project files have changed since last index build.

    Throttled to once every {_INDEX_THROTTLE_SECONDS}s to avoid
    grinding on large projects on every turn.
    """
    global _last_index_hash, _last_index_check
    now = time.time()
    if now - _last_index_check < _INDEX_THROTTLE_SECONDS:
        return False
    _last_index_check = now

    root = project_dir.resolve()
    ignore = set(IGNORE_DIRS)
    ignore.update(extra_ignore)
    entries = []
    try:
        for f in sorted(root.rglob("*")):
            if f.is_file():
                rel = f.relative_to(root)
                parts = rel.parts
                if any(part in ignore or part.startswith(".") for part in parts):
                    continue
                st = f.stat()
                entries.append(f"{rel}:{st.st_size}:{st.st_mtime_ns}")
    except OSError:
        pass
    current_hash = hashlib.md5("|".join(entries).encode()).hexdigest()
    if current_hash == _last_index_hash:
        return False
    _last_index_hash = current_hash
    return True



def run():
    cfg = config.load()
    provider = create_provider(cfg)
    tools.configure(cfg.get("sandbox_path"))
    state = {"model": f"{provider.name}/{provider.model}", "cost": 0.0, "turns": 0}

    system_prompt = cfg.get("system_prompt") or SYSTEM_PROMPT
    all_sk = skill_manager.list_all()
    skill_names = ", ".join(s.name for s in all_sk) if all_sk else "none"
    system_prompt = system_prompt.replace("{skills_list}", skill_names)
    messages = [{"role": "system", "content": system_prompt}]

    if provider.name in ("opencode-zen", "opencode"):
        proxy_manager.force_refresh()

    # ── Prompt for API key if missing ────────────────────────────────
    if provider.name in ("deepseek", "openai") and not has_key(provider.name):
        if not provider.api_key or provider.api_key == "public":
            print_system_msg(f"No API key found for {provider.name}. "
                             f"Set {provider.name.upper()}_API_KEY env var or enter one now.")
            prompt_key(provider.name)

    # ── Register MCP servers (lazy — no subprocess spawn yet) ─────────
    mcp_mgr = get_mcp_manager()
    mcp_mgr.load_from_config(cfg)
    if mcp_mgr.server_count > 0:
        print_system_msg(f"MCP: {mcp_mgr.server_count} server(s) registered (lazy — connect on demand)")

    print_header(state)

    # ── Auto-recover session from .widdx/session.json ──────────────────
    session_data = project_state.load_session()
    if session_data:
        saved_msgs = session_data.get("messages", [])
        saved_state = session_data.get("state", {})
        if saved_msgs:
            # Restore conversation messages (keep the system prompt)
            count = len(saved_msgs)
            state["cost"] = saved_state.get("cost", 0.0)
            state["turns"] = saved_state.get("turns", 0)
            if saved_state.get("model"):
                state["model"] = saved_state["model"]
            messages.extend(saved_msgs)
            print_system_msg(f"🔄 Session restored: {count} messages, ${state['cost']:.4f}, {state['turns']} turns")
        else:
            print_system_msg("Welcome back! Type your task or /help for commands.")

    # ── Load project config + context ───────────────────────────────────
    proj_config = project_state.load_project_config()
    project_instructions = proj_config.get("project_instructions", "")
    extra_ignore = proj_config.get("exclude_from_index", [])

    project_ctx = project_state.build_project_context()
    if project_ctx and not session_data:
        messages.append({
            "role": "system",
            "content": f"[PROJECT CONTEXT — loaded from .widdx/]\n{project_ctx}",
        })
        print_system_msg("Project context loaded from .widdx/")

    if project_instructions:
        messages.append({
            "role": "system",
            "content": f"[PROJECT INSTRUCTIONS]\n{project_instructions}",
        })

    if not project_ctx and not session_data:
        print_system_msg("Welcome! Type your task or /help for commands. (Ctrl+C to exit)")

    # ── Initialize persistent memory ─────────────────────────────────────
    memory_store = project_state.load_project_config().get("memory_store", True)
    if memory_store:
        from core.memory import MemoryStore
        mem = MemoryStore()
        mem_count = mem.total()
        if mem_count > 0:
            mem_list = mem.list_all()
            mem_text = "\n".join(
                f"  - {m['name']}: {m['description'][:100]}"
                for m in mem_list
            )
            messages.append({
                "role": "system",
                "content": f"[PERSISTENT MEMORY — {mem_count} fact(s)]\n{mem_text}",
            })
            print_system_msg(f"Memory: {mem_count} fact(s) loaded from .widdx/memory/")

    # ── Initialize Workflow Engine ───────────────────────────────────────
    from core.workflow import WorkflowEngine
    workflow = WorkflowEngine(provider, list(tools.TOOL_DEFINITIONS), cfg, state)
    tools.register_dynamic(
        workflow.get_tool_definitions(),
        {"create_agent": workflow.execute_workflow_tool,
         "run_parallel": workflow.execute_workflow_tool},
    )

    # ── Initialize UIL Central Brain (with LLM classifier fallback) ───────
    uil = UnifiedIntelligenceLayer(provider=provider)

    while True:
        try:
            user_input = get_input(state)
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input:
            continue
        print_divider()
        print_user_msg(user_input)

        # ── manual skill activation: !name or !off ────────────────────
        if user_input.startswith("!"):
            skill_name = user_input[1:].strip().lower()
            if skill_name == "off":
                if skill_manager.active:
                    old = skill_manager.active.name
                    skill_manager.deactivate()
                    print_system_msg(f"Skill '{old}' deactivated")
                else:
                    print_system_msg("No skill is active")
            elif skill_name:
                ok = skill_manager.toggle(skill_name)
                if ok:
                    active = skill_manager.active
                    if active:
                        icon = active.icon + " " if active.icon else ""
                        print_system_msg(f"{icon}Skill '{active.name}' activated — {active.description}")
                        skill_msg = {"role": "system", "content": active.prompt}
                        messages = [m for m in messages if not m.get("_skill_prompt")]
                        skill_msg["_skill_prompt"] = True
                        messages.append(skill_msg)
                    else:
                        messages = [m for m in messages if not m.get("_skill_prompt")]
                        print_system_msg("Skill deactivated")
                else:
                    print_system_msg(f"Unknown skill: '{skill_name}'. Use /skills to list.")
            continue

        # ── slash commands ────────────────────────────────────────────
        parts = user_input.split(None, 1)
        cmd = parts[0].lower()
        if cmd in ("/exit", "/quit"):
            break
        elif cmd == "/help":
            handle_help(); continue
        elif cmd == "/clear":
            print_header(state); continue
        elif cmd == "/tools":
            handle_tools_list(); continue
        elif cmd == "/skills":
            handle_skills_list(); continue
        elif cmd == "/history":
            handle_history(messages); continue
        elif cmd == "/proxy":
            handle_proxy(); continue
        elif cmd == "/save":
            handle_save(messages); continue
        elif cmd == "/model":
            provider, state = handle_model(provider, state); continue
        elif cmd == "/provider":
            provider, state = handle_provider(provider, state, cfg); continue
        elif cmd == "/sandbox":
            handle_sandbox(tools); continue
        elif cmd == "/manifest":
            from core.project.manifest import generate_manifest
            generate_manifest()
            print_system_msg("MANIFEST.json regenerated")
            continue
        elif cmd == "/reasoning":
            last = state.get("_last_reasoning")
            if last:
                from core.ui.ui import print_reasoning
                print_reasoning(last)
            else:
                print_system_msg("No reasoning from last turn")
            continue
        elif cmd == "/apikey":
            from core.config.keychain import prompt_key, forget_key, has_key
            action = parts[1].strip() if len(parts) > 1 else ""
            if action == "forget":
                forget_key(provider.name)
                print_system_msg(f"API key for {provider.name} removed from session")
            elif action == "show":
                if has_key(provider.name):
                    print_system_msg(f"\u2705 API key is set for {provider.name}")
                else:
                    print_system_msg(f"\u274c No API key set for {provider.name}")
            else:
                prompt_key(provider.name)
                print_system_msg(f"API key for {provider.name} stored securely in session")
            continue
        elif cmd == "/mcp":
            sub = parts[1].strip() if len(parts) > 1 else ""
            if sub == "discover":
                from core.mcp.client import discover_mcp_servers, MCPClientManager
                from rich.table import Table
                discovered = discover_mcp_servers(force_refresh=True)
                table = Table(title=f"Discovered {len(discovered)} MCP servers",
                              border_style="dim", header_style="bold #f5a623")
                table.add_column("Name", style="bold #00c896")
                table.add_column("Command", style="white")
                table.add_column("Status", style="dim")
                for s in discovered:
                    name = s["name"]
                    exists = "✅" if mcp_mgr.get_server(name) else "⬜"
                    table.add_row(name, f"{s['command']} {' '.join(s.get('args', []))[:40]}", exists)
                console.print(table)
                print_system_msg("Use /mcp add <name> <command> [args] to add a server")
            elif sub.startswith("add "):
                from core.mcp.client import MCPServerConnection
                rest = sub[4:].strip()
                # Parse: name command [args...]
                parts2 = rest.split(None, 2)
                if len(parts2) >= 2:
                    srv_name, srv_cmd = parts2[0], parts2[1]
                    srv_args = parts2[2].split() if len(parts2) > 2 else []
                    ok = mcp_mgr.add_server(srv_name, srv_cmd, srv_args)
                    if ok:
                        print_system_msg(f"MCP server '{srv_name}' added ({len(mcp_mgr.get_server(srv_name).get_tool_definitions())} tools)")
                    else:
                        err = mcp_mgr.get_server(srv_name).error if mcp_mgr.get_server(srv_name) else "unknown"
                        print_system_msg(f"Failed to add '{srv_name}': {err}")
                else:
                    print_system_msg("Usage: /mcp add <name> <command> [args...]")
            elif sub.startswith("remove "):
                srv_name = sub[7:].strip()
                mcp_mgr.remove_server(srv_name)
                print_system_msg(f"MCP server '{srv_name}' removed")
            else:
                handle_mcp()
            continue
        elif cmd == "/load":
            load_arg = parts[1] if len(parts) > 1 else ""
            provider, state, messages = handle_load(provider, state, messages, load_arg)
            continue
        elif cmd == "/undo":
            handle_undo()
            continue
        elif cmd == "/doctor":
            handle_doctor()
            continue
        elif cmd == "/export":
            handle_export(messages)
            continue
        elif cmd == "/version":
            handle_version()
            continue
        elif cmd == "/theme":
            use_enhanced_ui(not is_enhanced())
            print_system_msg(f"Switched to {'enhanced' if is_enhanced() else 'standard'} UI")
            print_header(state)
            continue
        elif cmd == "/remember":
            from core.memory import MemoryStore
            fact = parts[1] if len(parts) > 1 else ""
            if fact:
                mem = MemoryStore()
                mem.save(f"note-{len(fact[:20])}", fact, {"type": "feedback"})
                print_system_msg(f"Remembered: {fact[:80]}")
            else:
                print_system_msg("Usage: /remember <fact to remember>")
            continue
        elif cmd == "/memories":
            from core.memory import MemoryStore
            from rich.table import Table
            mem = MemoryStore()
            all_m = mem.list_all()
            query = parts[1] if len(parts) > 1 else ""
            if query:
                all_m = mem.search(query)
            if not all_m:
                print_system_msg("No memories found. Use /remember <fact> to save one.")
                continue
            table = Table(title=f"Memories ({'search: ' + query if query else str(len(all_m)) + ' total'})",
                          border_style="dim", header_style="bold #f5a623")
            table.add_column("Name", style="bold #00c896")
            table.add_column("Description", style="white")
            table.add_column("Type", style="dim")
            for m in all_m:
                table.add_row(m["name"], m.get("description", "")[:80], m.get("type", ""))
            console.print(table)
            continue
        # ── normal message → UIL Central Brain handles everything ──
        messages.append({"role": "user", "content": user_input})
        show_thinking()

        tool_defs = list(tools.TOOL_DEFINITIONS)
        use_skill_def = skill_manager.get_use_skill_tool_def()
        if use_skill_def:
            tool_defs.append(use_skill_def)
        skill_tool_defs = skill_manager.get_active_tools()
        if skill_tool_defs:
            tool_defs.extend(skill_tool_defs)

        # Add MCP tool definitions
        mcp_tools = mcp_mgr.get_all_tool_definitions()
        if mcp_tools:
            tool_defs.extend(mcp_tools)

        # Add workflow tools (create_agent, run_parallel)
        from core import tools as _tools
        workflow_tools = [td for td in _tools.TOOL_DEFINITIONS
                          if td["name"] in ("create_agent", "run_parallel")]
        if workflow_tools:
            tool_defs.extend(workflow_tools)

        # ── Helper: extract plan from decision (ctx) ─────────────────
        def _get_plan(decision):
            """Get the Plan object from decision/ctx."""
            plan = getattr(getattr(decision, "plan", None), "decomposed", None)
            return plan

        # ── Helper: read tools_used from state ──────────────────────
        def _get_tools():
            return list(state.get("tools_used", []))

        # ── UIL: analyze → route → plan → execute ──────────────────
        def _simple_chat_exec(decision, inp, msgs):
            from core.chat import run_stream_turn
            plan = _get_plan(decision)
            n_steps = len(plan.steps) if plan and plan.steps else 0
            if plan and not plan.is_minimal and plan.steps:
                steps_text = "\n".join(
                    f"  {s.id}: {s.description}"
                    + (f" (deps: {', '.join(s.dependencies)})" if s.dependencies else "")
                    for s in plan.steps
                )
                msgs.append({"role": "system",
                             "content": f"[PLAN — {n_steps} steps]\n{steps_text}",
                             "_plan": True})
            # Reset tool tracking for this turn
            state["tools_used"] = []
            msgs, _state = run_stream_turn(provider, msgs, state,
                                           decision.tool_defs, cfg)
            # Clean up plan system message
            msgs[:] = [m for m in msgs if not m.get("_plan")]
            tools_used = list(state.get("tools_used", []))
            for m in reversed(msgs):
                if m["role"] == "assistant":
                    return (m["content"], n_steps, 0, tools_used)
            return ("", n_steps, 0, tools_used)

        def _autonomous_exec(decision, inp, msgs):
            from core.agents.agent import AutonomousAgent
            plan = _get_plan(decision)
            n_steps = len(plan.steps) if plan and plan.steps else 0
            planned_inp = inp
            if plan and not plan.is_minimal and plan.steps:
                steps_text = "\n".join(
                    f"  {s.id}: {s.description}"
                    + (f" (deps: {', '.join(s.dependencies)})" if s.dependencies else "")
                    for s in plan.steps
                )
                planned_inp = (
                    f"[SYSTEM: Planner — {n_steps} steps]\n"
                    f"{steps_text}\n\n---\n{inp}"
                )
            state["tools_used"] = []
            agent = AutonomousAgent(provider, decision.tool_defs, cfg, state)
            steps_log, summary = agent.run(planned_inp)
            completed = sum(1 for s in steps_log if s.status == "done")
            failed = sum(1 for s in steps_log if s.status == "failed")
            tools_used = list(state.get("tools_used", []))
            return (summary, completed, failed, tools_used)

        def _expert_team_exec(decision, inp, msgs):
            from core.agents.expert import ExpertTeam
            plan = _get_plan(decision)
            n_steps = len(plan.steps) if plan and plan.steps else 0
            planned_inp = inp
            if plan and not plan.is_minimal and plan.steps:
                steps_text = "\n".join(
                    f"  {s.id}: {s.description}"
                    for s in plan.steps
                )
                planned_inp = (
                    f"[SYSTEM: Planner — {n_steps} steps]\n"
                    f"{steps_text}\n\n---\n{inp}"
                )
            state["tools_used"] = []
            team = ExpertTeam(provider, decision.tool_defs, cfg, state)
            summary = team.run(planned_inp)
            tools_used = list(state.get("tools_used", []))
            return (summary, n_steps, 0, tools_used)

        def _direct_tool_exec(decision, inp, msgs):
            from core import tools as core_tools
            result = core_tools.execute("bash", {"command": inp})
            failed = 1 if "Error" in result else 0
            tools_used = ["bash"]
            return (result, 1, failed, tools_used)

        executors = {
            ExecutionMode.SIMPLE_CHAT: _simple_chat_exec,
            ExecutionMode.AUTONOMOUS: _autonomous_exec,
            ExecutionMode.EXPERT_TEAM: _expert_team_exec,
            ExecutionMode.DIRECT_TOOL: _direct_tool_exec,
        }

        uil.set_tool_defs(tool_defs)
        # Wrap UIL processing in try/except to prevent hangs from API failures
        try:
            result, _ = uil.process(user_input,
                                    messages=messages,
                                    executors=executors)
            summary = result.summary
        except KeyboardInterrupt:
            print_system_msg("Interrupted by user")
            continue
        except Exception as exc:
            print_system_msg(f"Processing error: {exc}")
            summary = f"Error: {exc}"
        messages.append({"role": "assistant", "content": summary})

        # ── Save session + index + git commit + auto-summary ──────────
        try:
            project_state.save_session(messages, state)
        except Exception as exc:
            print_system_msg(f"[dim]Session save failed: {exc}[/]")

        try:
            if _project_changed(Path().resolve(), extra_ignore):
                project_state.save_index(Path().resolve(), extra_ignore=extra_ignore)
        except Exception as exc:
            print_system_msg(f"[dim]Index save failed: {exc}[/]")

        try:
            auto_commit_enabled = project_state.load_project_config().get("auto_commit", True)
            if auto_commit_enabled:
                git_utils.auto_commit(Path().resolve(), user_input)
        except Exception as exc:
            print_system_msg(f"[dim]Auto-commit failed: {exc}[/]")

        try:
            old_len = len(messages)
            messages = project_state.summarize_conversation(messages, keep_last=10)
            if len(messages) < old_len:
                print_system_msg(f"Conversation summarized ({old_len} -> {len(messages)} messages)")
        except Exception as exc:
            print_system_msg(f"[dim]Conversation summary failed: {exc}[/]")

    console.print(Rule(style="dim"))
    cost_str = "$%.4f" % state["cost"]
    console.print(Align.center(Text(f"Session ended - cost: {cost_str} - turns: {state['turns']}", style="dim")))


if __name__ == "__main__":
    run()

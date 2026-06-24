"""Conversation loop and tool processing for WIDDX.

Display functions are organized in ``DisplayManager`` class.
Module-level aliases kept for backward compatibility.
"""

import json, uuid
from datetime import datetime
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.live import Live

from core import tools
from core.skills import skill_manager
from core.providers.providers import estimate_turn_cost


# ── Console helpers ──────────────────────────────────────
_console = Console(highlight=False)
_GREEN = "#00c896"
_ORANGE = "#f5a623"
_DIM = "#888888"


class DisplayManager:
    """Rich display helpers for chat messages.

    All display output goes through this class so callers can
    substitute their own display logic (e.g., Web UI, TUI).
    """

    def __init__(self, console: Console | None = None):
        self.console = console or _console

    def system_msg(self, text: str):
        """Display a system message in a dim panel."""
        self.console.print(Panel(
            Text(text, style=_DIM),
            title="[dim]⚙ system[/]", border_style=_DIM, padding=(0, 1),
        ))

    def ai_msg(self, text: str):
        """Display an AI message in an orange panel."""
        self.console.print(Panel(
            Text(text[:2000], style=_ORANGE),
            title=f"[bold {_ORANGE}]🤖 WIDDX[/]",
            subtitle=f"[dim]{datetime.now().strftime('%H:%M')}[/]",
            border_style=_ORANGE, padding=(0, 1),
        ))

    def tool_call(self, name: str, args_str: str):
        """Display a tool call in a compact panel."""
        self.console.print(Panel(
            Text(f"{name}({args_str})", style=_GREEN),
            title="[bold green]🔧 tool[/]", border_style=_GREEN, padding=(0, 1),
        ))

    def tool_msg(self, name: str, content: str):
        """Display a tool result (surrogates cleaned for Rich compatibility)."""
        from core.providers.base import _clean_surrogates
        safe = _clean_surrogates(str(content))[:500]
        self.console.print(Panel(
            Text(safe, style="gray50"),
            title=f"[dim]{name}[/]", border_style="gray50", padding=(0, 1),
        ))

    def reasoning(self, text: str):
        """Display reasoning/thinking text."""
        self.console.print(Panel(
            Text(text, style="#b388ff"),
            title="[#b388ff]🧠 reasoning[/]", border_style="#b388ff", padding=(0, 1),
        ))

    def agent_done(self, steps: list, summary: str):
        """Display agent completion summary."""
        if not steps:
            self.console.print(f"  [dim]Agent: {summary[:200]}[/]")
            return
        step_lines = []
        for i, s in enumerate(steps[-5:], 1):
            name = getattr(s, "tool_name", getattr(s, "name", f"step_{i}"))
            status = getattr(s, "status", "done")
            icon = "✅" if status == "done" else "❌" if status == "failed" else "⏳"
            step_lines.append(f"    {icon} {name}")
        self.console.print(Panel(
            Text(f"{summary[:200]}\n" + "\n".join(step_lines), style=_GREEN),
            title="[bold green]✅ Agent Complete[/]",
            border_style=_GREEN, padding=(0, 1),
        ))


# ── Module-level singleton ───────────────────────────────
_display = DisplayManager()


# ── Public aliases (backward compatible) ─────────────────
console = _console

def print_system_msg(text: str):
    _display.system_msg(text)

def print_ai_msg(text: str):
    _display.ai_msg(text)

def print_tool_call(name: str, args_str: str):
    _display.tool_call(name, args_str)

def print_tool_msg(name: str, content: str):
    _display.tool_msg(name, content)

def print_reasoning(text: str):
    _display.reasoning(text)


def print_agent_done(steps: list, summary: str):
    """Show the final agent summary panel with step log."""
    from rich.table import Table
    if not steps:
        _console.print(Panel(
            Text(summary, style="white"),
            border_style=_GREEN,
            title="[bold]Agent Complete[/]",
            title_align="left",
        ))
        return
    done = sum(1 for s in steps if s.status == "done")
    failed = sum(1 for s in steps if s.status == "failed")
    total = len(steps)
    lines = [f"Steps: {done}/{total} succeeded"]
    if failed:
        lines.append(f"Failed: {failed}")
    table = Table(title="Agent Execution Summary", border_style="dim")
    table.add_column("Step", style="dim")
    table.add_column("Tool", style=f"bold {_GREEN}")
    table.add_column("Status", style=_ORANGE)
    for s in steps:
        status_icon = "✅" if s.status == "done" else "❌" if s.status == "failed" else "⏳"
        table.add_row(str(s.step_num), s.tool_name, status_icon)
    _display.console.print(table)
    if summary:
        _display.console.print(Panel(summary, title="[bold]Summary[/]", border_style=_GREEN))


def print_ai_stream():
    """Return (live, update_fn, done_fn) for streaming AI response."""
    ts = datetime.now().strftime("%H:%M")
    header = Text()
    header.append(" assistant ", style=f"bold {_GREEN}")
    header.append(f" {ts}", style="dim")
    _display.console.print()
    _display.console.print(header)
    _accumulated = [""]
    live_container = [None]

    def get_panel():
        return Panel(Text(_accumulated[0][:2000] or "[thinking...]", style=_ORANGE), border_style=_ORANGE, padding=(0, 1))

    def update(chunk: str):
        _accumulated[0] += chunk
        if live_container[0] is not None:
            live_container[0].update(get_panel())

    live = Live(get_panel(), refresh_per_second=10, vertical_overflow="visible")
    live_container[0] = live
    return live, update, live.stop


# ── Tool-call ID validation ────────────────────────────────
# Some API backends (OpenCode Zen proxy, strict OpenAI-compatible
# servers) reject empty, null, or malformed tool_call_id values.
# We guarantee every tool_call_id is a valid non-empty string.

def _valid_tool_call_id(tc_id: str | None) -> str:
    """Return a guaranteed-valid tool_call_id."""
    if not tc_id or not isinstance(tc_id, str) or not tc_id.strip():
        return f"call_{uuid.uuid4().hex[:12]}"
    return tc_id


def _sanitize_tool_call_ids(messages: list[dict]) -> list[dict]:
    """Remove ``tool_call_id`` from any message whose role is NOT ``tool``,
    and ensure every ``tool``-role message has a valid non-empty ``tool_call_id``.

    Also strips ``tool_calls`` from assistant messages when they contain
    IDs that look like UUID placeholders (leftover from text-based parsing).
    """
    for m in messages:
        if m.get("role") == "tool":
            m["tool_call_id"] = _valid_tool_call_id(m.get("tool_call_id", ""))
        elif "tool_call_id" in m:
            # Non-tool messages should never carry tool_call_id
            del m["tool_call_id"]
    return messages


def _inject_skill_prompt(messages):
    """Insert the active skill's system prompt at the front of messages."""
    if not skill_manager.active:
        return
    messages[:] = [m for m in messages if not m.get("_skill_prompt")]
    msg = {"role": "system", "content": skill_manager.active.prompt,
           "_skill_prompt": True}
    messages.insert(0, msg)


def _get_model(state: dict) -> str:
    """Extract the model name from state (format: 'provider/model')."""
    full = state.get("model", "")
    return full.split("/")[-1] if "/" in full else full


def _build_tc_list(tool_calls) -> list[dict]:
    """Convert ToolCall objects to OpenAI-compatible tool_calls dict list."""
    return [
        {"id": _valid_tool_call_id(tc.id), "type": "function",
         "function": {"name": tc.name,
                      "arguments": json.dumps(tc.args, ensure_ascii=False)}}
        for tc in tool_calls
    ]


def _handle_tool_calls(tool_calls, content, messages, state):
    """Shared: append assistant msg with tool_calls, print intents, execute tools."""
    tc_list = _build_tc_list(tool_calls)
    messages.append({
        "role": "assistant", "content": content or None,
        "tool_calls": tc_list,
    })
    for tc in tool_calls:
        print_tool_call(tc.name, json.dumps(tc.args, ensure_ascii=False))
    return process_tool_calls(tool_calls, messages, state)


def process_tool_calls(tool_calls, messages, state):
    """Execute each tool call and append results to messages.

    Shares tool-dispatch logic with agents via tools.execute_with_skills().
    Tracks tools_used in state for ExecutionResult telemetry.
    """
    if "tools_used" not in state:
        state["tools_used"] = []
    model = _get_model(state)

    for tc in tool_calls:
        state["turns"] += 1

        # Track tool usage (skip use_skill — it's meta)
        if tc.name != "use_skill" and tc.name not in state["tools_used"]:
            state["tools_used"].append(tc.name)

        # ── Special: use_skill tool (AI activates skills autonomously) ──
        if tc.name == "use_skill":
            result = tools.execute_with_skills(tc.name, tc.args)
            if "activated" in result and skill_manager.active:
                _inject_skill_prompt(messages)
            elif "deactivated" in result:
                messages[:] = [m for m in messages if not m.get("_skill_prompt")]
            state["cost"] += estimate_turn_cost(model, 200, 50)
            print_system_msg(result.replace("'", ""))
            messages.append({"role": "tool", "tool_call_id": _valid_tool_call_id(tc.id),
                             "name": tc.name, "content": result})
            continue

        print_tool_msg(tc.name, json.dumps(tc.args, ensure_ascii=False))
        result = tools.execute_with_skills(tc.name, tc.args)
        messages.append({"role": "tool", "tool_call_id": _valid_tool_call_id(tc.id),
                         "name": tc.name, "content": result})
        # Tool call: ~200 input tokens for context, ~100 output tokens for result
        state["cost"] += estimate_turn_cost(model, 200, 100)
    return messages


def run_chat_turn(provider, messages, state, tool_defs, cfg):
    """Run the inner AI conversation loop (max_turns iterations).
    Returns (messages, state)."""
    max_turns = cfg.get("max_turns", 10)
    last_error = None
    for turn in range(max_turns):
        _sanitize_tool_call_ids(messages)  # ensure valid tool_call_ids before API call
        try:
            content, tool_calls = provider.chat(
                messages, tool_defs, cfg.get("temperature", 0.7)
            )
        except Exception as e:
            print_system_msg(f"Error: {e}")
            last_error = str(e)
            break
        state["cost"] += estimate_turn_cost(_get_model(state), 500, 1000)
        if content and content.startswith("[thinking]"):
            end_idx = content.find("[/thinking]")
            if end_idx > 0:
                reasoning = content[len("[thinking]"):end_idx].strip()
                content = content[end_idx + len("[/thinking]"):].strip()
                if reasoning:
                    state["_last_reasoning"] = reasoning
                    print_reasoning(reasoning)
        if tool_calls:
            messages = _handle_tool_calls(tool_calls, content, messages, state)
        else:
            if not content or not content.strip():
                content = "[done]"
            messages.append({"role": "assistant", "content": content})
            print_ai_msg(content)
            break
    else:
        print_system_msg("Max turns reached")

    # ── Self-improvement: learn from errors ─────────────────
    if last_error:
        try:
            from core.self_improve import get_improver
            improver = get_improver()
            improver.learn_from_error(last_error, state.get("model", ""))
        except Exception:
            pass

    return messages, state


def run_stream_turn(provider, messages, state, tool_defs, cfg):
    """Run one conversation turn with live streaming display.
    Falls back to run_chat_turn() if provider does not support streaming."""
    if not hasattr(provider, "stream"):
        return run_chat_turn(provider, messages, state, tool_defs, cfg)

    max_turns = cfg.get("max_turns", 10)
    for turn in range(max_turns):
        _sanitize_tool_call_ids(messages)  # ensure valid tool_call_ids before API call
        live, update, done = print_ai_stream()
        content_chunks = []
        reasoning_chunks = []
        tool_calls = None
        err_msg = None
        stream_done = False

        with live:
            for event in provider.stream(messages, tool_defs, cfg.get("temperature", 0.7)):
                if event["type"] == "content":
                    update(event["data"])
                    content_chunks.append(event["data"])
                elif event["type"] == "reasoning":
                    reasoning_chunks.append(event["data"])
                elif event["type"] == "error":
                    err_msg = event["data"]
                    break
                elif event["type"] == "done":
                    final_content, tool_calls = event["data"]
                    # Provider may have packed reasoning into content — use it
                    # when no content was streamed as separate deltas
                    if not content_chunks and final_content:
                        # Strip [thinking] tags for cleaner live display
                        clean = final_content
                        if clean.startswith("[thinking]"):
                            end = clean.find("[/thinking]")
                            if end > 0:
                                clean = clean[len("[thinking]"):end].strip()
                        update(clean)
                        content_chunks.append(final_content)
                    stream_done = True
                    break
            # Ensure Live panel has *something* so it doesn't commit as empty
            if not content_chunks and not tool_calls:
                update("[done]")
            if not err_msg and not stream_done:
                err_msg = "Stream ended unexpectedly (possible connection timeout)"

        if err_msg:
            print_system_msg(f"Error: {err_msg}")
            break

        state["cost"] += estimate_turn_cost(_get_model(state), 500, 1000)
        content = "".join(content_chunks)
        full_reasoning = "".join(reasoning_chunks)
        if full_reasoning:
            state["_last_reasoning"] = full_reasoning
            print_reasoning(full_reasoning)

        # Strip [thinking]…[/thinking] tags that some providers prepend
        if content and content.startswith("[thinking]"):
            end_idx = content.find("[/thinking]")
            if end_idx > 0:
                reasoning = content[len("[thinking]"):end_idx].strip()
                rest = content[end_idx + len("[/thinking]"):].strip()
                content = rest or reasoning or "[done]"  # keep something!

        if tool_calls:
            done()  # commit the streamed text before showing tool calls
            messages = _handle_tool_calls(tool_calls, content, messages, state)
        else:
            messages.append({"role": "assistant", "content": content})
            done()  # always commit — prevents empty panel when content is only reasoning
            break
    else:
        print_system_msg("Max turns reached")
    return messages, state


def run_agent_turn(provider, messages, state, tool_defs, cfg, user_input):
    """Run one turn using the autonomous agent (real-time tool-calling loop)."""
    from core.agents.agent import AutonomousAgent
    agent = AutonomousAgent(provider, tool_defs, cfg, state)
    steps, summary = agent.run(user_input)
    # Build a rich result with step log + AI summary
    step_log = "\n".join(
        f"  Step {s.step_num}: {s.tool_name} - {'done' if s.status == 'done' else 'failed'}"
        for s in steps
    ) if steps else "  (no tools called)"
    result = f"[Agent completed {len(steps)} steps]\n\n{step_log}\n\n{summary}"
    messages.append({"role": "assistant", "content": result})
    return messages, state

"""Real autonomous agent — AI-driven tool-calling loop with full control.

This implementation wraps tool execution, tracks steps, and enforces
automatic validation after file writes/edits and after `bash` commands
that create/modify known source files.
"""

import json, uuid, time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.panel import Panel
from rich.text import Text

from .. import tools as core_tools
from ..skills import skill_manager as _skill_manager
from ..chat import (
    console, print_system_msg, print_tool_call, print_tool_msg,
    print_reasoning, print_ai_stream, print_agent_done,
)
from ..providers.providers import estimate_turn_cost


def _vid(tc_id) -> str:
    """Ensure tool_call_id is a non-empty string."""
    if not tc_id or not isinstance(tc_id, str) or not tc_id.strip():
        return f"call_{uuid.uuid4().hex[:12]}"
    return tc_id


# ---------------------------------------------------------------------------
# Agent System Prompt
# ---------------------------------------------------------------------------

AGENT_PROMPT = """# WIDDX Cortex — Autonomous Agent

You are WIDDX Cortex, created by MUHAMMAD MUSLIH (Founder & CEO of WIDDX).
🇵🇸 Made in Palestine.

AVAILABLE TOOLS:
{tool_descriptions}

WORKFLOW:
1. Receive a task from the user
2. Think step by step about what needs to be done
3. Call ONE tool at a time, analyze the result, then decide next step
4. If a tool fails, analyze the error and try a different approach
5. If you need clarification, ask the user directly in your response
6. Validate after every write/edit — quality first
7. When complete, summarize clearly what was accomplished

RULES:
- Call one tool at a time (you can call many in sequence)
- After each tool result, analyze and decide what to do next
- On failure: explain what happened, then try a different approach
- ALWAYS run validate after writing or editing code
- NEVER say you're done until the task is actually complete
- Your final response MUST be a summary of what was accomplished"""


# ---------------------------------------------------------------------------
# Agent Step Tracking
# ---------------------------------------------------------------------------


class AgentStep:
    """A single dynamically-recorded step during agent execution."""

    def __init__(self, step_num: int, tool_name: str, args: dict, result: str):
        self.step_num = step_num
        self.tool_name = tool_name
        self.args = args
        self.result = result
        self.status = "done" if self._is_success(result) else "failed"

    def _is_success(self, result: str) -> bool:
        if not result or not result.strip():
            return False
        normalized = result.strip()
        failure_prefixes = ("❌", "⚠️", "⚠", "⛔", "Error", "Failed", "No such", "File not found")
        return not normalized.startswith(failure_prefixes)

    def to_dict(self) -> dict:
        return {
            "step": self.step_num,
            "tool": self.tool_name,
            "args": self.args,
            "result": self.result[:500],
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Autonomous Agent
# ---------------------------------------------------------------------------


class AutonomousAgent:
    """Real autonomous agent with real-time tool-calling loop.
    The AI is in full control — it decides which tools to call,
    when to retry, when to ask the user, and when to finish.
    """

    def __init__(self, provider, tool_defs: list, cfg: dict, state: dict,
                 custom_prompt: Optional[str] = None):
        self.provider = provider
        self.tool_defs = tool_defs
        self.cfg = cfg
        self.state = state
        self.custom_prompt = custom_prompt
        self.steps: list[AgentStep] = []
        self.cost = 0.0

    def run(self, user_input: str) -> tuple[list[AgentStep], str]:
        """Execute the agentic loop. Returns (steps, summary_text)."""
        messages = [
            {"role": "system", "content": self._build_prompt()},
            {"role": "user", "content": user_input},
        ]

        max_iter = self.cfg.get("agent_max_iterations", 25)
        temperature = self.cfg.get("temperature", 0.7)
        self.steps = []

        print_system_msg("Starting autonomous execution...")

        for iteration in range(max_iter):
            # Check cancel flag (set by TUI escape key)
            cancel = self.cfg.get("_cancel_flag")
            if cancel and cancel():
                print_system_msg("🛑 Agent cancelled by user")
                break

            # Call provider (streaming preferred, fallback to chat)
            try:
                if self._supports_streaming():
                    content, tool_calls = self._streaming_call(messages, temperature)
                else:
                    content, tool_calls = self.provider.chat(
                        messages, self.tool_defs, temperature
                    )
            except Exception as e:
                print_system_msg(f"Agent error: {e}")
                break

            model = self.state.get("model", "").split("/")[-1] or "unknown"
            self.state["cost"] += estimate_turn_cost(model, 500, 1000)

            # ── Process tool calls if AI decided to use tools ──
            if tool_calls:
                tc_list = [
                    {"id": _vid(tc.id), "type": "function",
                     "function": {"name": tc.name,
                                  "arguments": json.dumps(tc.args, ensure_ascii=False)}}
                    for tc in tool_calls
                ]
                messages.append({"role": "assistant", "content": content or None, "tool_calls": tc_list})

                for tc in tool_calls:
                    result = self._execute_tool(tc)
                    step = AgentStep(len(self.steps) + 1, tc.name, tc.args, result)
                    self.steps.append(step)

                    # If the tool wrote or edited a file, run validation immediately
                    if tc.name in {"write", "edit"} and not step.result.startswith(("❌", "⚠️", "⚠", "⛔", "Error", "Failed", "No such", "File not found")):
                        file_path = tc.args.get("file_path")
                        if file_path:
                            val_result = self._auto_validate_file(file_path)
                            validation_step = AgentStep(len(self.steps) + 1, "validate", {"file_path": file_path}, val_result)
                            self.steps.append(validation_step)

                    # Append tool result to messages for context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": _vid(getattr(tc, 'id', None)),
                        "name": tc.name,
                        "content": result,
                    })
                    model = self.state.get("model", "").split("/")[-1] or "unknown"
                    self.state["cost"] += estimate_turn_cost(model, 200, 100)
                    self.state["turns"] = self.state.get("turns", 0) + 1
            else:
                # AI responded without tool calls — task is complete (or AI is asking a question)
                summary = content or "Task completed."
                self._show_final_result(content)
                print_agent_done(self.steps, summary)
                return self.steps, summary

        # Hit max iterations
        summary = f"Reached maximum iterations ({max_iter})."
        print_system_msg(summary)
        print_agent_done(self.steps, summary)
        return self.steps, summary

    # ── internal helpers ──────────────────────────────────────────────

    def _supports_streaming(self) -> bool:
        return hasattr(self.provider, "stream")

    def _streaming_call(self, messages: list, temperature: float) -> tuple:
        """Call provider with streaming display. Returns (content, tool_calls)."""
        live, update, done = print_ai_stream()
        content_chunks = []
        reasoning_chunks = []
        tool_calls = None
        err_msg = None

        with live:
            for event in self.provider.stream(messages, self.tool_defs, temperature):
                if event["type"] == "content":
                    update(event["data"])
                    content_chunks.append(event["data"])
                elif event["type"] == "reasoning":
                    reasoning_chunks.append(event["data"])
                elif event["type"] == "error":
                    err_msg = event["data"]
                    break
                elif event["type"] == "done":
                    _, tool_calls = event["data"]
                    break

        if err_msg:
            print_system_msg(f"Error: {err_msg}")
            return "", []

        content = "".join(content_chunks)
        if content and tool_calls:
            done()

        full_reasoning = "".join(reasoning_chunks)
        if full_reasoning:
            self.state["_last_reasoning"] = full_reasoning
            print_reasoning(full_reasoning)
        return content, tool_calls

    def _execute_tool(self, tc) -> str:
        """Execute a single tool call and display it.

        Handles automatic validation for `bash` commands that create/modify
        repository files by snapshotting mtimes and validating changed files.
        """
        # Track tool usage
        if "tools_used" not in self.state:
            self.state["tools_used"] = []
        if tc.name != "use_skill" and tc.name not in self.state["tools_used"]:
            self.state["tools_used"].append(tc.name)

        print_tool_call(tc.name, json.dumps(tc.args, ensure_ascii=False))

        # Handle bash specially: snapshot time, run command, then validate new/modified files
        if tc.name == "bash":
            t0 = time.time()
            result = core_tools.execute_with_skills(tc.name, tc.args)
            print_tool_msg(tc.name, result[:1000])

            normalized = (result or "").strip()
            if not normalized.startswith(("\ud83d\udeab", "❌", "⛔", "Error", "Failed")):
                exts = {".py", ".js", ".ts", ".tsx", ".json", ".css", ".html", ".htm", ".go", ".dart", ".rb", ".php", ".yaml", ".yml"}
                changed = []
                try:
                    root = Path(".").resolve()
                    for f in root.rglob("*"):
                        if not f.is_file():
                            continue
                        try:
                            if f.stat().st_mtime >= t0 - 0.5 and f.suffix.lower() in exts:
                                changed.append(f)
                        except Exception:
                            continue
                except Exception:
                    changed = []

                for f in changed[:30]:
                    val_result = self._auto_validate_file(str(f))
                    self.steps.append(AgentStep(len(self.steps) + 1, "validate", {"file_path": str(f)}, val_result))

            return result

        # Default execution path
        result = core_tools.execute_with_skills(tc.name, tc.args)
        print_tool_msg(tc.name, result[:1000])
        return result

    def _auto_validate_file(self, file_path: str) -> str:
        """Automatically validate a file after a write/edit operation."""
        p = Path(file_path)
        if not p.exists():
            return f"⚠️ Validation skipped: file not found {file_path}"
        validation_args = {"file_path": str(p)}
        print_tool_call("validate", json.dumps(validation_args, ensure_ascii=False))
        result = core_tools.execute_with_skills("validate", validation_args)
        print_tool_msg("validate", result[:1000])
        return result

    def _build_prompt(self) -> str:
        """Build the agent system prompt with all available tools.
        If custom_prompt is set, use it instead of the default AGENT_PROMPT."""
        lines = []
        mcp_lines = []
        for td in self.tool_defs:
            line = f"  {td['name']}: {td.get('description', '')}"
            if td["name"].startswith("mcp__"):
                mcp_lines.append(line)
            else:
                lines.append(line)

        tool_text = "\n".join(lines) if lines else "  (none)"
        mcp_text = "\n".join(mcp_lines) if mcp_lines else "  (none)"
        skill_names = [s.name for s in _skill_manager.list_all()]
        skill_text = "\n".join(f"  {s}" for s in skill_names) if skill_names else "  (none)"

        prompt_template = self.custom_prompt or AGENT_PROMPT
        return prompt_template.format(
            tool_descriptions=(
                f"Built-in tools:\n{tool_text}\n\n"
                f"MCP tools:\n{mcp_text}\n\n"
                f"Skills:\n{skill_text}"
            )
        )

    def _show_final_result(self, content: Optional[str]):
        """Show the AI's final response panel if there's content."""
        if not content:
            return
        console.print()
        console.print(Panel(
            Text(content, style="bold #00c896"),
            border_style="#00c896",
            title="[bold #00c896]Agent Result[/]",
            title_align="left",
        ))

    def get_status(self) -> str:
        """Return a short summary of current agent progress."""
        if not self.steps:
            return "No steps executed yet."
        done = sum(1 for s in self.steps if s.status == "done")
        failed = sum(1 for s in self.steps if s.status == "failed")
        return f"{len(self.steps)} steps ({done} done, {failed} failed)"

    def __repr__(self):
        return f"AutonomousAgent({len(self.steps)} steps, cost={self.cost:.4f})"


# ---------------------------------------------------------------------------
# Helper: run agent with a custom system prompt
# ---------------------------------------------------------------------------


def run_agent_with_prompt(provider, tool_defs, cfg, state, system_prompt, user_input):
    """Run AutonomousAgent with a custom system prompt.
    Returns (steps, summary_text).
    
    This is used by ExpertTeam to give each expert a specialized prompt.
    """
    agent = AutonomousAgent(provider, tool_defs, cfg, state,
                            custom_prompt=system_prompt)
    return agent.run(user_input)

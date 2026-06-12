"""Conversation loop and tool processing for WIDDX."""

import json

from core import tools
from core.skills import skill_manager
from core.ui import (
    print_tool_msg, print_tool_call, print_system_msg, print_ai_msg, print_reasoning,
    print_ai_stream,
)


def _inject_skill_prompt(messages):
    """Insert the active skill's system prompt at the front of messages."""
    if not skill_manager.active:
        return
    messages[:] = [m for m in messages if not m.get("_skill_prompt")]
    msg = {"role": "system", "content": skill_manager.active.prompt,
           "_skill_prompt": True}
    messages.insert(0, msg)


def process_tool_calls(tool_calls, messages, state):
    """Execute each tool call and append results to messages.

    Shares tool-dispatch logic with agents via tools.execute_with_skills().
    Tracks tools_used in state for ExecutionResult telemetry.
    """
    if "tools_used" not in state:
        state["tools_used"] = []

    for tc in tool_calls:
        state["turns"] += 1

        # Track tool usage (skip use_skill — it's meta)
        if tc.name != "use_skill" and tc.name not in state["tools_used"]:
            state["tools_used"].append(tc.name)

        # ── Special: use_skill tool (AI activates skills autonomously) ──
        if tc.name == "use_skill":
            # Insert skill prompt into message history before execution
            result = tools.execute_with_skills(tc.name, tc.args)
            if "activated" in result and skill_manager.active:
                _inject_skill_prompt(messages)
            elif "deactivated" in result:
                messages[:] = [m for m in messages if not m.get("_skill_prompt")]
            state["cost"] += 0.001
            print_system_msg(result.replace("'", ""))
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "name": tc.name, "content": result})
            continue

        print_tool_msg(tc.name, json.dumps(tc.args, ensure_ascii=False))
        result = tools.execute_with_skills(tc.name, tc.args)
        messages.append({"role": "tool", "tool_call_id": tc.id,
                         "name": tc.name, "content": result})
        state["cost"] += 0.001
    return messages


def run_chat_turn(provider, messages, state, tool_defs, cfg):
    """Run the inner AI conversation loop (max_turns iterations).
    Returns (messages, state)."""
    max_turns = cfg.get("max_turns", 10)
    for turn in range(max_turns):
        try:
            content, tool_calls = provider.chat(
                messages, tool_defs, cfg.get("temperature", 0.7)
            )
        except Exception as e:
            print_system_msg(f"Error: {e}")
            break
        state["cost"] += 0.002
        if content and content.startswith("[思考中]"):
            end_idx = content.find("[/思考中]")
            if end_idx > 0:
                reasoning = content[len("[思考中]"):end_idx].strip()
                content = content[end_idx + len("[/思考中]"):].strip()
                if reasoning:
                    state["_last_reasoning"] = reasoning
                    print_reasoning(reasoning)
        if tool_calls:
            tc_list = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name,
                              "arguments": json.dumps(tc.args, ensure_ascii=False)}}
                for tc in tool_calls
            ]
            messages.append({
                "role": "assistant", "content": content or None,
                "tool_calls": tc_list,
            })
            # Show tool intent before execution
            for tc in tool_calls:
                print_tool_call(tc.name, json.dumps(tc.args, ensure_ascii=False))
            messages = process_tool_calls(tool_calls, messages, state)
        else:
            messages.append({"role": "assistant", "content": content})
            if content:
                print_ai_msg(content)
            break
    else:
        print_system_msg("Max turns reached")
    return messages, state


def run_stream_turn(provider, messages, state, tool_defs, cfg):
    """Run one conversation turn with live streaming display.
    Falls back to run_chat_turn() if provider does not support streaming."""
    if not hasattr(provider, "stream"):
        return run_chat_turn(provider, messages, state, tool_defs, cfg)

    max_turns = cfg.get("max_turns", 10)
    for turn in range(max_turns):
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
                    _, tool_calls = event["data"]
                    stream_done = True
                    break
            if not err_msg and not stream_done:
                err_msg = "Stream ended unexpectedly (possible connection timeout)"

        if err_msg:
            print_system_msg(f"Error: {err_msg}")
            break

        state["cost"] += 0.002
        content = "".join(content_chunks)
        full_reasoning = "".join(reasoning_chunks)
        if full_reasoning:
            state["_last_reasoning"] = full_reasoning
            print_reasoning(full_reasoning)

        # Strip any [思考中] tags that the provider may have prepended
        if content and content.startswith("["):
            end_idx = content.find("[/")
            if end_idx > 0:
                close_bracket = content.find("]", end_idx)
                if close_bracket > 0:
                    content = content[close_bracket + 1:].strip()

        if tool_calls:
            done()  # commit the streamed text before showing tool calls
            tc_list = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name,
                              "arguments": json.dumps(tc.args, ensure_ascii=False)}}
                for tc in tool_calls
            ]
            messages.append({
                "role": "assistant", "content": content or None,
                "tool_calls": tc_list,
            })
            for tc in tool_calls:
                print_tool_call(tc.name, json.dumps(tc.args, ensure_ascii=False))
            messages = process_tool_calls(tool_calls, messages, state)
        else:
            messages.append({"role": "assistant", "content": content})
            if content:
                done()  # print the final response panel
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

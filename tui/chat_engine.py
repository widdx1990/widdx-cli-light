"""TUI Chat Engine — streaming, tool execution, agent dispatch.

Synchronous core logic.  The UI layer (MainScreen) wraps calls in
``@work(thread=True)`` to keep the interface responsive.
"""

import json
from textual.message import Message
from core import tools as core_tools
from core.chat import _valid_tool_call_id, _build_tc_list, _sanitize_tool_call_ids
from core.providers.providers import estimate_turn_cost
from core.memory_learner import MemoryLearner
from core.skills import skill_manager
from core.uil import UnifiedIntelligenceLayer, ExecutionMode
from core.project_tracker import build_context_block


# ── UI Messages ──────────────────────────────────────────────
class ResultMsg(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()

class ErrorMsg(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()

class ToolStepMsg(Message):
    def __init__(self, tool: str, status: str, detail: str) -> None:
        self.tool = tool
        self.status = status
        self.detail = detail
        super().__init__()

class StreamChunkMsg(Message):
    def __init__(self, chunk: str) -> None:
        self.chunk = chunk
        super().__init__()

class StreamEndMsg(Message):
    def __init__(self, content: str, msgs: list) -> None:
        self.content = content
        self.msgs = msgs
        super().__init__()

class ThinkingMsg(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class ChatEngine:
    """Handles chat execution, routing, streaming, and tool calls.

    Uses ``self.screen`` to post messages (thread-safe).
    Uses ``self.app`` (the Textual App) for ``call_from_thread``.
    """

    def __init__(self, screen):
        self.screen = screen
        self.app = screen.app  # Textual App instance (has call_from_thread)
        self._processing = False

    # ── Main entry ──────────────────────────────────────────
    def start(self, text: str, state):
        """Start a chat interaction.  Routes to the right executor."""
        if self._processing or not text.strip():
            return
        self._processing = True

        state.messages.append({"role": "user", "content": text})
        state.turns += 1
        state.tools_used = []

        # Inject context for this turn
        msgs = list(state.messages)

        # Project docs
        try:
            pt_ctx = build_context_block(Path.cwd().resolve())
            if pt_ctx:
                msgs = [m for m in msgs if not m.get("_project_docs")]
                msgs.insert(0, {"role": "system", "content": pt_ctx, "_project_docs": True})
        except Exception:
            pass

        # Memory context
        try:
            ml = MemoryLearner(provider=state.provider)
            mem_ctx = ml.load_relevant(text)
            if mem_ctx:
                msgs = [m for m in msgs if not m.get("_memory_context")]
                msgs.insert(0, {"role": "system", "content": mem_ctx, "_memory_context": True})
        except Exception:
            pass

        # UIL routing
        try:
            uil = UnifiedIntelligenceLayer(provider=state.provider)
            uil.set_tool_defs(state.tool_defs)
            _, decision = uil.process(text)
            mode = decision.plan.mode if decision else ExecutionMode.SIMPLE_CHAT
        except Exception:
            mode = ExecutionMode.SIMPLE_CHAT

        if mode == ExecutionMode.EXPERT_TEAM:
            self.app.post_message(ThinkingMsg("🧠 Routing to Expert Team..."))
            self._run_expert_team(state, text)
        elif mode == ExecutionMode.AUTONOMOUS:
            self.app.post_message(ThinkingMsg("🧠 Routing to autonomous agent..."))
            self._run_agent(state, text)
        else:
            self._run_chat(state, msgs)

    def _finish(self):
        self._processing = False

    # ── Simple chat (streaming) ─────────────────────────────
    def _run_chat(self, state, msgs):
        cfg_t = state.cfg.get("temperature", 0.7)
        max_iter = state.cfg.get("max_turns", 10)

        try:
            if hasattr(state.provider, "stream"):
                self._stream_loop(state, msgs, cfg_t, max_iter)
            else:
                self._nonstream_loop(state, msgs, cfg_t, max_iter)
        except Exception as e:
            self.app.post_message(ErrorMsg(str(e)))
        finally:
            self.app.call_from_thread(self._finish)

    def _stream_loop(self, state, msgs, cfg_t, max_iter):
        model_name = state.model.split("/")[-1] or "unknown"

        for turn in range(max_iter):
            _sanitize_tool_call_ids(msgs)
            chunks = []
            reasoning = ""
            tool_calls = None
            err = None

            for event in state.provider.stream(msgs, state.tool_defs, cfg_t):
                if event["type"] == "content":
                    chunks.append(event["data"])
                elif event["type"] == "reasoning":
                    reasoning += event["data"]
                elif event["type"] == "error":
                    err = event["data"]
                    break
                elif event["type"] == "done":
                    _, tool_calls = event["data"]
                    break

            if reasoning:
                state._last_reasoning = reasoning
                self.app.post_message(ThinkingMsg(reasoning))

            if err:
                self.app.post_message(ErrorMsg(err))
                return

            content = "".join(chunks)
            state.cost += estimate_turn_cost(model_name, 500, 1000)

            if tool_calls:
                msgs = self._execute_tools(tool_calls, content, msgs, model_name, state)
            else:
                msgs.append({"role": "assistant", "content": content})
                self.app.post_message(StreamEndMsg(content, msgs))
                state.messages = msgs
                state.save_session()
                return

        self.app.post_message(StreamEndMsg("[Max iterations]", msgs))
        state.messages = msgs
        state.save_session()

    def _nonstream_loop(self, state, msgs, cfg_t, max_iter):
        model_name = state.model.split("/")[-1] or "unknown"
        for _ in range(max_iter):
            _sanitize_tool_call_ids(msgs)
            content, calls = state.provider.chat(msgs, state.tool_defs, cfg_t)
            state.cost += estimate_turn_cost(model_name, 500, 1000)

            if not calls:
                self.app.post_message(ResultMsg(content))
                state.messages = msgs
                state.save_session()
                return
            msgs = self._execute_tools(calls, content, msgs, model_name, state)

        self.app.post_message(ResultMsg("[Max iterations]"))

    # ── Tool execution ──────────────────────────────────────
    def _execute_tools(self, tool_calls, content, msgs, model_name, state):
        tc_list = _build_tc_list(tool_calls)
        msgs.append({"role": "assistant", "content": content or None, "tool_calls": tc_list})

        for tc in tool_calls:
            state.turns += 1

            if tc.name == "use_skill":
                result = core_tools.execute_with_skills(tc.name, tc.args)
                if "activated" in result and skill_manager.active:
                    msgs = [m for m in msgs if not m.get("_skill_prompt")]
                    msgs.insert(0, {"role": "system", "content": skill_manager.active.prompt, "_skill_prompt": True})
                elif "deactivated" in result:
                    msgs[:] = [m for m in msgs if not m.get("_skill_prompt")]
                msgs.append({"role": "tool", "tool_call_id": _valid_tool_call_id(tc.id), "name": tc.name, "content": result})
                state.cost += estimate_turn_cost(model_name, 200, 50)
                continue

            if tc.name not in state.tools_used:
                state.tools_used.append(tc.name)

            try:
                result = core_tools.execute_with_skills(tc.name, tc.args)
            except Exception as te:
                result = f"[Tool error: {te}]"

            state.cost += estimate_turn_cost(model_name, 200, 100)
            msgs.append({"role": "tool", "tool_call_id": _valid_tool_call_id(tc.id), "name": tc.name, "content": result})
            self.app.post_message(ToolStepMsg(tc.name, "ok", result[:200]))

        return msgs

    # ── Agent (AutonomousAgent) ─────────────────────────────
    def _run_agent(self, state, task):
        try:
            from core.agents.agent import AutonomousAgent
            agent = AutonomousAgent(state.provider, state.tool_defs, state.cfg, {
                "model": state.model, "cost": state.cost, "turns": state.turns,
            })
            steps, summary = agent.run(task)
            state.cost = agent.state.get("cost", state.cost)
            state.turns = agent.state.get("turns", state.turns)
            state.messages.append({"role": "assistant", "content": summary})
            state.save_session()
            self.app.post_message(ResultMsg(summary))
        except Exception as e:
            self.app.post_message(ErrorMsg(str(e)))
        finally:
            self.app.call_from_thread(self._finish)

    # ── Expert Team ─────────────────────────────────────────
    def _run_expert_team(self, state, task):
        try:
            from core.agents.expert import ExpertTeam
            team = ExpertTeam(state.provider, state.tool_defs, state.cfg, {
                "model": state.model, "cost": state.cost, "turns": state.turns,
            })
            summary = team.run(task)
            state.messages.append({"role": "assistant", "content": summary})
            state.save_session()
            self.app.post_message(ResultMsg(summary))
        except Exception as e:
            self.app.post_message(ErrorMsg(str(e)))
        finally:
            self.app.call_from_thread(self._finish)

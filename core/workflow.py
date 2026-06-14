"""Workflow Engine — spawn sub-agents in parallel/pipeline.

Inspired by WIDDX's Workflow system.

Three primitives:
  agent(prompt, tools=None)  → spawn a sub-agent, get its result
  parallel([thunk1, ...])    → run callables concurrently via threads
  pipeline(items, s1, s2)   → process items through staged transforms

Synchronous (no asyncio) — parallelism uses threading for I/O-bound LLM calls.
"""

import json, threading, time, traceback
from typing import Any, Callable, Optional


class WorkflowEngine:
    """Orchestrates multiple sub-agents for complex tasks."""

    def __init__(self, provider, tool_defs: list, cfg: dict, state: dict):
        self.provider = provider
        self.tool_defs = tool_defs
        self.cfg = cfg
        self.state = state
        self._results: dict[str, Any] = {}

    # ── agent — run a single sub-agent ────────────────────────────────

    def agent(self, prompt: str,
              tool_defs: Optional[list] = None,
              label: str = "") -> str:
        """Run a sub-agent and return its summary.

        Args:
            prompt: The task description for the sub-agent.
            tool_defs: Optional subset of tools (defaults to all).
            label: Optional label for logging.

        Returns:
            The sub-agent's final summary string.
        """
        from core.agents.agent import AutonomousAgent

        tools = tool_defs or self.tool_defs
        ag = AutonomousAgent(self.provider, tools, self.cfg, self.state,
                             custom_prompt=self._agent_prompt(prompt))
        steps, summary = ag.run(prompt)
        key = label or prompt[:40]
        self._results[key] = {"steps": len(steps), "summary": summary[:200]}
        return summary

    # ── parallel — run multiple agents concurrently ───────────────────

    def parallel(self, thunks: list[Callable[[], str]],
                 timeout: int = 300) -> list[str]:
        """Run callables concurrently using threads.

        Args:
            thunks: List of zero-arg callables (usually lambdas).
            timeout: Max seconds per thunk.

        Returns:
            List of results in the same order as thunks.
            Failed thunks return an error string (never raise).
        """
        results: list[str] = [""] * len(thunks)
        errors: list[Optional[str]] = [None] * len(thunks)

        def _run(idx: int):
            try:
                results[idx] = thunks[idx]()
            except Exception as e:
                errors[idx] = f"{e}\n{traceback.format_exc()}"
                results[idx] = f"Error: {e}"

        threads = []
        for idx in range(len(thunks)):
            t = threading.Thread(target=_run, args=(idx,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=timeout)

        for idx, err in enumerate(errors):
            if err:
                results[idx] = f"⚠️ Sub-agent failed: {err[:200]}"

        return results

    # ── pipeline — staged processing ──────────────────────────────────

    def pipeline(self, items: list, *stages: Callable) -> list:
        """Process items through sequential stages.

        Each stage receives (prev_result, original_item, index)
        and returns a transformed result.

        Args:
            items: Input items to process.
            stages: One or more transform callables.

        Returns:
            List of final results (same order as items).
            Failed items return None (never raise).
        """
        results: list = list(items)
        for stage_idx, stage in enumerate(stages):
            new_results: list = []
            for idx, item in enumerate(results):
                prev = results[idx] if stage_idx > 0 else None
                original = items[idx] if idx < len(items) else item
                try:
                    new_results.append(stage(prev, original, idx))
                except Exception as e:
                    new_results.append(None)
            results = new_results
        return results

    # ── tools for AI to use workflow ──────────────────────────────────

    def get_tool_definitions(self) -> list[dict]:
        """Return workflow tool definitions for the AI to call."""
        return [
            {
                "name": "create_agent",
                "description": "Spawn a sub-agent to work on a subtask independently. "
                               "The sub-agent has its own tools and returns a summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The exact task for the sub-agent",
                        },
                        "label": {
                            "type": "string",
                            "description": "Optional short label for tracking",
                        },
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "run_parallel",
                "description": "Run multiple sub-agent tasks CONCURRENTLY. "
                               "All tasks start at once and run in parallel threads. "
                               "Returns results when ALL complete.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of task prompts, one per sub-agent",
                            "minItems": 1,
                            "maxItems": 8,
                        },
                    },
                    "required": ["tasks"],
                },
            },
        ]

    def execute_workflow_tool(self, name: str, args: dict) -> str:
        """Execute a workflow tool call from the AI."""
        if name == "create_agent":
            prompt = args.get("prompt", "")
            label = args.get("label", "")
            return self.agent(prompt, label=label)

        elif name == "run_parallel":
            tasks: list[str] = args.get("tasks", [])
            if not tasks:
                return "No tasks provided for parallel execution"

            thunks = [
                lambda t=task: self.agent(t, label=f"parallel-{i}")
                for i, task in enumerate(tasks)
            ]
            results = self.parallel(thunks)
            parts = [f"=== Parallel Results ({len(results)} tasks) ==="]
            for i, (task, res) in enumerate(zip(tasks, results)):
                parts.append(f"\n--- Task {i+1}: {task[:60]} ---")
                parts.append(res[:500])
            return "\n".join(parts)

        return f"Unknown workflow tool: {name}"

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _agent_prompt(task: str) -> str:
        """Build a focused sub-agent system prompt."""
        return (
            "You are a focused sub-agent. Complete the following task.\n\n"
            "RULES:\n"
            "1. Use tools to accomplish the task\n"
            "2. Do not ask for clarification — make reasonable assumptions\n"
            "3. When done, provide a concise summary of what was accomplished\n"
            "4. If you hit errors, try a different approach before giving up\n\n"
            f"TASK:\n{task}"
        )

    def get_status(self) -> str:
        """Return a summary of completed workflow runs."""
        if not self._results:
            return "No workflow runs yet."
        parts = []
        for key, val in list(self._results.items())[:10]:
            parts.append(f"  {key}: {val['steps']} steps, summary: {val['summary'][:60]}")
        return "\n".join(parts)

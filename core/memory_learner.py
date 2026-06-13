"""Memory Learner — auto-extract facts from conversations using the LLM."""

import json, time
from typing import Optional
from .memory import MemoryStore
from .utils import to_slug


class MemoryLearner:
    """Extracts and stores memories from conversation turns.

    Uses a lightweight LLM prompt to identify facts worth remembering,
    then stores them in the existing MemoryStore for future retrieval.
    """

    MEMORY_TYPES = {
        "user_preference":    "User stated a preference (language, style, tool, approach)",
        "project_convention": "Project-specific convention or rule (naming, architecture, pattern)",
        "learned_fix":        "A specific fix or solution to a problem",
        "tool_usage_pattern": "How to use a specific tool or command effectively",
    }

    def __init__(self, provider=None, memory_store: MemoryStore | None = None):
        self.provider = provider
        self.mem = memory_store or MemoryStore()

    # ── Main API ────────────────────────────────────────

    def extract_from_turn(self, user_input: str, assistant_response: str,
                          tools_used: list[str]) -> list[dict]:
        """Use LLM to extract 0-2 facts from the current turn.

        Returns list of {"name", "content", "type", "context"} dicts.
        Empty list if nothing worth remembering or LLM is unavailable.
        """
        if not self.provider:
            return []
        if len(assistant_response) < 100:
            return []  # too short to contain learnable facts

        prompt = self._build_prompt(user_input, assistant_response, tools_used)
        try:
            content, _ = self.provider.chat(
                [{"role": "user", "content": prompt}], [], temperature=0.1,
            )
            return self._parse_memories(content or "")
        except Exception:
            return []

    def store_memories(self, memories: list[dict]):
        """Save extracted memories to MemoryStore."""
        for m in memories:
            name = to_slug(m.get("name", f"fact-{int(time.time())}"))
            content = m.get("content", "")
            if not content.strip():
                continue
            self.mem.save(name, content, {
                "type": m.get("type", "learned_fix"),
                "context": m.get("context", ""),
                "source": "auto_extracted",
                "timestamp": time.time(),
            })

    def load_relevant(self, user_input: str, max_memories: int = 5) -> str:
        """Search memory for facts relevant to current input.

        Returns formatted string for injection, or empty string.
        """
        try:
            results = self.mem.search(user_input)
            if not results:
                return ""
            relevant = results[:max_memories]
            lines = ["[RELEVANT MEMORIES]"]
            for m in relevant:
                lines.append(f"  - {m.get('description', m.get('name', ''))[:120]}")
            return "\n".join(lines)
        except Exception:
            return ""

    # ── Internal ────────────────────────────────────────

    def _build_prompt(self, user_input: str, response: str, tools: list[str]) -> str:
        tools_str = ", ".join(tools[:5]) if tools else "none"
        return (
            "Extract 0-2 facts worth remembering from this exchange. "
            "Focus on user preferences, project conventions, learned fixes, "
            "and tool usage patterns.\n\n"
            f"User: {user_input[:300]}\n"
            f"Assistant: {response[:500]}\n"
            f"Tools used: {tools_str}\n\n"
            'Output ONLY a JSON array, e.g.: '
            '[{"name":"use-httpx","content":"User prefers httpx over requests",'
            '"type":"user_preference","context":"HTTP client choice"}]\n'
            'Output [] if nothing worth remembering.'
        )

    def _parse_memories(self, output: str) -> list[dict]:
        """Parse LLM JSON output into structured memory dicts."""
        try:
            # Find JSON array in output
            import re
            m = re.search(r'\[.*\]', output, re.DOTALL)
            if not m:
                return []
            data = json.loads(m.group(0))
            if not isinstance(data, list):
                return []
            # Validate fields
            result = []
            for item in data[:2]:  # max 2
                if isinstance(item, dict) and item.get("name") and item.get("content"):
                    result.append({
                        "name": str(item["name"])[:40],
                        "content": str(item["content"])[:200],
                        "type": str(item.get("type", "learned_fix")),
                        "context": str(item.get("context", ""))[:60],
                    })
            return result
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

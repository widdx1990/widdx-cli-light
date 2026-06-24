"""Ollama provider — local LLM integration."""
from __future__ import annotations

import json, time, uuid
import httpx

from .base import Provider, ToolCall, _clean_surrogates, _DEFAULT_MAX_TOKENS, _TOOL_CAPABLE_PATTERNS, _REASONING_PATTERNS

import logging as _logging
logger = _logging.getLogger("widdx.providers")

class OllamaProvider(Provider):
    # \u2500\u2500 Class-level capability cache \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    _capabilities: dict[str, dict] = {}  # model_name \u2192 {"tools": bool, "reasoning": bool}

    def _get_capabilities(self) -> dict:
        """Detect model capabilities (tools, reasoning).

        Results are cached per model name so the probe runs at most once.
        """
        if self.model in self._capabilities:
            return self._capabilities[self.model]

        caps = {"tools": False, "reasoning": False}
        model_lower = self.model.lower()

        # \u2500\u2500 1. Lightweight probe: send a ping with a dummy tool \u2500\u2500
        try:
            url = f"{self.base_url}/v1/chat/completions"
            body = {
                "model": self.model,
                "messages": [{"role": "user", "content": "reply with exactly: ok"}],
                "max_tokens": 10,
                "temperature": 0,
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "_ping",
                        "description": "test probe \u2014 ignore",
                        "parameters": {"type": "object", "properties": {}, "required": []},
                    },
                }],
            }
            resp = httpx.post(url, json=body, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                if msg.get("tool_calls"):
                    caps["tools"] = True
                # Check for native reasoning_content field
                if msg.get("reasoning_content"):
                    caps["reasoning"] = True
        except Exception:
            pass  # probe failed \u2192 assume no capabilities, fall through to heuristics

        # \u2500\u2500 2. Name-based heuristics \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        if not caps["tools"]:
            for pat in _TOOL_CAPABLE_PATTERNS:
                if pat in model_lower:
                    caps["tools"] = True
                    break

        if not caps["reasoning"]:
            for pat in _REASONING_PATTERNS:
                if pat in model_lower:
                    caps["reasoning"] = True
                    break

        # Also check for "think" / "reasoning" in model name
        if not caps["reasoning"]:
            if "think" in model_lower or "reason" in model_lower:
                caps["reasoning"] = True

        self._capabilities[self.model] = caps
        return caps

    # \u2500\u2500 Unified response parser \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _parse_response(self, data: dict) -> tuple[str, list]:
        """Parse an OpenAI-compatible chat/completions response.

        Handles: content, native tool_calls, and native reasoning_content.
        """
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        content = _clean_surrogates(msg.get("content") or "")

        # ── Native reasoning_content (DeepSeek-R1, QwQ, etc.) ──
        reasoning = _clean_surrogates(msg.get("reasoning_content") or "")
        if reasoning:
            content = f"[thinking]\n{reasoning}\n[/thinking]\n\n" + (content or "")

        # ── Native tool_calls ──────────────────────────────────
        calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            func = tc.get("function", {})
            raw = func.get("arguments", "{}")
            if isinstance(raw, str):
                raw = _clean_surrogates(raw)
                try:
                    raw = json.loads(raw) if raw.strip() else {}
                except json.JSONDecodeError:
                    raw = {}
            call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"
            calls.append(ToolCall(name=func.get("name", ""), args=raw, id=call_id))

        return content, calls

    # \u2500\u2500 Thinking extraction from content \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    @staticmethod
    def _extract_thinking_from_content(content: str) -> tuple[str, str]:
        """Extract \u2026 or [thinking]\u2026[/thinking] blocks from content.

        Many small models embed reasoning inline in the text.
        Returns (reasoning, cleaned_content).
        """
        import re

        reasoning = ""
        cleaned = content

        # Pattern 1: <thinking>...</thinking> (Qwen, DeepSeek style)
        m = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
        if m:
            reasoning = m.group(1).strip()
            cleaned = content[:m.start()] + content[m.end():]
            return reasoning, cleaned.strip()

        # Pattern 2: [thinking]...[/thinking] (bracket style)
        m = re.search(r'\[thinking\]\s*(.*?)\s*\[/thinking\]', content, re.DOTALL | re.IGNORECASE)
        if m:
            reasoning = m.group(1).strip()
            cleaned = content[:m.start()] + content[m.end():]
            return reasoning, cleaned.strip()

        # Pattern 3: <thinking>... (unclosed think tag \u2014 DeepSeek streaming)
        # NOTE: This pattern only catches incomplete streaming fragments where
        # the closing tag hasn't arrived yet. It only fires when there is
        # substantial content AFTER the <thinking> block.
        m = re.search(r'<thinking>(.*?)$', content, re.DOTALL)
        if m:
            reasoning = m.group(1).strip()
            # With $ and re.DOTALL, (.*?) captures to end-of-content.
            # Only use the thinking content if there's actual reasoning text.
            if len(reasoning) > 10:
                return reasoning, ""

        return reasoning, cleaned

    # \u2500\u2500 Text-based tool description builder \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    @staticmethod
    def _build_text_tools_prompt(tool_defs: list) -> str:
        """Convert structured tool definitions into a text prompt.

        Used when the model does NOT support native function calling.
        """
        if not tool_defs:
            return ""

        lines = [
            "",
            "## Available Tools",
            "",
            "You have access to tools. To call a tool, output EXACTLY one JSON block:",
            "",
            "```tool",
            '{"tool": "<tool_name>", "arguments": {"arg1": "value1", ...}}',
            "```",
            "",
            "Wait for the tool result before calling another tool or giving your final answer.",
            "Only call a tool when you actually need it to complete the task.",
            "",
            "### Tool Reference:",
            "",
        ]

        for t in tool_defs:
            name = t.get("name", "?")
            desc = t.get("description", "")
            params = t.get("parameters", {})
            props = params.get("properties", {}) if isinstance(params, dict) else {}
            required = params.get("required", []) if isinstance(params, dict) else []

            lines.append(f"**{name}** \u2014 {desc}")
            if props:
                for pname, pinfo in props.items():
                    ptype = pinfo.get("type", "string") if isinstance(pinfo, dict) else "string"
                    pdesc = pinfo.get("description", "") if isinstance(pinfo, dict) else ""
                    req_mark = " *(required)*" if pname in required else ""
                    lines.append(f"  \u2022 `{pname}` ({ptype}){req_mark}: {pdesc}")
            lines.append("")

        return "\n".join(lines)

    # \u2500\u2500 Text-based tool call parser \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    @staticmethod
    def _parse_text_tool_calls(content: str) -> tuple[str, list[ToolCall]]:
        """Parse model text for tool-call JSON blocks.

        Returns (cleaned_content, list_of_ToolCall).
        The tool JSON blocks are removed from the returned content.
        """
        import re

        tool_calls: list[ToolCall] = []
        cleaned = content

        # Pattern 1: ```tool\n{"tool": ..., "arguments": {...}}\n```
        for m in re.finditer(r'```tool\s*\n(\{.+?\})\s*\n```', content, re.DOTALL):
            try:
                data = json.loads(m.group(1))
                name = data.get("tool", "")
                args = data.get("arguments", {})
                if isinstance(name, str) and name:
                    call_id = f"call_{uuid.uuid4().hex[:12]}"
                    tool_calls.append(ToolCall(name=name, args=args, id=call_id))
                    cleaned = cleaned.replace(m.group(0), "", 1)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Pattern 2: ```json\n{"tool": ..., "arguments": {...}}\n```  (looser match)
        if not tool_calls:
            for m in re.finditer(r'```json\s*\n\s*(\{.+?"tool".+?\})\s*\n```', content, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    name = data.get("tool", "")
                    args = data.get("arguments", {})
                    if isinstance(name, str) and name:
                        call_id = f"call_{uuid.uuid4().hex[:12]}"
                        tool_calls.append(ToolCall(name=name, args=args, id=call_id))
                        cleaned = cleaned.replace(m.group(0), "", 1)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

        # Pattern 3: inline {"tool": "name", "arguments": {...}} (standalone JSON object)
        if not tool_calls:
            for m in re.finditer(
                r'\{\s*"tool"\s*:\s*"(\w[\w.-]*)"\s*,\s*"arguments"\s*:\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*\}',
                content,
            ):
                name = m.group(1)
                try:
                    args = json.loads(m.group(2))
                    call_id = f"call_{uuid.uuid4().hex[:12]}"
                    tool_calls.append(ToolCall(name=name, args=args, id=call_id))
                    cleaned = cleaned.replace(m.group(0), "", 1)
                except (json.JSONDecodeError, TypeError):
                    pass

        return cleaned.strip(), tool_calls

    # \u2500\u2500 Chat paths \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _chat_native(self, messages: list, tool_defs: list, temperature: float) -> tuple[str, list]:
        """Path A: model supports native function calling."""
        url = f"{self.base_url}/v1/chat/completions"
        schema = self.build_tools_schema(tool_defs)
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        if schema:
            body["tools"] = schema
        try:
            resp = httpx.post(url, json=body, timeout=300)
            resp.raise_for_status()
            return self._parse_response(resp.json())
        except httpx.ConnectError:
            return f"\u26a0\ufe0f  Cannot connect to Ollama at {self.base_url}\nRun: ollama serve", []
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:300] if e.response.text else str(e)
            return f"\u26a0\ufe0f  Ollama error {e.response.status_code}: {detail}", []

    def _chat_text_tools(self, messages: list, tool_defs: list, temperature: float) -> tuple[str, list]:
        """Path B: model does NOT support native tools.

        1. Remap ``role=tool`` messages to ``role=user`` (the model doesn't understand tool role).
        2. Inject tool descriptions as a labeled system message.
        3. Send request WITHOUT the ``tools`` field.
        4. Parse the text response for JSON tool-call blocks.
        5. Extract any inline thinking / reasoning from the content.
        """
        url = f"{self.base_url}/v1/chat/completions"

        # \u2500\u2500 1. Remap tool messages \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        remapped: list[dict] = []
        for m in messages:
            if m.get("role") == "tool":
                remapped.append({
                    "role": "user",
                    "content": (
                        f"[Tool Result: {m.get('name', 'unknown')}]\n"
                        f"{m.get('content', '')}"
                    ),
                })
            else:
                remapped.append(m)

        # \u2500\u2500 2. Inject tool descriptions (tagged so we can strip on re-entry) \u2500\u2500
        tools_text = self._build_text_tools_prompt(tool_defs)
        # Remove any previous tool-desc message to avoid duplication
        remapped = [m for m in remapped if not m.get("_tool_desc")]
        if tools_text:
            remapped.append({
                "role": "system",
                "content": tools_text,
                "_tool_desc": True,
            })

        body = {
            "model": self.model,
            "messages": remapped,
            "temperature": temperature,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            # No "tools" key \u2014 model doesn't support it
        }

        try:
            resp = httpx.post(url, json=body, timeout=300)
            resp.raise_for_status()
            content, _native_calls = self._parse_response(resp.json())

            # \u2500\u2500 3. Extract thinking from content \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
            reasoning, content = self._extract_thinking_from_content(content)
            if reasoning:
                content = f"[thinking]\n{reasoning}\n[/thinking]\n\n{content}"

            # \u2500\u2500 4. Parse text for tool calls \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
            cleaned, tool_calls = self._parse_text_tool_calls(content)

            return cleaned, tool_calls

        except httpx.ConnectError:
            return f"\u26a0\ufe0f  Cannot connect to Ollama at {self.base_url}\nRun: ollama serve", []
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:300] if e.response.text else str(e)
            return f"\u26a0\ufe0f  Ollama error {e.response.status_code}: {detail}", []

    def _chat_simple(self, messages: list, temperature: float) -> tuple[str, list]:
        """Path C: no tools at all \u2014 plain chat."""
        url = f"{self.base_url}/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        try:
            resp = httpx.post(url, json=body, timeout=300)
            resp.raise_for_status()
            content, _ = self._parse_response(resp.json())
            # Try to extract thinking from content
            reasoning, content = self._extract_thinking_from_content(content)
            if reasoning:
                content = f"[thinking]\n{reasoning}\n[/thinking]\n\n{content}"
            return content, []
        except httpx.ConnectError:
            return f"\u26a0\ufe0f  Cannot connect to Ollama at {self.base_url}\nRun: ollama serve", []
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:300] if e.response.text else str(e)
            return f"\u26a0\ufe0f  Ollama error {e.response.status_code}: {detail}", []

    # \u2500\u2500 Main entry point \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7) -> tuple[str, list]:
        """Run a chat completion, auto-selecting the right path.

        - Native tools supported  \u2192 send tools schema, parse tool_calls
        - No native tools         \u2192 text-based tool instructions + text parsing
        - No tools needed         \u2192 plain chat
        """
        caps = self._get_capabilities()

        if tool_defs and caps["tools"]:
            return self._chat_native(messages, tool_defs, temperature)
        elif tool_defs:
            return self._chat_text_tools(messages, tool_defs, temperature)
        else:
            return self._chat_simple(messages, temperature)


# ---------------------------------------------------------------------------
# OpenAI-Compatible Provider
# ---------------------------------------------------------------------------

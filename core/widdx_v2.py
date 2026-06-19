"""
WIDDX v2 - DEPRECATED
======================
This module is preserved for reference only.
All functionality has been consolidated into `core/chat.py` + `core/widdx.py`.

Key migration:
  - WIDDXV2.chat()        → use `core.chat.run_chat_turn()` / `run_stream_chat_turn()`
  - WIDDXV2.new_session() → use `core.session_v2.create_new_session()`
  - WIDDXV2.add_memory()  → use `core.memory.MemoryStore.save()`
"""

import warnings
warnings.warn(
    "core.widdx_v2 is deprecated. Use core.chat, core.session_v2, core.memory instead.",
    DeprecationWarning,
    stacklevel=2,
)

from .session_v2 import (
    SessionV2,
    get_current_session,
    set_current_session,
    create_new_session,
    load_session
)
from .skills_v2 import get_skill_registry
from .provider_router import get_provider_router
from .database import get_db


class WIDDXV2:
    def __init__(self):
        self.db = get_db()
        self.session = get_current_session()
        self.skills = get_skill_registry()
        self.providers = get_provider_router()
        
        if not self.session:
            self.session = create_new_session()
    
    def chat(self, user_input, stream=True):
        from .tools import get_tool_definitions, execute_tool
        
        suggested_skills = self.skills.suggest_for_input(user_input)
        
        messages = self._build_messages(user_input)
        
        tool_defs = get_tool_definitions()
        if self.skills.active:
            for t in self.skills.active.tools:
                tool_defs.append(t.to_openai_schema())
        
        if stream:
            return self._stream_chat(messages, tool_defs, execute_tool)
        else:
            return self._chat(messages, tool_defs, execute_tool)
    
    def _build_messages(self, user_input):
        messages = []
        
        system_prompt = self._get_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        memories_context = self._get_memories_context(user_input)
        if memories_context:
            messages.append({"role": "system", "content": memories_context})
        
        messages.extend(self.session.get_context(max_tokens=6000))
        
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _get_system_prompt(self):
        parts = [
            "You are WIDDX, a highly capable AI coding assistant.",
            "You have access to tools for reading, writing, and modifying code.",
            "Always use the appropriate tools when needed.",
            "Be helpful, thorough, and write clean, working code.",
            "",
        ]
        
        if self.skills.active:
            parts.append(self.skills.active.get_system_prompt())
        
        return "\n".join(parts)
    
    def _get_memories_context(self, query):
        memories = self.db.search_memories(query, limit=5)
        if not memories:
            return None
        
        lines = ["## Relevant Memories:"]
        for m in memories:
            lines.append(f"- {m['name']}: {m['description']}")
            if len(m['content']) < 500:
                lines.append(f"  {m['content']}")
            else:
                lines.append(f"  {m['content'][:500]}...")
        
        return "\n".join(lines)
    
    def _stream_chat(self, messages, tool_defs, execute_tool_fn):
        final_content = ""
        final_calls = []
        
        for event in self.providers.stream_with_fallback(messages, tool_defs):
            if event.get("type") == "content":
                final_content += event.get("data", "")
                yield event
            elif event.get("type") == "reasoning":
                yield event
            elif event.get("type") == "done":
                final_content, final_calls = event.get("data", ("", []))
                break
            elif event.get("type") == "error":
                yield event
                return
        
        self.session.add_message("assistant", final_content, final_calls)
        
        if final_calls:
            for tc in final_calls:
                result = self._handle_tool_call(tc, execute_tool_fn)
                self.session.add_message(
                    "tool", str(result),
                    tool_calls=[{"name": tc.name, "id": tc.id}]
                )
                yield {"type": "tool_result", "data": result}
    
    def _chat(self, messages, tool_defs, execute_tool_fn):
        content, calls = self.providers.chat_with_fallback(messages, tool_defs)
        
        self.session.add_message("assistant", content, calls)
        
        results = []
        if calls:
            for tc in calls:
                result = self._handle_tool_call(tc, execute_tool_fn)
                self.session.add_message(
                    "tool", str(result),
                    tool_calls=[{"name": tc.name, "id": tc.id}]
                )
                results.append(result)
        
        return content, results
    
    def _handle_tool_call(self, tc, execute_tool_fn):
        try:
            result = execute_tool_fn(tc.name, tc.args)
            return result
        except Exception as e:
            if self.skills.active:
                try:
                    return self.skills.execute_tool(tc.name, tc.args)
                except Exception as e2:
                    return f"Error executing tool: {e}\n{e2}"
            return f"Error executing tool: {e}"
    
    def new_session(self, name="New Session", branch="main"):
        self.session = create_new_session(name, branch)
        return self.session
    
    def load_session(self, session_id):
        self.session = load_session(session_id)
        return self.session
    
    def list_sessions(self, branch=None):
        return SessionV2.list_sessions(branch)
    
    def activate_skill(self, skill_id):
        return self.skills.activate(skill_id)
    
    def deactivate_skill(self):
        self.skills.deactivate()
    
    def list_skills(self):
        return self.skills.list_all()
    
    def suggest_skills(self, user_input):
        return self.skills.suggest_for_input(user_input)
    
    def add_memory(self, name, content, description=None, memory_type="general", tags=None):
        if tags is None:
            tags = []
        return self.db.add_memory(name, content, description, memory_type, tags)
    
    def list_memories(self, memory_type=None):
        return self.db.list_memories(memory_type)
    
    def search_memories(self, query):
        return self.db.search_memories(query)
    
    def switch_provider(self, name):
        self.providers.set_current(name)
    
    def list_providers(self):
        return self.providers.list_providers()


_widdx = None

def get_widdx():
    global _widdx
    if _widdx is None:
        _widdx = WIDDXV2()
    return _widdx

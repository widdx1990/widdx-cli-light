
"""
Session V2 - Durable Session Management
Inspired by OpenCode's Session Architecture
"""

from pathlib import Path

from .database import get_db


class SessionV2:
    def __init__(self, session_id=None, name="New Session", branch="main"):
        self.db = get_db()
        if session_id:
            existing = self.db.get_session(session_id)
            if existing:
                self.id = existing["id"]
                self.name = existing["name"]
                self.branch = existing["branch"]
                self.metadata = existing["metadata"]
                self._messages = self.db.get_messages(session_id)
                return
        self.id = self.db.create_session(name, branch)
        self.name = name
        self.branch = branch
        self.metadata = {}
        self._messages = []
    
    @property
    def messages(self):
        return self._messages.copy()
    
    def add_message(self, role, content, tool_calls=None):
        msg_id = self.db.add_message(self.id, role, content, tool_calls)
        self._messages = self.db.get_messages(self.id)
        return msg_id
    
    def clear(self):
        self.db.clear_messages(self.id)
        self._messages = []
    
    def rename(self, new_name):
        self.name = new_name
        self.db.update_session(self.id, name=new_name)
    
    def switch_branch(self, new_branch):
        self.branch = new_branch
        self.db.update_session(self.id, branch=new_branch)
    
    def get_context(self, max_tokens=8000, max_messages=None):
        messages = self._messages.copy()
        if max_messages:
            if len(messages) > max_messages:
                messages = messages[-max_messages:]
        
        total_chars = 0
        trimmed = []
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]
        
        trimmed.extend(system_msgs)
        total_chars += sum(len(m["content"]) for m in system_msgs)
        
        for msg in reversed(other_msgs):
            msg_chars = len(msg["content"])
            if total_chars + msg_chars > max_tokens * 4:
                break
            trimmed.insert(len(system_msgs), msg)
            total_chars += msg_chars
        
        return trimmed
    
    @staticmethod
    def list_sessions(branch=None, limit=50):
        db = get_db()
        return db.list_sessions(branch, limit)
    
    @staticmethod
    def delete(session_id):
        db = get_db()
        db.delete_session(session_id)
    
    def save(self, state: dict | None = None):
        """Persist session metadata and optional state to SQLite.

        Messages are already persisted in real time via ``add_message()``.
        This method syncs everything else: metadata, timestamps, and
        arbitrary state (cost, turns, model, etc.).

        ``update_session`` (database.py:136) automatically bumps
        ``updated_at`` when any field is passed.
        """
        if state:
            merged = dict(self.metadata)
            merged.update(state)
            self.metadata = merged

        self.db.update_session(self.id, metadata=self.metadata)

    def create_checkpoint(self, label: str = "") -> str:
        """Create a named restore point for this session."""
        from core.checkpoint import checkpoint_manager
        cpm = checkpoint_manager(Path.cwd())
        return cpm.create(label or f"session_{self.id}", self.messages, self.metadata)

    @staticmethod
    def search(query: str, branch: str | None = None, limit: int = 20) -> list[dict]:
        """Full-text search across sessions."""
        from core.session_search import SessionSearcher
        searcher = SessionSearcher()
        try:
            return searcher.search(query, branch=branch, limit=limit)
        except TypeError:
            return searcher.search(query, limit=limit)


_current_session = None

def get_current_session():
    return _current_session

def set_current_session(session):
    global _current_session
    _current_session = session

def create_new_session(name="New Session", branch="main"):
    session = SessionV2(name=name, branch=branch)
    set_current_session(session)
    return session

def load_session(session_id):
    session = SessionV2(session_id=session_id)
    if session:
        set_current_session(session)
    return session

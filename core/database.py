
"""
Durable Session Database for WIDDX
SQLite-based persistent storage for sessions, memories, and history
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path


def get_db_path(project_dir=None):
    if project_dir is None:
        project_dir = Path.cwd()
    widdx_dir = project_dir / ".widdx"
    widdx_dir.mkdir(exist_ok=True)
    return widdx_dir / "widdx.db"


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    branch TEXT DEFAULT 'main',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'general',
                    tags TEXT DEFAULT '[]',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provider_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    last_used INTEGER,
                    UNIQUE(provider_name, model_name)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)")
            conn.commit()
    
    def create_session(self, name, branch="main", metadata=None):
        session_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, name, branch, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, name, branch, now, now, json.dumps(metadata or {}))
            )
            conn.commit()
        return session_id
    
    def get_session(self, session_id):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "branch": row["branch"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "metadata": json.loads(row["metadata"])
                }
        return None
    
    def list_sessions(self, branch=None, limit=50):
        with self._get_conn() as conn:
            if branch:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE branch = ? ORDER BY updated_at DESC LIMIT ?",
                    (branch, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "branch": r["branch"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "metadata": json.loads(r["metadata"])
                }
                for r in rows
            ]
    
    def update_session(self, session_id, **kwargs):
        allowed_fields = ["name", "branch", "metadata"]
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed_fields:
                updates.append(f"{k} = ?")
                if k == "metadata":
                    params.append(json.dumps(v))
                else:
                    params.append(v)
        if updates:
            updates.append("updated_at = ?")
            params.append(int(datetime.now().timestamp()))
            params.append(session_id)
            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()
    
    def delete_session(self, session_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    def add_message(self, session_id, role, content, tool_calls=None):
        msg_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO messages (id, session_id, role, content, tool_calls, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, role, content, json.dumps(tool_calls or []) if tool_calls else None, now)
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
            conn.commit()
        return msg_id
    
    def get_messages(self, session_id, limit=None):
        with self._get_conn() as conn:
            if limit:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (session_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                    (session_id,)
                ).fetchall()
            return [
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "tool_calls": json.loads(r["tool_calls"]) if r["tool_calls"] else None,
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]
    
    def clear_messages(self, session_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()
    
    def add_memory(self, name, content, description=None, memory_type="general", tags=None):
        memory_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO memories (id, name, description, content, memory_type, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (memory_id, name, description or "", content, memory_type, json.dumps(tags or []), now, now)
            )
            conn.commit()
        return memory_id
    
    def get_memory(self, memory_id):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "tags": json.loads(row["tags"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        return None
    
    def list_memories(self, memory_type=None, limit=100):
        with self._get_conn() as conn:
            if memory_type:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE memory_type = ? ORDER BY updated_at DESC LIMIT ?",
                    (memory_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "content": r["content"],
                    "memory_type": r["memory_type"],
                    "tags": json.loads(r["tags"]),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]
    
    def search_memories(self, query, limit=20):
        with self._get_conn() as conn:
            search = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM memories WHERE name LIKE ? OR description LIKE ? OR content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (search, search, search, limit)
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "content": r["content"],
                    "memory_type": r["memory_type"],
                    "tags": json.loads(r["tags"]),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]
    
    def delete_memory(self, memory_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
    
    def record_provider_usage(self, provider_name, model_name, success, response_time):
        now = int(datetime.now().timestamp())
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO provider_stats (provider_name, model_name, success_count, failure_count, avg_response_time, last_used)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_name, model_name) DO UPDATE SET
                    success_count = success_count + excluded.success_count,
                    failure_count = failure_count + excluded.failure_count,
                    avg_response_time = (avg_response_time + excluded.avg_response_time) / 2,
                    last_used = excluded.last_used
            """, (
                provider_name, model_name, 
                1 if success else 0, 0 if success else 1,
                response_time, now
            ))
            conn.commit()
    
    def get_provider_stats(self, provider_name=None, model_name=None):
        with self._get_conn() as conn:
            query = "SELECT * FROM provider_stats WHERE 1=1"
            params = []
            if provider_name:
                query += " AND provider_name = ?"
                params.append(provider_name)
            if model_name:
                query += " AND model_name = ?"
                params.append(model_name)
            query += " ORDER BY last_used DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


_db = None

def get_db():
    global _db
    if _db is None:
        _db = Database()
    return _db

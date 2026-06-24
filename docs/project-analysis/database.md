# WIDDX Nexus — Database & Storage Reference

> SQLite schema, file-based storage, and data persistence patterns.

## Primary Database

**Location:** `<project>/.widdx/widdx.db` (SQLite)
**Engine:** Python `sqlite3` stdlib (no ORM)
**Connection:** One connection per operation (no connection pooling)

### Schema

#### `sessions` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `name` | TEXT | NOT NULL | Human-readable name |
| `branch` | TEXT | DEFAULT 'main' | Git branch |
| `created_at` | INTEGER | NOT NULL | Unix timestamp |
| `updated_at` | INTEGER | NOT NULL | Unix timestamp |
| `metadata` | TEXT | DEFAULT '{}' | JSON blob |

**Indexes:** `idx_sessions_updated` on `updated_at DESC`

#### `messages` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `session_id` | TEXT | NOT NULL, FK→sessions(id) CASCADE | Parent session |
| `role` | TEXT | NOT NULL | 'system', 'user', 'assistant', 'tool' |
| `content` | TEXT | NOT NULL | Message content |
| `tool_calls` | TEXT | NULLABLE | JSON array of tool calls |
| `timestamp` | INTEGER | NOT NULL | Unix timestamp |

**Indexes:** `idx_messages_session_id`, `idx_messages_timestamp DESC`

#### `memories` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID |
| `name` | TEXT | NOT NULL | Memory name |
| `description` | TEXT | — | Short description |
| `content` | TEXT | NOT NULL | Memory content |
| `memory_type` | TEXT | DEFAULT 'general' | 'user', 'feedback', 'project', 'reference' |
| `tags` | TEXT | DEFAULT '[]' | JSON array |
| `created_at` | INTEGER | NOT NULL | Unix timestamp |
| `updated_at` | INTEGER | NOT NULL | Unix timestamp |

**Indexes:** `idx_memories_type` on `memory_type`

#### `provider_stats` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| `provider_name` | TEXT | NOT NULL | Provider name |
| `model_name` | TEXT | NOT NULL | Model name |
| `success_count` | INTEGER | DEFAULT 0 | Successful calls |
| `failure_count` | INTEGER | DEFAULT 0 | Failed calls |
| `avg_response_time` | REAL | DEFAULT 0 | Average response time |
| `last_used` | INTEGER | — | Last use timestamp |

**Unique constraint:** `(provider_name, model_name)`
**Upsert:** Uses `ON CONFLICT ... DO UPDATE` for atomic updates.

### Database Access Pattern

```python
# Singleton pattern
from core.database import get_db
db = get_db()

# Session operations
session_id = db.create_session(name, branch)
session = db.get_session(session_id)
db.update_session(session_id, name=new_name)
db.delete_session(session_id)

# Message operations
msg_id = db.add_message(session_id, role, content, tool_calls)
messages = db.get_messages(session_id, limit=50)
db.clear_messages(session_id)

# Memory operations
mem_id = db.add_memory(name, content, description, memory_type, tags)
memory = db.get_memory(mem_id)
db.delete_memory(mem_id)
results = db.search_memories(query, limit=20)
```

## File-Based Storage

### Memory Store (markdown files)

**Location (global):** `~/.widdx/memory/`
**Location (project):** `<project>/.widdx/memory/`
**Index:** `MEMORY.md` in the parent directory

**Format:**
```markdown
---
name: my-fact
description: Short description
metadata:
  type: user
  updated: 2026-06-24T00:00:00+00:00
---
The actual memory content here.
```

**Conflict detection:** When overwriting, saves `.old.md` backup.

### Knowledge Store (JSON)

**Location:** `<project>/.widdx/knowledge.json`

**Format:**
```json
{
  "code_write": [
    {
      "task_type": "code_write",
      "execution_mode": "autonomous",
      "steps_planned": 2,
      "steps_completed": 2,
      "execution_time": 5.2,
      "success": true,
      "timestamp": 1719200000.0,
      "verification_criticals": 0,
      "verification_errors": 0
    }
  ]
}
```

**Access:**
```python
from core.uil.knowledge import KnowledgeBase
kb = KnowledgeBase()
kb.record(classification, result, decision)
stats = kb.get_stats("code_write")
mode = kb.suggest_mode("code_write")
```

### Session Workspace

**Location:** `~/.widdx/workspaces/<session_id>/`
**Auto-cleanup:** After 24 hours (`SessionWorkspace.cleanup_old()`)

### Workflow Storage

**Location:** `<project>/.widdx/workflows/<wf_id>.json`

**Format:**
```json
{
  "id": "wf_abc123",
  "name": "My Workflow",
  "steps": [
    {"type": "agent", "prompt": "Step 1 task"},
    {"type": "parallel", "tasks": ["Task A", "Task B"]}
  ],
  "created_at": 1719200000.0
}
```

### Configuration

**Location (resolution order):**
1. `<project>/.widdx/config.json` (project-local, writable)
2. `<project>/config.json` (bare in CWD, writable)
3. `<install_dir>/config.json` (bundled default, read-only)

**Secret stripping:** API keys are removed before writing to disk. Stored in:
- Environment variables (current process)
- Keychain (`core/config/keychain.py`) — obfuscated JSON fallback

### Cache Store

**Location:** In-memory only (LRU + TTL)
**Cache types:**
- `ResponseCache`: LLM response caching (keyed by content hash)
- `ToolResultCache`: Tool result caching (keyed by tool name + args hash)
- `invalidate_on_write()`: Clears read-only caches when files change

### Activity Log

**Location:** In-memory only (`ActivityStore`)
**Event types:** tool_call, agent_spawn, message, system

### Cron Jobs

**Location:** `<project>/.widdx/cron_jobs.json`
**Format:** JSON array of `CronJob` objects

### Error Patterns

**Location:** In-memory only (`ErrorPatternLearner`)
**Pattern tracking:** Counts recurring errors by (category, message_hash)

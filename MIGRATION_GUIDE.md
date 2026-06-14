
# WIDDX v2 Migration Guide

## What's New in WIDDX v2

WIDDX v2 brings major enhancements inspired by OpenCode's architecture! Here's what's new:

### 1. **Durable Sessions (SQLite Database)**
- All chat history is automatically saved to a SQLite database
- Multiple branches supported natively
- Session management with create/load/delete
- Persists across program restarts

### 2. **Enhanced Skills System**
- Skill registry with automatic discovery
- Trigger-based skill activation
- Custom tools per skill
- YAML frontmatter support for skill definitions

### 3. **Smart Provider Router**
- Automatic fallback chain
- Performance-based provider selection
- Success/failure tracking
- Priority-based ordering

### 4. **Unified Memory System**
- SQLite-backed memory storage
- Searchable memories with tags
- Memory types: user, project, reference, feedback

## Backward Compatibility

All your existing code should continue to work! The v1 modules are untouched.

## Quick Start with v2

### Option 1: Using the new WIDDXV2 class (Recommended)

```python
from core.widdx_v2 import get_widdx

# Initialize
widdx = get_widdx()

# Chat
for event in widdx.chat("Hello, what can you do?", stream=True):
    if event["type"] == "content":
        print(event["data"], end="")

# Session management
widdx.new_session("My New Project")
sessions = widdx.list_sessions()

# Skills
skills = widdx.list_skills()
widdx.activate_skill("code-review")

# Memory
widdx.add_memory(
    name="Important Note",
    content="Always use type hints!",
    memory_type="project"
)

# Provider switching
widdx.switch_provider("ollama")
```

### Option 2: Using individual components

```python
# Durable Sessions
from core.session_v2 import SessionV2, create_new_session, load_session

session = create_new_session("My Session")
session.add_message("user", "Hello")

# Skills
from core.skills_v2 import get_skill_registry

skills = get_skill_registry()
skills.activate("code-review")

# Provider Router
from core.provider_router import get_provider_router

router = get_provider_router()
content, calls = router.chat_with_fallback(messages, tools)
```

## Database Location

The SQLite database is stored at:
```
./.widdx/widdx.db
```

This includes:
- Sessions
- Chat history
- Memories
- Provider performance stats

## Upgrading Skills to v2

Skills in the `./skills/` directory will be automatically loaded! Each skill should have:

```
skills/
  my-skill/
    skill.md      # Skill definition with frontmatter
    tools.py      # (Optional) Custom tools
```

Example `skill.md`:
```markdown
---
id: my-skill
name: My Awesome Skill
icon: 🚀
description: Does awesome things!
triggers: awesome, amazing
---

You are an expert at awesome things. When a user asks for something awesome, 
help them create it with style!
```

## New Commands (Add these to your CLI!)

```python
# In your CLI add:
from core.widdx_v2 import get_widdx

widdx = get_widdx()

# /sessions [list]
# /session new &lt;name&gt;
# /session load &lt;id&gt;
# /memories [query]
# /remember &lt;name&gt; &lt;content&gt;
# /skills [list]
# /skill activate &lt;id&gt;
# /skill deactivate
# /providers [list]
# /provider &lt;name&gt;
```

## FAQ

**Q: Do I need to change my existing code?**
A: No! All v1 code continues to work exactly as before.

**Q: Can I use both v1 and v2 together?**
A: Absolutely! They are separate modules.

**Q: Where is my chat history stored?**
A: In `.widdx/widdx.db` - SQLite database you can inspect with any SQLite tool.

**Q: Can I import my old memories?**
A: Yes! You can read old memory files from `.widdx/memory/` and add them with `widdx.add_memory()`.

## Getting Help

If you run into issues:
1. Check that your `.widdx/` directory is writable
2. Make sure you have Python 3.10+
3. Check the logs for errors

Enjoy coding with WIDDX v2! 🚀

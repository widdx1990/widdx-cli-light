# Complete Bug Fix Plan — WIDDX Chat-Tool

## Phase 1: Critical Fixes (must fix — safety, portability, data loss)

### Task 1: Fix `config.json` — make paths dynamic
**Files:** `config.json`

**Problem:** Hardcoded Windows absolute paths (`e:/deepseek/chat-tool`, `C:/Users/widdx`) make the project non-portable.

**Solution:** 
- Replace hardcoded paths with `{PROJECT_ROOT}` placeholder in MCP server args
- Add a `project_root` auto-detection in `config/settings.py` that resolves `{PROJECT_ROOT}` relative to the config file location
- Example: `"args": ["{PROJECT_ROOT}/node_modules/..."]`

**Implementation:**
In `core/config/settings.py` — add a `_resolve_paths()` function that replaces `{PROJECT_ROOT}` with the directory containing config.json.

---

### Task 2: Fix `git.py` — safe undo with staged-changes warning
**File:** `core/project/git.py`, lines 50-93

**Problem:** `git reset --hard HEAD~1` permanently deletes uncommitted changes.

**Solution:**
- Change `--hard` to `--soft` to preserve all changes as staged
- Before executing undo, check if there are staged files (`git diff --cached --quiet`)
- If staged files exist, show a warning to the user before proceeding
- Keep existing checks (last commit message starts with "WIDDX:", commit count > 1)

Current:
```python
["git", "reset", "--hard", "HEAD~1"]
```
New:
```python
# Check for staged files first
staged_check = subprocess.run(
    ["git", "diff", "--cached", "--quiet"],
    cwd=path_str, capture_output=True, text=True, timeout=10,
)
has_staged = staged_check.returncode != 0
if has_staged:
    print_system_msg("Warning: You have staged changes that will be un-staged by undo.")
    # (confirmation dialog handled by caller)

["git", "reset", "--soft", "HEAD~1"]
```

---

### Task 3: Fix `tools.py` — strict UTF-8 errors in read/edit
**File:** `core/tools.py`, lines 201, 224, 232

**Problem:** `p.read_text(encoding="utf-8")` raises on non-UTF-8 files.

**Solution:** Add `errors="replace"` to all `read_text()` calls in `read()` and `edit()` functions.

Current:
```python
text = p.read_text(encoding="utf-8")
```
New:
```python
text = p.read_text(encoding="utf-8", errors="replace")
```

---

### Task 4: Fix `tools.py` — cross-platform command execution
**File:** `core/tools.py`, line 268-269

**Problem:** Hardcoded `["powershell", "-NoProfile", "-Command", command]` only works on Windows.

**Solution:** Detect OS at runtime:
```python
import platform
if platform.system() == "Windows":
    shell_cmd = ["powershell", "-NoProfile", "-Command", command]
else:
    shell_cmd = ["bash", "-c", command]
```

---

### Task 5: Fix `state.py` — preserve full session data (tool_calls)
**File:** `core/project/state.py`, `_serializable_messages()` lines 312-320

**Problem:** Only saves `role` and `content`, drops `tool_calls`, `_skill_prompt`, etc.

**Solution:** Preserve all serializable fields:
```python
def _serializable_messages(messages: list) -> list:
    cleaned = []
    for m in messages:
        entry = {"role": m["role"]}
        if m.get("content"):
            entry["content"] = m["content"]
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        if m.get("_skill_prompt"):
            entry["_skill_prompt"] = True
        if m.get("_summary"):
            entry["_summary"] = True
        cleaned.append(entry)
    return cleaned
```

---

### Task 6: Fix `mcp/client.py` — add read timeout + prevent infinite loop
**File:** `core/mcp/client.py`, `_send_jsonrpc()` lines 38-62

**Problem:** `readline()` in while loop has no timeout; can hang forever.

**Solution:**
- Use `threading.Timer` to enforce a global read timeout (works on both Windows and POSIX — most compatible approach)
- Set `READ_TIMEOUT = 30` seconds per response
- Track start time per request and break after 30 seconds
- Set max retry attempts for incomplete responses

Implementation approach:
```python
import threading

READ_TIMEOUT = 30

def _send_jsonrpc(self, method, params=None, msg_id=1):
    ...
    timer = threading.Timer(READ_TIMEOUT, self._timeout_read)
    timer.start()
    try:
        while self._proc.stdout:
            line = self._proc.stdout.readline()
            if not line:
                break
            ...  # process line
    finally:
        timer.cancel()

def _timeout_read(self):
    """Kill the subprocess on timeout to unblock readline()."""
    if self._proc:
        self._proc.kill()
```

---

### Task 7: Fix `router.py` — CODE domain modifier shouldn't add write to CODE_READ
**File:** `core/uil/router.py`, lines 70-78

**Problem:** `Domain.CODE` adds `["write", "bash"]` to ALL CODE tasks including CODE_READ, giving read tasks write permissions.

**Solution:** Apply domain modifiers only when the allowed patterns already include write-capable tools. Or split domain modifiers into additive vs restrictive. Simplest fix: check if current tool list (from `_TOOL_GROUPS`) already has write tools before adding more.

---

### Task 8: Fix all silent `except: pass` blocks
**Files:** `core/tools.py` line 259, `main.py` line 277

**Problem:** Empty except blocks hide bugs.

**Solution:**
- `main.py` line 277-278: Replace `pass` with `console.print_exception()` or at minimum log the error
- `tools.py` line 259: Log the exception instead of `pass`

---

## Phase 2: Medium Priority Fixes

### Task 9: Fix `state.py` — summarize_conversation keeps ALL system messages
**File:** `core/project/state.py`, `summarize_conversation()` lines 275-310

**Problem:** Only `messages[0]` is kept as system message; skill prompts and project instructions are summarized and lost.

**Solution:** Collect ALL system messages (including `_skill_prompt` and `_summary` flags) and preserve them, only summarizing user/assistant messages in between.

---

### Task 10: Fix `providers.py` — make DeepSeek thinking optional
**File:** `core/providers/providers.py`, lines 345-346

**Problem:** `thinking: {"type": "enabled"}` and `reasoning_effort: "high"` are hardcoded.

**Solution:** Add a config option `thinking: bool` to `config.json` and only send thinking params when enabled.

---

### Task 11: Fix `chat.py` — don't hardcode provider names for streaming
**File:** `core/chat.py`, line 100

**Problem:** Only "opencode-zen", "opencode", "deepseek" get streaming.

**Solution:** Check for `hasattr(provider, "stream")` alone — if the provider has a stream method, use it regardless of name.

---

### Task 12: Fix `main.py` — cache project index, rebuild only on change
**File:** `main.py`, line 263

**Problem:** `save_index()` rescans entire project after every user message.

**Solution:**
- Compute a content hash of the project directory listing (sorted file paths + mtimes)
- Store the last hash in memory and skip rebuild if hash unchanged
- Reset hash when a tool call creates/modifies/deletes files (track via tool results)
- This guarantees the index is always up-to-date but never rebuilt unnecessarily

Implementation approach in `main.py`:
```python
_last_index_hash = None

def _index_changed(project_dir) -> bool:
    root = Path(project_dir).resolve()
    # Quick check: hash of all file paths + their mtimes
    entries = []
    for f in sorted(root.rglob("*")):
        if f.is_file() and not any(part.startswith(".") for part in f.relative_to(root).parts):
            entries.append(f"{f.relative_to(root)}:{f.stat().st_mtime}")
    current_hash = hash("|".join(entries))
    global _last_index_hash
    if current_hash == _last_index_hash:
        return False
    _last_index_hash = current_hash
    return True
```

---

## Phase 3: Polish / Low Priority

### Task 13: Fix `manifest.py` — add missing ignore dirs
**File:** `core/project/manifest.py`, line 8

**Problem:** Only ignores `__pycache__` and `.git`, misses `node_modules`, `.venv`, `.pytest_cache`, `.widdx`.

**Solution:** Copy the comprehensive `IGNORE_DIRS` set from `state.py` line 106-108 into `manifest.py`.

---

### Task 14: Fix `tools.py` — glob sorting performance
**File:** `core/tools.py`, line 240

**Problem:** `key=lambda x: x.stat().st_mtime` calls stat() on every file.

**Solution:** Remove sorting by mtime (default sort is fine), or make it opt-in with a flag.

---

### Task 15: Fix `ui.py` — update stale header text
**File:** `core/ui/ui.py`, line 60

**Problem:** Header still shows "expert team" even though UIL is the entry point.

**Solution:** Update to reflect current routing (UIL + Expert Team fallback).

---

### Task 16: Fix `analyzer.py` — reduce ChatClassifier trigger overlap
**File:** `core/uil/analyzer.py`, ChatClassifier triggers lines 262-267

**Problem:** Generic words like "what is", "how do", "can you" overlap with specialized classifiers.

**Solution:** Either:
- Remove overlapping triggers from ChatClassifier
- Or increase MIN_MATCHES to 2 for ChatClassifier

---

## Execution Order & Dependencies

```
Phase 1 (Critical):
  Task 1 (config.json paths) — no deps
  Task 2 (git --hard) — no deps
  Task 3 (UTF-8 errors) — no deps
  Task 4 (cross-platform cmd) — no deps
  Task 5 (session data) — no deps
  Task 6 (MCP timeout) — no deps
  Task 7 (domain modifiers) — no deps
  Task 8 (except:pass) — no deps

Phase 2 (Medium):
  Task 9 (summarize system msgs) — depends on Task 5
  Task 10 (thinking option) — no deps
  Task 11 (streaming names) — no deps
  Task 12 (index caching) — no deps

Phase 3 (Polish):
  Task 13 (manifest ignore) — no deps
  Task 14 (glob sort) — no deps
  Task 15 (UI header) — no deps
  Task 16 (analyzer triggers) — no deps
```

All Phase 1 tasks can be done in parallel. Phase 2 and 3 are independent of each other. Only Task 9 depends on Task 5.

## Verification Strategy
- After each task: run existing tests with `pytest` to ensure no regressions
- After Task 1: verify `python -c "from core.config.settings import load; print(load())"` resolves paths correctly
- After Task 2: run `/undo` command and verify files are preserved
- After Task 5: save session, reload it, verify tool_calls are intact
- After Task 6: start app with MCP servers, verify no hang on disconnect
- After Task 12: check `.widdx/index.json` is not rewritten every turn

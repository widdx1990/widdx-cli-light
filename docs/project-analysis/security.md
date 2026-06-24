# WIDDX Nexus — Security Analysis

> Comprehensive security audit of the entire codebase with severity ratings.

## Security Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                      │
├─────────────────────────────────────────────────────────┤
│ Layer 1: API Authentication (Bearer token)             │
│ Layer 2: Rate Limiting (sliding window, 60 req/min)    │
│ Layer 3: CORS Restriction (localhost only)              │
│ Layer 4: Command Guard (dangerous pattern blocking)     │
│ Layer 5: Sandbox Isolation (WSL/Docker/subprocess)      │
│ Layer 6: File Path Sandboxing (_is_safe_path)           │
│ Layer 7: SSRF Protection (web_fetch URL validation)     │
│ Layer 8: API Key Stripping (env var sanitization)       │
│ Layer 9: Surrogate Sanitization (Unicode safety)        │
│ Layer 10: Permission Manager (tool-level permissions)   │
└─────────────────────────────────────────────────────────┘
```

## Security Issues Found

### 🔴 CRITICAL (Severity: Critical)

| # | Issue | File | Line | Description | Risk |
|---|-------|------|------|-------------|------|
| S1 | **shell=True fallback** | `core/sandbox.py` | 637-641 | If `shell=False` fails, retries with `shell=True` — allows shell injection | **HIGH** |
| S2 | **shell=True in web sandbox** | `scripts/web/sandbox.py` | 65 | `subprocess.Popen(command, shell=True)` — direct command injection via web API | **HIGH** |
| S3 | **shell=True in container** | `core/isolation/container.py` | 200 | Container execution uses `shell=True` | **MEDIUM** |
| S4 | **shell=True in validation** | `core/validation/runner.py` | 155 | Code runner uses `shell=True` | **MEDIUM** |
| S5 | **GitHub webhook no secret** | `github-app/app.py` | 43 | `WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")` — fail-open if empty | **HIGH** |
| S6 | **Hardcoded Windows paths** | `config.json` | MCP servers | Absolute `E:/deepseek/chat-tool/` paths — breaks on other machines and exposes filesystem layout | **MEDIUM** |

### 🟠 HIGH (Severity: High)

| # | Issue | File | Description | Risk |
|---|-------|------|-------------|------|
| S7 | **No input validation on chat API** | `scripts/api_server.py:195` | `message` field has no `max_length` — allows arbitrarily large payloads | **MEDIUM** |
| S8 | **Regex bypass for tool injection** | `core/tools/security.py` | `_scan_dangerous` uses regex that can be bypassed with 5+ techniques (Unicode, encoding, whitespace tricks) | **MEDIUM** |
| S9 | **MCP subprocess not isolated** | `core/mcp/client.py:152` | `MCPServerConnection` uses `subprocess.Popen` directly — no sandbox, no resource limits | **MEDIUM** |
| S10 | **API key in environment** | `core/config/keychain.py` | Keys stored in `os.environ` — visible to all child processes and crash dumps | **LOW** |
| S11 | **No request size limit** | `scripts/api_server.py` | FastAPI app has no `max_body_size` — vulnerable to memory exhaustion | **MEDIUM** |
| S12 | **Skill loader executes arbitrary code** | `core/skill_loader.py:37` | `exec_module()` runs Python files from `skills/` directory — supply chain risk | **MEDIUM** |
| S13 | **Docker runs as root** | `Dockerfile` | No `USER` directive — container processes run as root | **LOW** |

### 🟡 MEDIUM (Severity: Medium)

| # | Issue | File | Description | Risk |
|---|-------|------|-------------|------|
| S14 | **No CORS in web server** | `scripts/web/server.py` | Web server has no CORS middleware — any origin can make requests | **LOW** |
| S15 | **SQLite without WAL** | `core/database.py` | SQLite uses default journal mode — concurrent writes may corrupt | **LOW** |
| S16 | **No SQL parameterization concern** | `core/database.py:315` | `get_provider_stats` builds query with string concatenation (but uses params) — safe but fragile pattern | **LOW** |
| S17 | **Trust decisions are self-reported** | `core/engine_trust.py` | Trust scores based on self-reported metrics — no external validation | **LOW** |
| S18 | **In-memory rate limiter** | `scripts/api_server.py:58` | Rate limiter state lost on restart — no distributed rate limiting | **LOW** |
| S19 | **No HTTPS enforcement** | `scripts/api_server.py` | API server serves HTTP only — no TLS configuration | **LOW** |

### 🟢 LOW (Severity: Low)

| # | Issue | File | Description | Risk |
|---|-------|------|-------------|------|
| S20 | **Path traversal in MCP** | `core/mcp/client.py` | MCP filesystem server restricted to project directory but args come from LLM | **LOW** |
| S21 | **Logger may leak sensitive data** | Various | API keys, tokens may appear in log output at DEBUG level | **LOW** |
| S22 | **No Content-Security-Policy** | `scripts/web/server.py` | Web UI served without CSP headers | **LOW** |
| S23 | **WSL fallback is silent** | `core/sandbox.py:329` | When WSL is requested but unavailable, falls back to subprocess silently — user may not realize isolation is lost | **LOW** |
| S24 | **Tool cache not encrypted** | `core/cache.py` | Cached tool results stored in memory — accessible if process memory is dumped | **INFO** |

## SSRF Protection (web_fetch tool)

```python
# core/tools/__init__.py — _web_fetch()
# ✅ Blocks non-http(s) schemes
# ✅ Blocks localhost, 127.0.0.1, ::1, 0.0.0.0
# ✅ Blocks cloud metadata endpoints (169.254.169.254, metadata.google.internal)
# ⚠️ Does NOT block IPv6 loopback (::1) in hostname check (uses string match)
# ⚠️ Does NOT resolve DNS before checking — DNS rebinding possible
```

## Command Guard Patterns

### Blocked (never execute)
- Fork bombs (`:(){ :|:& };:`)
- `rm -rf /`, `rm -rf /home`, `rm -rf /etc`, etc.
- `mkfs`, `format`, `fdisk`, `dd if=`
- `chmod 777 /etc`, `chmod 777 /usr`
- Device overwrites (`> /dev/sda`)

### Warned (allow with warning)
- `rm -rf` (any target)
- `git reset --hard`
- `git push --force`
- `DROP TABLE`, `DROP DATABASE`
- `curl | bash`, `wget | bash`
- `shutdown`, `reboot`

## File Path Sandboxing

```python
# core/tools/__init__.py
_SAFE_DIR = None  # Set by configure()

def _is_safe_path(p: Path) -> bool:
    """Check if resolved path is inside sandbox directory."""
    if _SAFE_DIR is None:
        return True  # No sandbox configured
    try:
        p.resolve().relative_to(Path(_SAFE_DIR).resolve())
        return True
    except ValueError:
        return False
```

**Applied to:** `_read()`, `_write()`, `_edit()`, `_glob()`, `_grep()`, `_list_files()`, `_project_validate()`

## API Key Management

```
Resolution order:
  1. os.environ[provider_env]     — session-scoped
  2. os.environ[WIDDX_API_KEY]    — session-scoped
  3. ~/.widdx/api_keys.json       — persisted (obfuscated)

Stripping:
  - All child processes: env vars starting with WIDDX_API_KEY are removed
  - Config file: api_key stripped before writing to disk
  - API server: keys never logged at INFO level
```

## Recommendations

1. **S1-S4:** Replace all `shell=True` with explicit `shlex.split()` + `shell=False` where possible
2. **S5:** Make `WEBHOOK_SECRET` required for production deployments
3. **S7:** Add `max_length` to `ChatRequest.message` (e.g., 100,000 chars)
4. **S11:** Add `--limit-request-body` or configure FastAPI's `max_body_size`
5. **S12:** Implement skill code signing or at minimum hash verification
6. **S13:** Add `USER widdx` to Dockerfile
7. **S22:** Add Content-Security-Policy headers to web server

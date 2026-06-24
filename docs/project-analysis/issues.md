# WIDDX Nexus — Issues Register

> Complete catalog of all detected issues with severity, location, root cause, and affected files.

## Issue Severity Scale

| Severity | Impact | Urgency |
|----------|--------|---------|
| 🔴 CRITICAL | System broken, data loss, security breach | Fix immediately |
| 🟠 HIGH | Major functionality impaired, significant risk | Fix within 1 week |
| 🟡 MEDIUM | Workaround exists, moderate impact | Fix within 1 month |
| 🟢 LOW | Minor inconvenience, cosmetic | Fix when convenient |
| ⚪ INFO | Not a bug, but an observation | No action needed |

---

## 🔴 CRITICAL Issues

### CRIT-001: shell=True Fallback in Sandbox

| Field | Value |
|-------|-------|
| **File** | `core/sandbox.py:637-641` |
| **Location** | `_execute_subprocess()` method |
| **Root Cause** | When `shell=False` fails (FileNotFoundError), retries with `shell=True` — enabling shell injection |
| **Affected Files** | `core/tools/__init__.py` (calls `_bash` → `_handle_sandbox_exec` → `SandboxExecutor`) |
| **Suggested Fix** | Parse command with `shlex.split()` before Popen; only use `shell=True` as absolute last resort with additional validation |
| **Risk Level** | **HIGH** — Any user-crafted command can escape sandbox |

### CRIT-002: GitHub Webhook Fail-Open

| Field | Value |
|-------|-------|
| **File** | `github-app/app.py:43` |
| **Location** | `WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")` |
| **Root Cause** | Empty string fallback means webhook accepts ALL requests without verification |
| **Affected Files** | `github-app/app.py` (entire webhook handler) |
| **Suggested Fix** | Make `WEBHOOK_SECRET` required in production; reject requests when unset |
| **Risk Level** | **HIGH** — Unauthenticated webhook execution |

### CRIT-003: shell=True in Web Sandbox

| Field | Value |
|-------|-------|
| **File** | `scripts/web/sandbox.py:65` |
| **Location** | `SandboxHandler` class |
| **Root Cause** | `subprocess.Popen(command, shell=True)` — direct command injection via web API |
| **Affected Files** | `scripts/web/server.py` (exposes `/api/sandbox/exec` endpoint) |
| **Suggested Fix** | Use `shlex.split()` + `shell=False`; validate against CommandGuard |
| **Risk Level** | **HIGH** — Remote code execution via HTTP |

---

## 🟠 HIGH Issues

### HIGH-001: No Request Size Limit on Chat API

| Field | Value |
|-------|-------|
| **File** | `scripts/api_server.py:195` |
| **Location** | `ChatRequest` Pydantic model |
| **Root Cause** | `message: str` has no `max_length` constraint |
| **Affected Files** | `scripts/api_server.py` (POST /api/chat) |
| **Suggested Fix** | Add `message: str = Field(..., max_length=100000)` |
| **Risk Level** | **MEDIUM** — Memory exhaustion via large payloads |

### HIGH-002: No Input Validation on Web Chat

| Field | Value |
|-------|-------|
| **File** | `scripts/web/server.py:157` |
| **Location** | `POST /api/chat` endpoint |
| **Root Cause** | No rate limiting or input size validation on web chat endpoint |
| **Affected Files** | `scripts/web/server.py` |
| **Suggested Fix** | Add rate limiting + input size validation |
| **Risk Level** | **MEDIUM** — Denial of service |

### HIGH-003: MCP Server Subprocess Not Isolated

| Field | Value |
|-------|-------|
| **File** | `core/mcp/client.py:152` |
| **Location** | `MCPServerConnection.__init__()` |
| **Root Cause** | MCP servers spawn via `subprocess.Popen` with no sandbox or resource limits |
| **Affected Files** | `core/mcp/client.py`, any code using MCP tools |
| **Suggested Fix** | Run MCP servers in sandboxed subprocess with resource limits |
| **Risk Level** | **MEDIUM** — Unrestricted subprocess execution |

### HIGH-004: Skill Loader Executes Arbitrary Code

| Field | Value |
|-------|-------|
| **File** | `core/skills.py:58-73` |
| **Location** | `_load_skill_tools()` function |
| **Root Cause** | `importlib.util.exec_module()` runs Python from `skills/tools.py` without verification |
| **Affected Files** | `core/skills.py`, `core/plugin_loader.py` |
| **Suggested Fix** | Add hash verification, code signing, or at minimum a warning |
| **Risk Level** | **MEDIUM** — Supply chain attack vector |

### HIGH-005: Regex Bypass for Command Guard

| Field | Value |
|-------|-------|
| **File** | `core/tools/security.py` |
| **Location** | `_DANGEROUS_PATTERNS` regex list |
| **Root Cause** | Regex patterns can be bypassed with Unicode encoding, whitespace tricks, variable expansion, etc. |
| **Affected Files** | `core/tools/__init__.py:306-312` (calls `_scan_dangerous`) |
| **Suggested Fix** | Add multi-layer validation: regex + AST parsing + shell expansion simulation |
| **Risk Level** | **MEDIUM** — Bypassable security controls |

### HIGH-006: Docker Container Runs as Root

| Field | Value |
|-------|-------|
| **File** | `Dockerfile` |
| **Location** | Missing `USER` directive |
| **Root Cause** | No non-root user defined — all container processes run as root |
| **Affected Files** | `Dockerfile` |
| **Suggested Fix** | Add `RUN useradd -m widdx && USER widdx` before COPY |
| **Risk Level** | **LOW** — Container escape risk |

---

## 🟡 MEDIUM Issues

### MED-001: No CORS in Web Server

| Field | Value |
|-------|-------|
| **File** | `scripts/web/server.py` |
| **Location** | FastAPI app configuration |
| **Root Cause** | No CORS middleware — any origin can make requests |
| **Affected Files** | `scripts/web/server.py` |
| **Suggested Fix** | Add `CORSMiddleware` with localhost-only origins |
| **Risk Level** | **LOW** — Cross-origin request forgery |

### MED-002: No HTTPS Enforcement

| Field | Value |
|-------|-------|
| **File** | `scripts/api_server.py` |
| **Location** | `uvicorn.run()` call |
| **Root Cause** | HTTP only — no TLS configuration |
| **Affected Files** | `scripts/api_server.py`, `scripts/web/server.py` |
| **Suggested Fix** | Add SSL cert/key configuration options |
| **Risk Level** | **LOW** — Cleartext transmission |

### MED-003: SQLite Without WAL Mode

| Field | Value |
|-------|-------|
| **File** | `core/database.py` |
| **Location** | `_get_conn()` method |
| **Root Cause** | Default journal mode — concurrent writes may cause "database is locked" |
| **Affected Files** | `core/database.py`, all code using database |
| **Suggested Fix** | Set `PRAGMA journal_mode=WAL` on connection |
| **Risk Level** | **LOW** — Concurrency issues |

### MED-004: Hardcoded Windows Paths in Config

| Field | Value |
|-------|-------|
| **File** | `config.json` |
| **Location** | `mcp_servers` array |
| **Root Cause** | Absolute `E:/deepseek/chat-tool/` paths — breaks on other machines |
| **Affected Files** | `config.json` |
| **Suggested Fix** | Use relative paths or `{PROJECT_ROOT}` placeholder |
| **Risk Level** | **LOW** — Portability issue |

### MED-005: No Connection Pooling for SQLite

| Field | Value |
|-------|-------|
| **File** | `core/database.py:25` |
| **Location** | `_get_conn()` method |
| **Root Cause** | Creates new connection per operation — ~1ms overhead each |
| **Affected Files** | `core/database.py` |
| **Suggested Fix** | Use connection pooling or persistent connection |
| **Risk Level** | **LOW** — Performance overhead |

### MED-006: In-Memory Rate Limiter

| Field | Value |
|-------|-------|
| **File** | `scripts/api_server.py:58` |
| **Location** | `RateLimiter` class |
| **Root Cause** | Rate limit state lost on restart; not distributed |
| **Affected Files** | `scripts/api_server.py` |
| **Suggested Fix** | Use Redis or database-backed rate limiter for production |
| **Risk Level** | **LOW** — Rate limit bypass on restart |

### MED-007: Knowledge Save on Every Execution

| Field | Value |
|-------|-------|
| **File** | `core/uil/knowledge.py:100` |
| **Location** | `KnowledgeBase.record()` method |
| **Root Cause** | `_save()` writes entire JSON file after every execution — no batching |
| **Affected Files** | `core/uil/knowledge.py`, `core/uil/brain.py` (calls record) |
| **Suggested Fix** | Batch writes every N records or use timer-based flush |
| **Risk Level** | **LOW** — Performance overhead |

### MED-008: ExpertTeam Sequential Execution

| Field | Value |
|-------|-------|
| **File** | `core/agents/expert.py:248` |
| **Location** | `ExpertTeam.run()` method |
| **Root Cause** | Experts run one at a time with string concatenation — no parallelism |
| **Affected Files** | `core/agents/expert.py`, `core/agents/executor_adapter.py` |
| **Suggested Fix** | Use threading for independent expert tasks |
| **Risk Level** | **LOW** — Performance bottleneck |

### MED-009: Tool Cache Over-Invalidation

| Field | Value |
|-------|-------|
| **File** | `core/cache.py` |
| **Location** | `invalidate_on_write()` method |
| **Root Cause** | Clears ALL read caches on any write — overly aggressive |
| **Affected Files** | `core/cache.py`, `core/agents/agent.py` |
| **Suggested Fix** | Invalidation by file path pattern instead of full clear |
| **Risk Level** | **LOW** — Cache hit rate degradation |

### MED-010: LLM Classification on Every Message

| Field | Value |
|-------|-------|
| **File** | `core/uil/analyzer.py:100-160` |
| **Location** | `LLMClassifier.classify()` method |
| **Root Cause** | Every message triggers LLM call for classification (500-2000ms overhead) |
| **Affected Files** | `core/uil/brain.py` (calls analyzer.analyze) |
| **Suggested Fix** | Use local classifier as primary; LLM as fallback for ambiguous cases |
| **Risk Level** | **LOW** — Latency overhead |

---

## 🟢 LOW Issues

### LOW-001: No Content-Security-Policy Headers

| Field | Value |
|-------|-------|
| **File** | `scripts/web/server.py` |
| **Root Cause** | Web UI served without CSP headers |
| **Suggested Fix** | Add `Content-Security-Policy` header |
| **Risk Level** | **INFO** — XSS risk in web UI |

### LOW-002: Logger May Leak Sensitive Data

| Field | Value |
|-------|-------|
| **File** | Various (`core/mcp/client.py`, `core/providers/*.py`) |
| **Root Cause** | API keys, tokens may appear in DEBUG log output |
| **Suggested Fix** | Sanitize log output; mask sensitive values |
| **Risk Level** | **INFO** — Information disclosure |

### LOW-003: WSL Fallback is Silent

| Field | Value |
|-------|-------|
| **File** | `core/sandbox.py:329` |
| **Root Cause** | Falls back from WSL to subprocess without user notification |
| **Suggested Fix** | Log warning visible to user |
| **Risk Level** | **INFO** — User unaware of reduced isolation |

### LOW-004: No Content-Length on Web Responses

| Field | Value |
|-------|-------|
| **File** | `scripts/web/server.py` |
| **Root Cause** | Large responses may not have proper Content-Length |
| **Suggested Fix** | Ensure all responses have proper headers |
| **Risk Level** | **INFO** — Minor HTTP compliance |

### LOW-005: SQLite Without Foreign Keys Enforcement

| Field | Value |
|-------|-------|
| **File** | `core/database.py` |
| **Root Cause** | SQLite disables foreign keys by default; no `PRAGMA foreign_keys = ON` |
| **Suggested Fix** | Enable foreign key enforcement on connection |
| **Risk Level** | **INFO** — Data integrity |

### LOW-006: API Key Auto-Generated Without Notification

| Field | Value |
|-------|-------|
| **File** | `scripts/api_server.py:40-43` |
| **Root Cause** | Generates ephemeral API key without clear user notification |
| **Suggested Fix** | Add clear console output with instructions |
| **Risk Level** | **INFO** — User confusion |

### LOW-007: __import__ Anti-Pattern in Providers

| Field | Value |
|-------|-------|
| **File** | `core/providers/base.py:16` and 7 other provider files |
| **Root Cause** | `logger = __import__("logging").getLogger(...)` — hides imports from static analysis |
| **Suggested Fix** | Replace with standard `import logging` at top of file |
| **Risk Level** | **INFO** — Code quality |

### LOW-008: `except: pass` Blocks Removed But Pattern Still Found

| Field | Value |
|-------|-------|
| **File** | `core/diagnostics.py:167-169` |
| **Root Cause** | Diagnostics module detects bare except patterns but the module itself is diagnostic-only |
| **Suggested Fix** | No action needed — diagnostic module is working correctly |
| **Risk Level** | **INFO** — False positive in analysis |

### LOW-009: No Timeout on SQLite Operations

| Field | Value |
|-------|-------|
| **File** | `core/database.py` |
| **Root Cause** | No timeout specified on `sqlite3.connect()` — could hang on lock |
| **Suggested Fix** | Add `timeout=5` to `sqlite3.connect()` |
| **Risk Level** | **INFO** — Potential hang |

### LOW-010: ProjectScanner Not Cached

| Field | Value |
|-------|-------|
| **File** | `core/project/scanner.py` |
| **Root Cause** | Full directory scan on every instantiation — no caching |
| **Suggested Fix** | Cache scan results with TTL |
| **Risk Level** | **INFO** — Startup latency |

---

## ⚪ INFO Observations

### INFO-001: Dual Session Systems

| Field | Value |
|-------|-------|
| **Observation** | Both `Database` class and `SessionV2` exist; `SessionDB` wraps `SessionV2` |
| **Status** | Backward compatibility layer — working as intended |

### INFO-002: Feature-Flagged Intelligence Engine

| Field | Value |
|-------|-------|
| **Observation** | `core/intelligence/` and `core/validation/` are v4 engine features, gated behind `engine_enabled()` |
| **Status** | Safe by default — only activates with explicit config flag |

### INFO-003: Dead Module Cleanup

| Field | Value |
|-------|-------|
| **Observation** | `auto_commit.py`, `project_context.py`, `project_structure.py` are dead code |
| **Status** | Safe to remove — only referenced in tests |

### INFO-004: Skill Tool Loading Security

| Field | Value |
|-------|-------|
| **Observation** | `_load_skill_tools()` uses `exec_module()` — potential security concern |
| **Status** | Mitigated by skills being local files (not remote) |

---

## Summary

| Severity | Count | Critical Path |
|----------|-------|---------------|
| 🔴 CRITICAL | 3 | Security (shell injection, webhook) |
| 🟠 HIGH | 6 | Security + Input validation |
| 🟡 MEDIUM | 10 | Performance + Concurrency |
| 🟢 LOW | 10 | Code quality + Compliance |
| ⚪ INFO | 4 | Architecture observations |
| **Total** | **33** | |

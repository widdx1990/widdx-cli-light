# WIDDX Nexus — Fix Plan

> Prioritized remediation plan for all detected issues, organized by urgency and effort.

## Priority Matrix

```
                    LOW EFFORT          HIGH EFFORT
                 ┌──────────────────┬──────────────────┐
   HIGH IMPACT   │ 🔥 P1: Quick     │ 🟠 P2: Strategic  │
                 │    Wins          │    Fixes          │
                 ├──────────────────┼──────────────────┤
   LOW IMPACT    │ 🟢 P3: Cleanup   │ ⚪ P4: Backlog    │
                 │    & Polish      │                   │
                 └──────────────────┴──────────────────┘
```

---

## 🔥 P1: Quick Wins (1-3 days, high impact) — 6/6 COMPLETE as of 2026-06-25

### P1-1: Fix shell=True Fallback [CRITICAL] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | CRIT-001, CRIT-003 |
| **Files** | `core/sandbox.py:637-641`, `scripts/web/sandbox.py:65` |
| **Effort** | 2 hours |
| **Fix** | Replace `shell=True` fallback with `shlex.split()` + explicit shell wrapper |
| **Verification** | Run `test_sandbox.py` + manual injection test |

```python
# In _execute_subprocess():
cmd, needs_shell = self._split_command(command)
if needs_shell:
    # Explicitly wrap in shell — logged and auditable
    logger.info("shell=True for: %.100s", command)
    proc = subprocess.Popen(
        ["bash", "-c", command],  # Explicit shell, not shell=True
        ...
    )
```

### P1-2: Fix GitHub Webhook Security [CRITICAL] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | CRIT-002 |
| **Files** | `github-app/app.py:43` |
| **Effort** | 1 hour |
| **Fix** | Make `WEBHOOK_SECRET` required; reject when empty |
| **Verification** | Test with empty/missing secret |

### P1-3: Add Request Size Limits [HIGH] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | HIGH-001, HIGH-002 |
| **Files** | `scripts/api_server.py:118`, `scripts/web/server.py` |
| **Effort** | 30 minutes |
| **Fix** | Add `Field(max_length=100000)` to `ChatRequest.message` |
| **Verification** | Test with oversized payload |

### P1-4: Add CORS to Web Server [MEDIUM] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | MED-001 |
| **Files** | `scripts/web/server.py` |
| **Effort** | 30 minutes |
| **Fix** | Add `CORSMiddleware` with localhost-only origins |
| **Verification** | Test cross-origin request from different port |

### P1-5: Enable SQLite WAL Mode [MEDIUM] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | MED-003 |
| **Files** | `core/database.py:25` |
| **Effort** | 15 minutes |
| **Fix** | Add `PRAGMA journal_mode=WAL` after connection |
| **Verification** | Check WAL file created |

### P1-6: Fix Hardcoded Paths in Config [MEDIUM] ✅ DONE

| Field | Value |
|-------|-------|
| **Issue** | MED-004 |
| **Files** | `config.json` |
| **Effort** | 15 minutes |
| **Fix** | Replace `E:/deepseek/chat-tool/` with `{PROJECT_ROOT}` placeholder |
| **Verification** | Verify config loads on different machine |

---

## 🟠 P2: Strategic Fixes (1-2 weeks, high impact)

### P2-1: Sandbox MCP Servers [HIGH]

| Field | Value |
|-------|-------|
| **Issue** | HIGH-003 |
| **Files** | `core/mcp/client.py:152` |
| **Effort** | 1 day |
| **Fix** | Run MCP servers in `SandboxExecutor` with resource limits |
| **Verification** | Test MCP server startup/shutdown |

### P2-2: Skill Code Signing [HIGH]

| Field | Value |
|-------|-------|
| **Issue** | HIGH-004 |
| **Files** | `core/skills.py:58-73` |
| **Effort** | 2 days |
| **Fix** | Add hash verification for skill Python files |
| **Verification** | Test with modified skill file |

### P2-3: Improve Command Guard [HIGH]

| Field | Value |
|-------|-------|
| **Issue** | HIGH-005 |
| **Files** | `core/tools/security.py` |
| **Effort** | 1 day |
| **Fix** | Add shell expansion simulation + Unicode normalization |
| **Verification** | Test bypass techniques |

### P2-4: Parallel ExpertTeam [MEDIUM]

| Field | Value |
|-------|-------|
| **Issue** | MED-008 |
| **Files** | `core/agents/expert.py:248` |
| **Effort** | 2 days |
| **Fix** | Use `threading` for independent expert tasks |
| **Verification** | Benchmark complex task execution time |

### P2-5: Batch Knowledge Saves [MEDIUM]

| Field | Value |
|-------|-------|
| **Issue** | MED-007 |
| **Files** | `core/uil/knowledge.py:100` |
| **Effort** | 4 hours |
| **Fix** | Add dirty flag + timer-based flush (every 5 records or 30 seconds) |
| **Verification** | Monitor disk I/O during rapid execution |

### P2-6: Local Classifier as Primary [MEDIUM]

| Field | Value |
|-------|-------|
| **Issue** | MED-010 |
| **Files** | `core/uil/analyzer.py` |
| **Effort** | 3 days |
| **Fix** | Make `LocalClassifier` primary; LLM as fallback for ambiguous cases |
| **Verification** | Benchmark classification accuracy + latency |

### P2-7: Add Docker Non-Root User [LOW]

| Field | Value |
|-------|-------|
| **Issue** | HIGH-006 |
| **Files** | `Dockerfile` |
| **Effort** | 30 minutes |
| **Fix** | Add `RUN useradd -m widdx && USER widdx` |
| **Verification** | Build and run Docker image |

### P2-8: Add HTTPS Support [MEDIUM]

| Field | Value |
|-------|-------|
| **Issue** | MED-002 |
| **Files** | `scripts/api_server.py`, `scripts/web/server.py` |
| **Effort** | 1 day |
| **Fix** | Add SSL cert/key configuration options |
| **Verification** | Test with self-signed certificate |

---

## 🟢 P3: Cleanup & Polish (1 week, low impact)

### P3-1: Remove Dead Code

| Field | Value |
|-------|-------|
| **Issues** | DEAD-001 through DEAD-008 |
| **Files** | `core/auto_commit.py`, `core/project_context.py`, `core/project_structure.py`, `core/self_reflection.py`, `core/web_launcher.py`, `_debug_brain.py`, `_run_tests.py` |
| **Effort** | 2 hours |
| **Fix** | Delete dead modules + update imports |
| **Verification** | Run full test suite |

### P3-2: Fix __import__ Anti-Pattern

| Field | Value |
|-------|-------|
| **Issue** | LOW-007 |
| **Files** | 9 provider files in `core/providers/` |
| **Effort** | 30 minutes |
| **Fix** | Replace `__import__("logging")` with standard import |
| **Verification** | Run `test_providers.py` |

### P3-3: Add CSP Headers to Web UI

| Field | Value |
|-------|-------|
| **Issue** | LOW-001 |
| **Files** | `scripts/web/server.py` |
| **Effort** | 30 minutes |
| **Fix** | Add `Content-Security-Policy` header middleware |
| **Verification** | Check browser console for CSP violations |

### P3-4: Sanitize Log Output

| Field | Value |
|-------|-------|
| **Issue** | LOW-002 |
| **Files** | Various `core/` modules |
| **Effort** | 2 hours |
| **Fix** | Create `mask_secret()` helper; apply to all log calls |
| **Verification** | Grep logs for API keys |

### P3-5: Enable SQLite Foreign Keys

| Field | Value |
|-------|-------|
| **Issue** | LOW-005 |
| **Files** | `core/database.py` |
| **Effort** | 15 minutes |
| **Fix** | Add `PRAGMA foreign_keys = ON` after connection |
| **Verification** | Run database tests |

### P3-6: Add SQLite Connection Timeout

| Field | Value |
|-------|-------|
| **Issue** | LOW-009 |
| **Files** | `core/database.py:25` |
| **Effort** | 5 minutes |
| **Fix** | Add `timeout=5` to `sqlite3.connect()` |
| **Verification** | Run database tests |

### P3-7: Cache Project Scan Results

| Field | Value |
|-------|-------|
| **Issue** | LOW-010 |
| **Files** | `core/project/scanner.py` |
| **Effort** | 2 hours |
| **Fix** | Add mtime-based cache with 5-minute TTL |
| **Verification** | Benchmark startup time |

### P3-8: Tool Cache Path-Based Invalidation

| Field | Value |
|-------|-------|
| **Issue** | MED-009 |
| **Files** | `core/cache.py` |
| **Effort** | 4 hours |
| **Fix** | Track file paths in cache keys; invalidate by path pattern |
| **Verification** | Measure cache hit rate during editing session |

---

## ⚪ P4: Backlog (when time permits)

| # | Issue | Effort | Notes |
|---|-------|--------|-------|
| P4-1 | Redis-backed rate limiter | 2 days | Only needed for multi-instance deployment |
| P4-2 | Connection pooling for SQLite | 1 day | Current performance is acceptable |
| P4-3 | Async execution throughout | 2 weeks | Major refactor, high risk |
| P4-4 | Vector-based semantic memory | 1 week | Replace TF-IDF with proper embeddings |
| P4-5 | WebSocket streaming for all interfaces | 1 week | Already partially implemented |
| P4-6 | Precompiled skill modules | 4 hours | Eliminate exec_module overhead |
| P4-7 | DOM-based HTML verification | 2 days | Replace regex with BeautifulSoup |

---

## Implementation Roadmap

```
Week 1:  P1-1 to P1-6 (Quick Wins — security + portability)
Week 2:  P2-1 to P2-3 (Security hardening)
Week 3:  P2-4 to P2-6 (Performance + Architecture)
Week 4:  P2-7 to P2-8 + P3-1 to P3-4 (Cleanup + Polish)
Week 5+: P3-5 to P3-8 + P4 items (Backlog)
```

## Estimated Total Effort

| Priority | Issues | Effort |
|----------|--------|--------|
| P1 (Quick Wins) | 6 | ~1 day |
| P2 (Strategic) | 8 | ~10 days |
| P3 (Cleanup) | 8 | ~3 days |
| P4 (Backlog) | 7 | ~5 weeks |
| **Total** | **29** | **~7 weeks** |

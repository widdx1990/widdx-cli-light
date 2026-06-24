# WIDDX Nexus — Performance Analysis

> Performance characteristics, bottlenecks, resource usage patterns, and optimization opportunities.

## Execution Time Profiles

### UIL Pipeline Latency (per message)

| Stage | Typical Time | Bottleneck? | Notes |
|-------|-------------|-------------|-------|
| Analyze (LLM classify) | 500-2000ms | ✅ YES | LLM call for classification |
| Analyze (keyword fallback) | <1ms | No | Fast path when LLM unavailable |
| Route | <1ms | No | Deterministic dict lookup |
| Plan | <1ms | No | Rule-based decomposition |
| Execute (SIMPLE_CHAT) | 1000-5000ms | ✅ YES | LLM call for response |
| Execute (AUTONOMOUS) | 5000-60000ms | ✅ YES | Multiple LLM + tool cycles |
| Execute (EXPERT_TEAM) | 15000-120000ms | ✅ YES | Sequential expert pipeline |
| Verify | <50ms | No | Regex-based checks |
| Knowledge (save) | 5-20ms | No | JSON file write |
| **Total (SIMPLE_CHAT)** | **1.5-7s** | | |
| **Total (AUTONOMOUS)** | **6-65s** | | |

### Provider Response Times (measured)

| Provider | First Token | Full Response | Streaming |
|----------|-------------|---------------|-----------|
| DeepSeek API | 200-800ms | 1-5s | ✅ Yes |
| OpenCode Zen | 100-500ms | 1-3s | ✅ Yes |
| Ollama (local) | 50-200ms | 2-30s | ✅ Yes |
| GGUF (llama-cpp) | 10-100ms | 2-60s | ✅ Yes |

## Memory Usage

### Process Memory

| Component | Memory | Notes |
|-----------|--------|-------|
| Python base | ~30MB | CPython 3.12 |
| Rich/Terminal | ~5MB | Rich console rendering |
| Textual TUI | ~15MB | Textual framework overhead |
| MCP clients | ~10-50MB | Per server subprocess |
| Cache stores | ~5-20MB | Depends on cache size |
| **Typical total** | **65-120MB** | |

### SQLite Database Growth

| Data Type | Growth Rate | Cleanup? |
|-----------|-------------|----------|
| Messages | ~200 bytes/msg | No auto-cleanup |
| Sessions | ~200 bytes/session | Manual delete only |
| Memories | ~500 bytes/fact | Manual delete only |
| Provider stats | ~100 bytes/model | No cleanup |

### File System Growth

| Data | Location | Growth | Cleanup |
|------|----------|--------|---------|
| Knowledge JSON | `.widdx/knowledge.json` | Grows with executions | Manual |
| Workspaces | `~/.widdx/workspaces/` | ~10MB/session | Auto after 24h |
| Skills cache | `~/.widdx/skills/` | Minimal | Manual |
| Memory files | `.widdx/memory/*.md` | ~1KB/file | Manual |
| Activity log | In-memory only | Fixed | On restart |

## Performance Bottlenecks

### 🔴 Critical

1. **LLM classification on every message** (`analyzer.py`)
   - Every user message triggers an LLM call just to classify intent
   - Cache exists (60s TTL) but cache key is hash of input — same semantic request with different wording = cache miss
   - **Impact:** 500-2000ms added latency per message
   - **Fix:** Batch classification or use local classifier as primary

2. **Sequential ExpertTeam execution** (`expert.py`)
   - Experts run one at a time, string concatenating results
   - No parallelism even for independent experts
   - **Impact:** 3-5x longer than necessary for complex tasks
   - **Fix:** Use threading for independent expert tasks

3. **Knowledge save on every execution** (`knowledge.py`)
   - `_save()` writes entire JSON file after every single execution
   - No batching or debouncing
   - **Impact:** Disk I/O on every message, JSON re-serialization
   - **Fix:** Batch writes every N records or use timer-based flush

### 🟠 High

4. **MCP server startup latency** (`mcp/client.py`)
   - Each MCP server starts a subprocess on app launch
   - Sequential startup (one at a time)
   - **Impact:** 2-5 seconds added to startup time
   - **Fix:** Parallel subprocess startup

5. **ProjectScanner on every session load** (`project/scanner.py`)
   - Scans entire project directory tree on startup
   - No caching of scan results
   - **Impact:** 100-500ms on startup for large projects
   - **Fix:** Cache scan results, incremental updates

6. **Tool result caching is read-only** (`cache.py`)
   - `invalidate_on_write()` clears ALL read caches on any write
   - Overly aggressive — writing `foo.py` invalidates caches for `bar.py`
   - **Impact:** Cache hit rate drops on active editing sessions
   - **Fix:** Invalidation by file path pattern

### 🟡 Medium

7. **No connection pooling for SQLite** (`database.py`)
   - Creates new connection per operation via `_get_conn()`
   - SQLite has connection overhead
   - **Impact:** ~1ms per DB operation (acceptable for now)
   - **Fix:** Use connection pool or persistent connection

8. **Regex-based verification** (`verifier.py`)
   - HTML/CSS/JS verification uses regex instead of DOM parsing
   - Can produce false positives/negatives
   - **Impact:** Incorrect verification results
   - **Fix:** Use proper HTML parser (BeautifulSoup/lxml)

9. **Skill tool loading on every activation** (`skills.py`)
   - `_load_skill_tools()` calls `exec_module()` each time
   - No caching of compiled modules
   - **Impact:** 10-50ms per skill activation
   - **Fix:** Cache compiled modules by path + mtime

## Optimization Opportunities

### Quick Wins (< 1 day)

| Optimization | Expected Impact | Effort |
|-------------|-----------------|--------|
| Cache LLM classification by semantic hash | 30-50% latency reduction | Low |
| Batch knowledge saves (every 5 records) | Reduce disk I/O 80% | Low |
| Parallel MCP server startup | 2-5s faster startup | Low |
| Cache project scan results | 100-500ms startup savings | Low |
| Add `max_body_size` to FastAPI | Prevent memory exhaustion | Low |

### Medium Effort (1-3 days)

| Optimization | Expected Impact | Effort |
|-------------|-----------------|--------|
| Parallel ExpertTeam execution | 2-3x faster complex tasks | Medium |
| Use local classifier as primary (LLM as fallback) | 500ms per message saved | Medium |
| Connection pooling for SQLite | Consistent DB performance | Medium |
| Semantic deduplication for tool caching | Better cache hit rate | Medium |

### Major Refactors (1+ weeks)

| Optimization | Expected Impact | Effort |
|-------------|-----------------|--------|
| Async execution throughout (asyncio) | Non-blocking I/O | High |
| WebSocket streaming for all interfaces | Real-time UX | High |
| Vector-based semantic memory search (replace TF-IDF) | Better memory recall | High |
| Precompiled skill modules | Eliminate exec_module overhead | Medium |

## Scalability Limits

| Resource | Current Limit | Bottleneck |
|----------|---------------|-----------|
| Concurrent users | 1 (CLI/TUI) | Session state is in-memory |
| API concurrent requests | ~10 | Single-threaded FastAPI workers |
| Messages per session | ~10,000 | SQLite performance degrades |
| MCP servers | ~6 | Process overhead |
| Background tasks | ~50 | Thread limit, memory |
| Memory facts | ~1,000 | Linear search + TF-IDF index rebuild |

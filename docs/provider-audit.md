# WIDDX Provider Layer — Complete Audit

> التاريخ: 2026-06-27 | الحالة: Honest Assessment

---

## 1. Provider Abstraction

**Interface:** `core/providers/base.py` — `Provider` ABC with one abstract method: `chat()`.
`stream()` is optional with default implementation that falls back to `chat()`.

**Concrete providers (7):**
| Provider | File | Tool Support | Auth |
|----------|------|-------------|------|
| OpenCodeZen | `opencode_zen.py` | ✅ | Public (free) |
| DeepSeek | `deepseek.py` | ✅ | API Key |
| OpenAI Comp. | `openai_compatible.py` | ✅ | API Key |
| Ollama | `ollama.py` | ✅ | None (local) |
| GGUF Direct | `gguf_provider.py` | ❌ | None |
| GGUF Legacy | `gguf.py` | ❌ | None |
| Free Models | `free_models.py` | ❌ | None |

**Verdict:** ⚠️ Single `chat()` method. No `chat_with_tools()`, no `stream_with_tools()`. Each provider implements tool calling differently — no unified protocol.

---

## 2. Failover

**Current:** ❌ **No automatic failover exists.**

`create_provider(cfg)` creates ONE provider from config. If it fails, returns error.
No fallback chain, no retry with alternate provider.

The only fallback: `_get_fallback_model()` for model name resolution — picks a default model if none specified. Not a provider failover.

---

## 3. Checkpoint / Resume

**Current:** ❌ **No checkpoint/resume on provider failure.**

`AutonomousAgent` loop runs in-memory. If provider fails:
- Error returned to UI
- Agent stops
- State is NOT saved mid-execution
- Next run starts fresh

`TaskState` (Level 5.1) persists goal and steps, but `AutonomyLoop` doesn't use it to resume.

---

## 4. Provider Differences Normalization

**Current:** ❌ **Minimal. Each provider handles its own differences.**

| Capability | Normalization |
|-----------|---------------|
| Tool calling | Each provider has own format (DeepSeek sends in system prompt, OpenAI uses native) |
| Context limits | Hardcoded per provider in `_DEFAULT_MAX_TOKENS` |
| Reasoning tags | `[thinking]...[/thinking]` stripped in `base.py:_clean_surrogates()` |
| Response format | Each provider parses own response format |
| Streaming | `stream()` optional, each provider implements differently |

---

## 5. Model Selection

**Current:** Static. User picks provider + model in Settings.

`resolve_model()` in `factory.py` can discover available models for Ollama/GGUF.
No dynamic selection based on: task complexity, cost, latency, capabilities.
No "smart routing" — e.g., simple chat → cheap model, complex code → powerful model.

---

## 6. Retry Strategy

**Current:** ⚠️ Limited.

| Error Type | Handled? | Where |
|-----------|----------|-------|
| Timeout | ✅ | `AutonomousAgent` loop breaks on exception |
| 401 Auth | ❌ | Error returned to UI, retry would fail anyway |
| Rate limit (429) | ❌ | No backoff, no retry-after parsing |
| Network error | ❌ | Exception bubbles up to caller |
| Empty response | ⚠️ | Agent logs warning, continues |
| Invalid JSON | ❌ | Provider raises exception |

`Provider` base class has NO retry logic. Agent loop catches `Exception` but doesn't retry with backoff.

---

## 7. Context Window Management

**Current:** ⚠️ Basic.

- `_DEFAULT_MAX_TOKENS` per provider (hardcoded)
- `SessionV2.get_context()` trims messages by character count (max_tokens * 4)
- No dynamic resizing when switching providers with different context windows
- No token counting (uses char count approximation)

---

## 8. Stress Tests

**Current:** ❌ None.

`tests/test_providers.py` tests factory creation and model listing. No tests for:
- Provider failure during autonomous task
- Network interruption mid-execution
- Rate limit handling
- 24h+ autonomous runs
- Multi-provider switching

---

## Summary

| Capability | Status | Priority |
|-----------|--------|----------|
| Unified interface | ⚠️ Basic ABC | - |
| Auto-failover | ❌ None | P0 |
| Checkpoint/resume | ❌ None | P0 |
| Provider normalization | ❌ Minimal | P1 |
| Dynamic model selection | ❌ Static | P2 |
| Retry with backoff | ❌ None | P0 |
| Context window adaptation | ⚠️ Basic | P1 |
| Stress tests | ❌ None | P1 |

---

## Roadmap to Production-Grade Provider Layer

### P0 — Critical for Autonomy

1. **Provider Pool with Failover:**
```python
providers = [deepseek, opencode_zen, ollama]  # ordered by preference
for p in providers:
    try:
        result = p.chat(messages, tools)
        break
    except (Timeout, RateLimit, NetworkError):
        continue  # try next provider
```

2. **Retry with Exponential Backoff:**
```python
for attempt in range(3):
    try:
        return provider.chat(...)
    except RateLimitError:
        time.sleep(2 ** attempt)
    except NetworkError:
        time.sleep(1)
```

3. **Checkpoint on Provider Failure:**
```python
try:
    result = agent.run(task)
except ProviderError:
    TaskState.save_checkpoint(agent.steps, agent.messages)
    raise  # will resume from here next run
```

### P1 — Quality

4. **Unified Tool Calling Protocol** — normalize DeepSeek/OpenAI/Ollama tool formats in base class
5. **Dynamic Context Window** — per-provider token limits, auto-truncate messages
6. **Stress Tests** — simulate failures, verify system recovers

### P2 — Optimization

7. **Smart Model Router** — route based on task complexity (simple→cheap, complex→powerful)
8. **Cost Tracking** — per-provider cost accounting

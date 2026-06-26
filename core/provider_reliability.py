"""Provider Reliability Layer — Production-grade execution backbone.

Implements:
  1. Provider Pool with automatic failover
  2. Retry with exponential backoff
  3. Checkpoint on failure for task resume
  4. Unified tool calling across all providers
  5. Failures trigger recovery, not termination

Usage:
    from core.provider_reliability import ReliableProvider
    rp = ReliableProvider()
    result = rp.chat_with_retry(messages, tools, task_state=ts)
"""

from __future__ import annotations

import logging
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("widdx.reliability")


# ═══════════════════════════════════════════════════════════════
# Reliability Result
# ═══════════════════════════════════════════════════════════════

@dataclass
class ReliabilityResult:
    content: str = ""
    tool_calls: list = field(default_factory=list)
    provider_used: str = ""
    attempts: int = 0
    total_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    recovered: bool = False


# ═══════════════════════════════════════════════════════════════
# Provider Pool
# ═══════════════════════════════════════════════════════════════

class ProviderPool:
    """Manages multiple providers with priority-based failover."""

    def __init__(self):
        self._providers: list[dict] = []
        self._health: dict[str, dict] = {}  # name → {failures, last_fail, cooldown_until}
        self._init_pool()

    def _init_pool(self):
        """Initialize the provider pool from config."""
        try:
            from core.config.settings import load as load_cfg
            cfg = load_cfg()
            from core.providers.factory import create_provider

            # Primary provider from config
            try:
                primary = create_provider(cfg)
                self._providers.append({"provider": primary, "priority": 1, "name": primary.name})
            except Exception as e:
                logger.warning("Primary provider unavailable: %s", e)

            # Fallback providers
            fallbacks = [
                ("opencode-zen", "deepseek-v4-flash-free"),
                ("ollama", "deepseek-v4-flash-free"),
            ]
            for name, model in fallbacks:
                if name not in [p["name"] for p in self._providers]:
                    try:
                        fb_cfg = dict(cfg)
                        fb_cfg["provider"] = {"name": name, "model": model}
                        fb = create_provider(fb_cfg)
                        self._providers.append({"provider": fb, "priority": len(self._providers) + 1, "name": name})
                    except Exception:
                        pass

            logger.info("ProviderPool: %d providers available", len(self._providers))
        except Exception as e:
            logger.error("ProviderPool init failed: %s", e)

    def get_provider(self, skip_unhealthy: bool = True) -> Any | None:
        """Get the best available provider, skipping unhealthy ones."""
        now = time.time()
        for entry in sorted(self._providers, key=lambda x: x["priority"]):
            name = entry["name"]
            health = self._health.get(name, {})
            if skip_unhealthy and health.get("cooldown_until", 0) > now:
                logger.debug("Provider %s in cooldown until %s", name, health.get("cooldown_until"))
                continue
            return entry["provider"]
        return None

    def mark_failure(self, name: str, error: str):
        """Mark a provider as failed, putting it in cooldown."""
        now = time.time()
        if name not in self._health:
            self._health[name] = {"failures": 0, "last_fail": 0, "cooldown_until": 0}
        h = self._health[name]
        h["failures"] += 1
        h["last_fail"] = now
        # Exponential cooldown: 2s, 4s, 8s, 16s, max 60s
        cooldown = min(2 ** h["failures"], 60)
        h["cooldown_until"] = now + cooldown
        logger.warning("Provider %s failed (x%d), cooldown %ds: %s", name, h["failures"], cooldown, error[:100])

    def mark_success(self, name: str):
        """Reset failure count on success."""
        if name in self._health:
            self._health[name]["failures"] = 0
            self._health[name]["cooldown_until"] = 0

    @property
    def available_count(self) -> int:
        return len([p for p in self._providers if self._health.get(p["name"], {}).get("cooldown_until", 0) <= time.time()])

    @property
    def total_count(self) -> int:
        return len(self._providers)


# ═══════════════════════════════════════════════════════════════
# Unified Tool Protocol
# ═══════════════════════════════════════════════════════════════

class UnifiedToolCall:
    """Normalized tool call across all providers."""

    def __init__(self, name: str, arguments: dict, call_id: str = ""):
        self.id = call_id or f"call_{name}_{id(arguments)}"
        self.name = name
        self.arguments = arguments

    @staticmethod
    def from_provider(provider_name: str, raw_call: Any) -> "UnifiedToolCall":
        """Parse a provider-specific tool call into unified format."""
        if isinstance(raw_call, UnifiedToolCall):
            return raw_call
        if isinstance(raw_call, dict):
            fn = raw_call.get("function", raw_call)
            return UnifiedToolCall(
                name=fn.get("name", ""),
                arguments=fn.get("arguments", {}) if isinstance(fn.get("arguments"), dict) else json.loads(fn.get("arguments", "{}")),
                call_id=raw_call.get("id", ""),
            )
        if hasattr(raw_call, "name") and hasattr(raw_call, "args"):
            return UnifiedToolCall(name=raw_call.name, arguments=raw_call.args or {}, call_id=getattr(raw_call, "id", ""))
        return UnifiedToolCall(name="unknown", arguments={})

    def to_openai_format(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments, ensure_ascii=False)},
        }

    def to_dict(self) -> dict:
        return {"name": self.name, "args": self.arguments, "id": self.id}


def normalize_tool_result(raw_result: str, provider_name: str) -> str:
    """Normalize tool execution results across providers."""
    if not raw_result:
        return ""
    # DeepSeek sometimes wraps results in extra formatting
    if provider_name in ("deepseek", "opencode-zen"):
        # Strip thinking tags
        import re
        raw_result = re.sub(r'\[thinking\].*?\[/thinking\]', '', raw_result, flags=re.DOTALL)
    return raw_result.strip()


# ═══════════════════════════════════════════════════════════════
# Checkpoint Manager
# ═══════════════════════════════════════════════════════════════

class CheckpointManager:
    """Saves agent state on provider failure for later resume."""

    def __init__(self):
        self._dir = Path.cwd() / ".widdx" / "checkpoints"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_id: str, steps: list, messages: list, goal: str):
        """Save current execution state."""
        data = {
            "task_id": task_id,
            "goal": goal,
            "steps": [s.to_dict() for s in steps],
            "messages": messages[-20:],  # last 20 messages
            "timestamp": time.time(),
        }
        fpath = self._dir / f"{task_id}.json"
        fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("Checkpoint saved: %d steps, %d messages → %s", len(steps), len(messages), fpath.name)

    def load(self, task_id: str) -> dict | None:
        """Load a saved checkpoint."""
        fpath = self._dir / f"{task_id}.json"
        if fpath.exists():
            return json.loads(fpath.read_text())
        return None

    def clear(self, task_id: str):
        (self._dir / f"{task_id}.json").unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
# Reliable Provider — Main API
# ═══════════════════════════════════════════════════════════════

class ReliableProvider:
    """Production-grade provider with pool, retry, backoff, and checkpointing."""

    def __init__(self):
        self._pool = ProviderPool()
        self._checkpoint = CheckpointManager()
        self._max_retries = 3
        self._base_delay = 1.0

    def chat_with_retry(
        self,
        messages: list[dict],
        tool_defs: list[dict] | None = None,
        task_state: Any = None,
        task_id: str = "",
    ) -> ReliabilityResult:
        """Call provider with full reliability: failover + retry + checkpoint.

        Args:
            messages: Chat messages.
            tool_defs: Tool definitions (unified format).
            task_state: TaskState for checkpoint save on failure.
            task_id: Unique task identifier for checkpoint.

        Returns:
            ReliabilityResult with content, tool_calls, and metadata.
        """
        t0 = time.perf_counter()
        result = ReliabilityResult()

        for attempt in range(self._max_retries):
            provider = self._pool.get_provider()
            if provider is None:
                # All providers in cooldown — wait and retry
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning("All providers in cooldown, retrying in %.1fs", delay)
                    time.sleep(delay)
                    continue
                result.errors.append("All providers unavailable")
                break

            try:
                content, tool_calls = self._call_provider(provider, messages, tool_defs)
                result.content = content or ""
                result.tool_calls = [UnifiedToolCall.from_provider(provider.name, tc).to_dict() for tc in (tool_calls or [])]
                result.provider_used = provider.name
                result.attempts = attempt + 1
                result.recovered = attempt > 0
                self._pool.mark_success(provider.name)
                break

            except RateLimitError:
                delay = self._base_delay * (2 ** attempt)
                logger.warning("Rate limited by %s, retry in %.1fs (attempt %d/%d)", provider.name, delay, attempt + 1, self._max_retries)
                self._pool.mark_failure(provider.name, "rate_limit")
                if task_state and task_id:
                    self._checkpoint.save(task_id, [], messages, "")
                time.sleep(delay)

            except (TimeoutError, ConnectionError, OSError) as e:
                logger.warning("Network error with %s: %s", provider.name, e)
                self._pool.mark_failure(provider.name, str(e)[:100])
                if task_state and task_id:
                    self._checkpoint.save(task_id, [], messages, "")
                if attempt < self._max_retries - 1:
                    time.sleep(self._base_delay)

            except ProviderAuthError:
                # Auth errors are permanent — don't retry this provider
                logger.error("Auth error with %s — disabling", provider.name)
                self._pool.mark_failure(provider.name, "auth_error")
                # Force long cooldown
                self._pool._health[provider.name]["cooldown_until"] = time.time() + 3600

            except Exception as e:
                logger.error("Unexpected error with %s: %s", provider.name, e)
                self._pool.mark_failure(provider.name, str(e)[:100])
                if task_state and task_id:
                    self._checkpoint.save(task_id, [], messages, "")

        result.total_time = round(time.perf_counter() - t0, 3)
        return result

    def _call_provider(self, provider, messages, tool_defs):
        """Call a provider, normalizing input/output."""
        # Try streaming first, fall back to chat
        if hasattr(provider, "stream") and callable(provider.stream):
            try:
                content_parts = []
                tool_calls = []
                for chunk in provider.stream(messages, tool_defs or []):
                    if isinstance(chunk, dict):
                        if chunk.get("type") == "content" or chunk.get("type") == "text":
                            content_parts.append(chunk.get("data", ""))
                        elif chunk.get("type") == "tool":
                            tool_calls.append(UnifiedToolCall.from_provider(provider.name, chunk.get("data", {})))
                        elif chunk.get("type") == "done":
                            tc = chunk.get("data", [])
                            if isinstance(tc, list):
                                tool_calls = [UnifiedToolCall.from_provider(provider.name, t) for t in tc]
                    elif isinstance(chunk, tuple):
                        # (content, tool_calls) tuple
                        return chunk
                content = "".join(content_parts)
                if content or tool_calls:
                    return content, tool_calls
            except Exception:
                pass  # Fall through to chat()

        return provider.chat(messages, tool_defs or [])

    @property
    def pool_status(self) -> dict:
        return {
            "total": self._pool.total_count,
            "available": self._pool.available_count,
            "health": dict(self._pool._health),
        }


# ═══════════════════════════════════════════════════════════════
# Custom Exceptions
# ═══════════════════════════════════════════════════════════════

class RateLimitError(Exception):
    pass


class ProviderAuthError(Exception):
    pass


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_reliable: ReliableProvider | None = None


def get_reliable_provider() -> ReliableProvider:
    global _reliable
    if _reliable is None:
        _reliable = ReliableProvider()
    return _reliable

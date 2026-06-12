import json, time
import httpx
from typing import Optional

from ..proxy import proxy_manager, ZEN_BASE
from ..config.keychain import get_key

# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------

class ToolCall:
    def __init__(self, name: str, args: dict, id: str = ""):
        self.name = name
        self.args = args
        self.id = id


# ---------------------------------------------------------------------------
# Base Provider
# ---------------------------------------------------------------------------

class Provider:
    def __init__(self, name: str, model: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def build_tools_schema(self, tools: list) -> list:
        result = []
        for t in tools:
            params = t.get("parameters", {})
            # Support both flat format and OpenAI-compatible format
            if isinstance(params, dict) and params.get("type") == "object" and "properties" in params:
                props = params["properties"]
                required = params.get("required", [])
            else:
                props = {}
                required = []
                for k, v in params.items():
                    props[k] = {"type": v.get("type", "string"), "description": v.get("description", "")}
                    if v.get("required", False):
                        required.append(k)
            result.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": {"type": "object", "properties": props, "required": required},
                },
            })
        return result

    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7):
        raise NotImplementedError

    def stream(self, messages: list, tool_defs: list, temperature: float = 0.7):
        """Generator that yields events for live streaming.
        Default: single done event (no streaming)."""
        content, tool_calls = self.chat(messages, tool_defs, temperature)
        yield {"type": "done", "data": (content, tool_calls)}


# ---------------------------------------------------------------------------
# Ollama Provider
# ---------------------------------------------------------------------------

class OllamaProvider(Provider):
    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7):
        url = f"{self.base_url}/v1/chat/completions"
        schema = self.build_tools_schema(tool_defs)
        body = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": 32768}
        if schema:
            body["tools"] = schema
        try:
            resp = httpx.post(url, json=body, timeout=300)
            resp.raise_for_status()
            return self._parse(resp.json())
        except httpx.ConnectError:
            return f"\u26a0\ufe0f  Cannot connect to Ollama at {self.base_url}\nRun: ollama serve", []

    def _parse(self, data: dict) -> tuple:
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        calls = []
        for tc in msg.get("tool_calls") or []:
            func = tc.get("function", {})
            raw = func.get("arguments", "{}")
            if isinstance(raw, str):
                raw = json.loads(raw) if raw.strip() else {}
            calls.append(ToolCall(name=func.get("name", ""), args=raw, id=tc.get("id", "")))
        return content, calls


# ---------------------------------------------------------------------------
# OpenAI-Compatible Provider
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(Provider):
    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7):
        url = f"{self.base_url}/chat/completions"
        schema = self.build_tools_schema(tool_defs)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": 32768}
        if schema:
            body["tools"] = schema
        try:
            resp = httpx.post(url, json=body, headers=headers, timeout=300)
            resp.raise_for_status()
            return self._parse(resp.json())
        except httpx.HTTPStatusError as e:
            return f"\u26a0\ufe0f  Error {e.response.status_code}: {e.response.text[:500]}", []
        except httpx.ConnectError:
            return f"\u26a0\ufe0f  Cannot connect to {self.base_url}", []

    def _parse(self, data: dict) -> tuple:
        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content") or ""
        calls = []
        for tc in msg.get("tool_calls") or []:
            func = tc.get("function", {})
            raw = func.get("arguments", "{}")
            if isinstance(raw, str):
                raw = json.loads(raw) if raw.strip() else {}
            calls.append(ToolCall(name=func.get("name", ""), args=raw, id=tc.get("id", "")))
        return content, calls


# ---------------------------------------------------------------------------
# OpenCode Zen Provider -- with automatic proxy rotation
# ---------------------------------------------------------------------------

class OpenCodeZenProvider(OpenAICompatibleProvider):
    """
    Connects to opencode.ai/zen/v1 with:
    - full streaming
    - automatic proxy rotation on every 429
    - fallback across all free models on repeated failures
    - retry with exponential backoff
    """

    MAX_RETRIES = 5           # total retry attempts
    PROXY_ROTATIONS = 3       # how many proxy rotations before switching model

    def __init__(self, name: str, model: str,
                 base_url: str = "https://opencode.ai/zen/v1",
                 api_key: str = "public"):
        super().__init__(name, model, base_url, api_key)
        # Free model list for fallback -- populated on first use
        self._free_models: list[str] = []
        self._model_index: int = 0

    def _get_free_models(self) -> list[str]:
        if not self._free_models:
            self._free_models = fetch_free_models()
            # Put the current model first
            if self.model in self._free_models:
                self._free_models.remove(self.model)
            self._free_models.insert(0, self.model)
        return self._free_models

    def _next_model(self) -> str:
        models = self._get_free_models()
        self._model_index = (self._model_index + 1) % len(models)
        return models[self._model_index]

    def stream(self, messages: list, tool_defs: list, temperature: float = 0.7):
        """Generator: yields content chunks + tool calls + done event."""
        url = f"{self.base_url}/chat/completions"
        schema = self.build_tools_schema(tool_defs)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 32768,
            "stream": True,
        }
        if schema:
            body["tools"] = schema

        proxy_rotations_done = 0
        retries = self.MAX_RETRIES

        content_chunks: list[str] = []
        reasoning_chunks: list[str] = []
        current_tool_calls: dict = {}

        for attempt in range(retries):
            transport = proxy_manager.get_transport()
            try:
                client_kwargs = {"timeout": 300}
                if transport:
                    client_kwargs["transport"] = transport

                with httpx.Client(**client_kwargs) as client:
                    with client.stream("POST", url, json=body, headers=headers) as resp:

                        if resp.status_code == 429:
                            resp.read()
                            if proxy_rotations_done < self.PROXY_ROTATIONS:
                                proxy_manager.rotate()
                                proxy_rotations_done += 1
                                wait = 1
                            else:
                                new_model = self._next_model()
                                body["model"] = new_model
                                proxy_manager.rotate()
                                proxy_rotations_done = 0
                                wait = 2 ** attempt
                            time.sleep(wait)
                            continue

                        if resp.status_code != 200:
                            try:
                                err_body = resp.read().decode("utf-8", errors="replace")
                            except Exception:
                                err_body = f"HTTP {resp.status_code}"
                            if resp.status_code in (401, 403) and "Free promotion" in err_body:
                                body["model"] = self._next_model()
                                continue
                            yield {"type": "error", "data": f"{resp.status_code}: {err_body[:500]}"}
                            return

                        # Read stream
                        for line in resp.iter_lines():
                            if not line or line == "data: [DONE]" or line.startswith(":keepalive"):
                                continue
                            if not line.startswith("data: "):
                                continue
                            try:
                                chunk = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue
                            choices = chunk.get("choices")
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            if not delta:
                                continue
                            if delta.get("content"):
                                content_chunks.append(delta["content"])
                                yield {"type": "content", "data": delta["content"]}
                            if delta.get("reasoning_content"):
                                reasoning_chunks.append(delta["reasoning_content"])
                                yield {"type": "reasoning", "data": delta["reasoning_content"]}
                            tc = delta.get("tool_calls")
                            if tc:
                                for t in tc:
                                    idx = t.get("index", 0)
                                    if idx not in current_tool_calls:
                                        current_tool_calls[idx] = {
                                            "id": t.get("id", ""),
                                            "function": {"name": "", "arguments": ""},
                                        }
                                    func = t.get("function", {})
                                    if func.get("name"):
                                        current_tool_calls[idx]["function"]["name"] += func["name"]
                                    if func.get("arguments"):
                                        current_tool_calls[idx]["function"]["arguments"] += func["arguments"]
                                    if t.get("id"):
                                        current_tool_calls[idx]["id"] = t["id"]

                # --- Success ---
                content = "".join(content_chunks)
                full_reasoning = "".join(reasoning_chunks)
                if full_reasoning:
                    content = f"[\u601d\u8003\u4e2d]\n{full_reasoning}\n[/\u601d\u8003\u4e2d]\n\n" + (content or "")
                calls = []
                for idx in sorted(current_tool_calls):
                    tc = current_tool_calls[idx]
                    raw = tc["function"]["arguments"]
                    try:
                        args = json.loads(raw) if raw.strip() else {}
                    except json.JSONDecodeError:
                        args = {}
                    calls.append(ToolCall(name=tc["function"]["name"], args=args, id=tc["id"]))
                yield {"type": "done", "data": (content, calls)}
                return

            except (httpx.ProxyError, httpx.ConnectError):
                proxy_manager.rotate()
                proxy_rotations_done += 1
                time.sleep(1)
                continue
            except httpx.ReadTimeout:
                yield {"type": "error", "data": "Timeout (300 seconds)"}
                return
            except Exception as e:
                yield {"type": "error", "data": f"Unexpected error: {e}"}
                return

        yield {"type": "error", "data": "All attempts failed (proxies + models exhausted)"}

    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7):
        """Non-streaming: consume stream() and return final result."""
        content = ""
        calls = []
        for event in self.stream(messages, tool_defs, temperature):
            if event["type"] == "error":
                return f"\u26a0\ufe0f  {event['data']}", []
            if event["type"] == "done":
                content, calls = event["data"]
        return content, calls


# ---------------------------------------------------------------------------
# DeepSeek Provider (OpenAI-compatible, with streaming)
# ---------------------------------------------------------------------------

class DeepSeekProvider(OpenAICompatibleProvider):
    """
    Connects to api.deepseek.com with:
    - full streaming
    - reasoning_content support
    - tool calls support
    - optional thinking / reasoning_effort parameters (controlled via config)
    """

    def __init__(self, name: str, model: str,
                 base_url: str = "https://api.deepseek.com",
                 api_key: str = "",
                 cfg: dict | None = None):
        super().__init__(name, model, base_url, api_key)
        self._thinking_enabled = True if cfg is None else cfg.get("thinking", True)

    def stream(self, messages: list, tool_defs: list, temperature: float = 0.7):
        """Generator with reasoning_content + tool calls support."""
        url = f"{self.base_url}/chat/completions"
        schema = self.build_tools_schema(tool_defs)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 32768,
            "stream": True,
        }
        if self._thinking_enabled:
            body["thinking"] = {"type": "enabled"}
            body["reasoning_effort"] = "high"
        if schema:
            body["tools"] = schema

        try:
            with httpx.Client(timeout=300) as client:
                with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code != 200:
                        err_body = resp.read().decode("utf-8", errors="replace")
                        yield {"type": "error",
                               "data": f"{resp.status_code}: {err_body[:500]}"}
                        return

                    content_chunks: list[str] = []
                    reasoning_chunks: list[str] = []
                    current_tool_calls: dict = {}

                    for line in resp.iter_lines():
                        if not line or line == "data: [DONE]":
                            continue
                        if not line.startswith("data: "):
                            continue
                        try:
                            chunk = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices")
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if not delta:
                            continue
                        if delta.get("content"):
                            content_chunks.append(delta["content"])
                            yield {"type": "content", "data": delta["content"]}
                        if delta.get("reasoning_content"):
                            reasoning_chunks.append(delta["reasoning_content"])
                            yield {"type": "reasoning",
                                   "data": delta["reasoning_content"]}
                        tc = delta.get("tool_calls")
                        if tc:
                            for t in tc:
                                idx = t.get("index", 0)
                                if idx not in current_tool_calls:
                                    current_tool_calls[idx] = {
                                        "id": t.get("id", ""),
                                        "function": {"name": "", "arguments": ""},
                                    }
                                func = t.get("function", {})
                                if func.get("name"):
                                    current_tool_calls[idx]["function"]["name"] += func["name"]
                                if func.get("arguments"):
                                    current_tool_calls[idx]["function"]["arguments"] += func["arguments"]
                                if t.get("id"):
                                    current_tool_calls[idx]["id"] = t["id"]

                    # --- Build final result ---
                    content = "".join(content_chunks)
                    full_reasoning = "".join(reasoning_chunks)
                    if full_reasoning:
                        content = f"[\u601d\u8003\u4e2d]\n{full_reasoning}\n[/\u601d\u8003\u4e2d]\n\n" + (content or "")
                    calls = []
                    for idx in sorted(current_tool_calls):
                        tc = current_tool_calls[idx]
                        raw = tc["function"]["arguments"]
                        try:
                            args = json.loads(raw) if raw.strip() else {}
                        except json.JSONDecodeError:
                            args = {}
                        calls.append(ToolCall(name=tc["function"]["name"],
                                              args=args, id=tc["id"]))
                    yield {"type": "done", "data": (content, calls)}

        except httpx.ConnectError:
            yield {"type": "error",
                   "data": f"Cannot connect to DeepSeek at {self.base_url}"}
        except httpx.ReadTimeout:
            yield {"type": "error", "data": "Timeout (300 seconds)"}
        except Exception as e:
            yield {"type": "error", "data": f"Error: {e}"}

    def chat(self, messages: list, tool_defs: list, temperature: float = 0.7):
        """Non-streaming: consume stream() and return final result."""
        content = ""
        calls = []
        for event in self.stream(messages, tool_defs, temperature):
            if event["type"] == "error":
                return f"\u26a0\ufe0f  {event['data']}", []
            if event["type"] == "done":
                content, calls = event["data"]
        return content, calls


# ---------------------------------------------------------------------------
# Default fallback model (used when API calls fail — loaded from config first)
# ---------------------------------------------------------------------------

_DEFAULT_FALLBACK_MODEL: str | None = None

def set_fallback_model(model: str):
    """Set the fallback model from config (called at startup)."""
    global _DEFAULT_FALLBACK_MODEL
    _DEFAULT_FALLBACK_MODEL = model


def _get_fallback_model() -> str:
    """Return the configured fallback, or a safe hardcoded last resort."""
    return _DEFAULT_FALLBACK_MODEL or "deepseek-v4-flash-free"


# ---------------------------------------------------------------------------
# Free Models Cache
# ---------------------------------------------------------------------------

FREE_MODELS_CACHE = {"models": [], "timestamp": 0}

def fetch_free_models(force_refresh: bool = False) -> list[str]:
    now = time.time()
    if (not force_refresh
            and FREE_MODELS_CACHE["models"]
            and (now - FREE_MODELS_CACHE["timestamp"]) < 3600):
        return FREE_MODELS_CACHE["models"]
    fallback = _get_fallback_model()
    try:
        r = httpx.get(f"{ZEN_BASE}/models", timeout=10)
        if r.status_code != 200:
            return FREE_MODELS_CACHE["models"] or [fallback]
        all_models = r.json().get("data", [])
        free = [m["id"] for m in all_models if "free" in m.get("id", "").lower()]
        if free:
            FREE_MODELS_CACHE["models"] = free
            FREE_MODELS_CACHE["timestamp"] = now
        return FREE_MODELS_CACHE["models"] or [fallback]
    except Exception:
        return FREE_MODELS_CACHE["models"] or [fallback]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cost tracking — map model names to per-token pricing
# ---------------------------------------------------------------------------

_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (input_per_1M, output_per_1M) in USD
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3.5": (0.80, 4.00),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    "deepseek-v4-flash": (0.35, 1.40),
    "deepseek-v4-pro": (1.50, 6.00),
}

# Fallback pricing for unknown models
_DEFAULT_INPUT_PRICE = 1.0  # $1/M tokens
_DEFAULT_OUTPUT_PRICE = 4.0  # $4/M tokens


def get_model_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for a model.

    Falls back to sensible defaults for unknown models.
    Returns (0, 0) for free models (opencode-zen, etc.).
    """
    if not model or "free" in model.lower() or "opencode" in model.lower():
        return (0.0, 0.0)
    model_lower = model.lower()
    if model_lower in _MODEL_PRICING:
        return _MODEL_PRICING[model_lower]
    # Check partial match
    for key, pricing in _MODEL_PRICING.items():
        if key in model_lower:
            return pricing
    return (_DEFAULT_INPUT_PRICE, _DEFAULT_OUTPUT_PRICE)


def estimate_turn_cost(model: str, input_tokens: int = 500,
                       output_tokens: int = 1000) -> float:
    """Estimate cost of a single LLM turn.

    Uses model pricing lookup. Returns 0 for free models.
    """
    inp_price, out_price = get_model_pricing(model)
    if inp_price == 0 and out_price == 0:
        return 0.0
    return (input_tokens / 1_000_000 * inp_price +
            output_tokens / 1_000_000 * out_price)


def create_provider(cfg: dict) -> Provider:
    p = cfg.get("provider", {})
    # Load from config with dynamic fallbacks
    name = p.get("name") or cfg.get("default_provider", "opencode-zen")
    model = p.get("model") or cfg.get("default_model", "deepseek-v4-flash-free")
    base_url = p.get("base_url") or cfg.get("default_base_url", "https://opencode.ai/zen/v1")
    # Update the fallback model for proxy & cache (dynamic)
    set_fallback_model(model)

    # Prefer key from env / keychain; fall back to config (for legacy compat)
    api_key = get_key(name) or p.get("api_key", "public")
    if name == "ollama":
        return OllamaProvider(name, model, base_url, api_key)
    if name in ("opencode-zen", "opencode"):
        return OpenCodeZenProvider(name, model, base_url, api_key)
    if name == "deepseek":
        return DeepSeekProvider(name, model, base_url, api_key, cfg=cfg)
    return OpenAICompatibleProvider(name, model, base_url, api_key)

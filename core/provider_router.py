
"""
Provider Router - DEPRECATED
============================
This module is preserved for reference only.
All functionality has been consolidated into `core/providers/providers.py`.

Key migration:
  - ProviderRouter          → use `create_provider()` in `core/providers/providers.py`
  - ProviderRouter.fallback → already handled by `OpenCodeZenProvider._next_model()`
"""

import warnings
warnings.warn(
    "core.provider_router is deprecated. Use core.providers.providers.create_provider() instead.",
    DeprecationWarning,
    stacklevel=2,
)

import time
import logging

logger = logging.getLogger("widdx.provider_router")


class ProviderConfig:
    def __init__(self, name, provider_class, model, base_url=None, api_key=None, priority=0, enabled=True, config=None):
        self.name = name
        self.provider_class = provider_class
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.priority = priority
        self.enabled = enabled
        self.config = config


class ProviderRouter:
    def __init__(self):
        from .database import get_db
        self.db = get_db()
        self._configs = {}
        self._current_provider = None
        self._fallback_chain = []
        self._init_default_providers()
    
    def _init_default_providers(self):
        from .providers.providers import (
            OpenCodeZenProvider,
            DeepSeekProvider,
            OllamaProvider,
            OpenAICompatibleProvider
        )
        
        defaults = [
            ProviderConfig(
                name="opencode-zen",
                provider_class=OpenCodeZenProvider,
                model="deepseek-v4-flash-free",
                base_url="https://opencode.ai/zen/v1",
                api_key="public",
                priority=100
            ),
            ProviderConfig(
                name="deepseek",
                provider_class=DeepSeekProvider,
                model="deepseek-chat",
                base_url="https://api.deepseek.com",
                priority=90
            ),
            ProviderConfig(
                name="ollama",
                provider_class=OllamaProvider,
                model="llama3.2",
                base_url="http://localhost:11434/v1",
                priority=80
            ),
            ProviderConfig(
                name="openai",
                provider_class=OpenAICompatibleProvider,
                model="gpt-4o-mini",
                base_url="https://api.openai.com/v1",
                priority=70
            )
        ]
        
        for cfg in defaults:
            self._configs[cfg.name] = cfg
        
        self._rebuild_fallback_chain()
    
    def _rebuild_fallback_chain(self):
        enabled = [cfg for cfg in self._configs.values() if cfg.enabled]
        
        stats = {}
        for s in self.db.get_provider_stats():
            key = f"{s['provider_name']}:{s['model_name']}"
            stats[key] = s
        
        def score(cfg):
            key = f"{cfg.name}:{cfg.model}"
            s = stats.get(key, {})
            succ = s.get("success_count", 0)
            fail = s.get("failure_count", 0)
            rate = succ / max(1, succ + fail)
            return (cfg.priority * 0.5) + (rate * 100 * 0.5)
        
        enabled.sort(key=score, reverse=True)
        self._fallback_chain = [c.name for c in enabled]
        if not self._current_provider and self._fallback_chain:
            self._current_provider = self._fallback_chain[0]
    
    def register_provider(self, config):
        self._configs[config.name] = config
        self._rebuild_fallback_chain()
    
    def get_provider(self, name=None):
        if name:
            cfg = self._configs.get(name)
            if cfg and cfg.enabled:
                return self._instantiate_provider(cfg)
        if self._current_provider:
            cfg = self._configs.get(self._current_provider)
            if cfg and cfg.enabled:
                return self._instantiate_provider(cfg)
        for name in self._fallback_chain:
            cfg = self._configs[name]
            if cfg.enabled:
                return self._instantiate_provider(cfg)
        raise RuntimeError("No enabled providers available")
    
    def _instantiate_provider(self, cfg):
        kwargs = {"name": cfg.name, "model": cfg.model}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.api_key:
            kwargs["api_key"] = cfg.api_key
        if cfg.config:
            kwargs["cfg"] = cfg.config
        return cfg.provider_class(**kwargs)
    
    def set_current(self, name):
        if name in self._configs and self._configs[name].enabled:
            self._current_provider = name
    
    @property
    def current_name(self):
        return self._current_provider
    
    def list_providers(self):
        return [
            {
                "name": cfg.name,
                "model": cfg.model,
                "priority": cfg.priority,
                "enabled": cfg.enabled,
                "current": cfg.name == self._current_provider
            }
            for cfg in self._configs.values()
        ]
    
    def chat_with_fallback(self, messages, tool_defs, temperature=0.7, max_attempts=3):
        last_error = None
        start_time = time.time()
        
        try_order = []
        if self._current_provider:
            try_order.append(self._current_provider)
        for name in self._fallback_chain:
            if name not in try_order:
                try_order.append(name)
        
        for attempt, provider_name in enumerate(try_order[:max_attempts]):
            try:
                provider_start = time.time()
                provider = self.get_provider(provider_name)
                content, calls = provider.chat(messages, tool_defs, temperature)
                provider_time = time.time() - provider_start
                
                self.db.record_provider_usage(
                    provider_name, provider.model, 
                    success=True, response_time=provider_time
                )
                
                if self._current_provider != provider_name:
                    self._current_provider = provider_name
                    self._rebuild_fallback_chain()
                
                return content, calls
            except Exception as e:
                last_error = str(e)
                try:
                    provider = self._instantiate_provider(self._configs[provider_name])
                    self.db.record_provider_usage(
                        provider_name, provider.model,
                        success=False, response_time=0
                    )
                except Exception:
                    logger.debug("Provider failed (already recorded), skipping")
                continue
        
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
    def stream_with_fallback(self, messages, tool_defs, temperature=0.7, max_attempts=3):
        try_order = []
        if self._current_provider:
            try_order.append(self._current_provider)
        for name in self._fallback_chain:
            if name not in try_order:
                try_order.append(name)
        
        last_error = None
        
        for provider_name in try_order[:max_attempts]:
            try:
                provider = self.get_provider(provider_name)
                
                start_time = time.time()
                success = False
                final_content = ""
                final_calls = []
                
                for event in provider.stream(messages, tool_defs, temperature):
                    if event.get("type") == "done":
                        final_content, final_calls = event.get("data", ("", []))
                        success = True
                    yield event
                
                if success:
                    total_time = time.time() - start_time
                    self.db.record_provider_usage(
                        provider_name, provider.model,
                        success=True, response_time=total_time
                    )
                    if self._current_provider != provider_name:
                        self._current_provider = provider_name
                        self._rebuild_fallback_chain()
                    return
                
            except Exception as e:
                last_error = str(e)
                try:
                    provider = self._instantiate_provider(self._configs[provider_name])
                    self.db.record_provider_usage(
                        provider_name, provider.model,
                        success=False, response_time=0
                    )
                except Exception:
                    logger.debug("Provider failed (already recorded), skipping")
                continue
        
        yield {"type": "error", "data": f"All providers failed. Last error: {last_error}"}


_router = None

def get_provider_router():
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router

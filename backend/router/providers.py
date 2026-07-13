"""
LLM Provider clients - unified interface for all 9 providers.
Supports: OpenAI, Anthropic, Gemini, Mistral, Groq, Together AI, OpenRouter, Ollama, Custom
"""
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

import structlog

from backend.config import settings
from backend.models.schemas import Message

logger = structlog.get_logger()


class LLMProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int = 500):
        self.provider = provider
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class BaseLLMClient(ABC):
    def __init__(self, provider_name: str, default_model: str, api_key: Optional[str] = None):
        self.provider_name = provider_name
        self.default_model = default_model
        self._api_key_override = api_key

    @abstractmethod
    async def complete(self, messages: List[Message], model: Optional[str] = None, max_tokens: int = 2048, temperature: float = 0.7) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": m.role, "content": m.content} for m in messages]


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("openai", "gpt-4o-mini", api_key=api_key)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                key = self._api_key_override or settings.openai_api_key
                if not key:
                    raise LLMProviderError("openai", "No API key configured")
                self._client = AsyncOpenAI(api_key=key)
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError("openai", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("openai", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override or settings.openai_api_key)


class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("anthropic", "claude-3-haiku-20240307", api_key=api_key)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                key = self._api_key_override or settings.anthropic_api_key
                if not key:
                    raise LLMProviderError("anthropic", "No API key configured")
                self._client = anthropic.AsyncAnthropic(api_key=key)
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError("anthropic", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            system_msg = ""
            non_system = []
            for m in messages:
                if m.role == "system":
                    system_msg = m.content
                else:
                    non_system.append({"role": m.role, "content": m.content})
            kwargs = dict(model=model, max_tokens=max_tokens, messages=non_system, temperature=temperature)
            if system_msg:
                kwargs["system"] = system_msg
            response = await client.messages.create(**kwargs)
            return {
                "content": response.content[0].text,
                "tokens_input": response.usage.input_tokens,
                "tokens_output": response.usage.output_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("anthropic", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override or settings.anthropic_api_key)


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("gemini", "gemini-2.5-flash", api_key=api_key)
        self._configured = False
        self._genai = None

    def _configure(self):
        if not self._configured:
            try:
                import google.generativeai as genai
                key = self._api_key_override or settings.gemini_api_key
                genai.configure(api_key=key)
                self._configured = True
                self._genai = genai
            except Exception as e:
                raise LLMProviderError("gemini", f"Failed to configure: {e}")

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        self._configure()
        model = model or self.default_model
        start = time.time()
        try:
            genai_model = self._genai.GenerativeModel(model)
            prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
            response = genai_model.generate_content(prompt)
            input_tokens = int(len(prompt.split()) * 1.3)
            output_tokens = int(len(response.text.split()) * 1.3)
            return {
                "content": response.text,
                "tokens_input": input_tokens,
                "tokens_output": output_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("gemini", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override or settings.gemini_api_key)


class MistralClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("mistral", "mistral-small-latest", api_key=api_key)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from mistralai import Mistral
                key = self._api_key_override or settings.mistral_api_key
                self._client = Mistral(api_key=key)
            except Exception as e:
                raise LLMProviderError("mistral", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.complete_async(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("mistral", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override or settings.mistral_api_key)


class GroqClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("groq", "llama-3.3-70b-versatile", api_key=api_key)
        self._base_url = base_url or "https://api.groq.com/openai/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                key = self._api_key_override
                if not key:
                    raise LLMProviderError("groq", "No API key configured")
                self._client = AsyncOpenAI(api_key=key, base_url=self._base_url)
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError("groq", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("groq", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override)


class TogetherClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("together", "meta-llama/Llama-3-70b-chat-hf", api_key=api_key)
        self._base_url = base_url or "https://api.together.xyz/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                key = self._api_key_override
                if not key:
                    raise LLMProviderError("together", "No API key configured")
                self._client = AsyncOpenAI(api_key=key, base_url=self._base_url)
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError("together", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("together", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override)


class OpenRouterClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("openrouter", "openai/gpt-4o-mini", api_key=api_key)
        self._base_url = base_url or "https://openrouter.ai/api/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                key = self._api_key_override
                if not key:
                    raise LLMProviderError("openrouter", "No API key configured")
                self._client = AsyncOpenAI(
                    api_key=key, base_url=self._base_url,
                    default_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "LLMOps Gateway"},
                )
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError("openrouter", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("openrouter", str(e))

    async def is_available(self) -> bool:
        return bool(self._api_key_override)


class OllamaClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("ollama", "llama3.2", api_key=api_key)
        self._base_url = base_url or "http://localhost:11434/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key="ollama", base_url=self._base_url)
            except Exception as e:
                raise LLMProviderError("ollama", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": getattr(response.usage, "prompt_tokens", 0),
                "tokens_output": getattr(response.usage, "completion_tokens", 0),
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("ollama", str(e))

    async def is_available(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(self._base_url.replace("/v1", "/api/tags"))
                return r.status_code == 200
        except Exception:
            return False


class CustomOpenAIClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("custom", "gpt-3.5-turbo", api_key=api_key)
        self._base_url = base_url or "http://localhost:8080/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key_override or "custom", base_url=self._base_url)
            except Exception as e:
                raise LLMProviderError("custom", f"Failed to initialize: {e}")
        return self._client

    async def complete(self, messages, model=None, max_tokens=2048, temperature=0.7):
        client = self._get_client()
        model = model or self.default_model
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=model, messages=self._format_messages(messages),
                max_tokens=max_tokens, temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_input": getattr(response.usage, "prompt_tokens", 0),
                "tokens_output": getattr(response.usage, "completion_tokens", 0),
                "model": model, "provider": self.provider_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            raise LLMProviderError("custom", str(e))

    async def is_available(self) -> bool:
        return bool(self._base_url)


# ─── Default models per provider ──────────────────────────────────────────────

PROVIDER_DEFAULT_MODELS = {
    "openai":      ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic":   ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
    "gemini":      ["gemini-2.5-flash", "gemini-2.5-pro"],
    "mistral":     ["mistral-large-latest", "mistral-small-latest", "open-mistral-7b"],
    "groq":        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "together":    ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
    "openrouter":  ["openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash-1.5"],
    "ollama":      ["llama3.2", "llama3.1", "mistral", "codellama", "phi3"],
    "custom":      ["gpt-3.5-turbo"],
}


# ─── Provider Registry ────────────────────────────────────────────────────────

class LLMProviderRegistry:
    _client_classes = {
        "openai":      OpenAIClient,
        "anthropic":   AnthropicClient,
        "gemini":      GeminiClient,
        "mistral":     MistralClient,
        "groq":        GroqClient,
        "together":    TogetherClient,
        "openrouter":  OpenRouterClient,
        "ollama":      OllamaClient,
        "custom":      CustomOpenAIClient,
    }

    @classmethod
    def get_client(cls, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> BaseLLMClient:
        if provider not in cls._client_classes:
            raise ValueError(f"Unknown provider: {provider}")
        import inspect
        klass = cls._client_classes[provider]
        sig = inspect.signature(klass.__init__)
        kwargs = {}
        if "api_key" in sig.parameters:
            kwargs["api_key"] = api_key
        if "base_url" in sig.parameters:
            kwargs["base_url"] = base_url
        return klass(**kwargs)

    @classmethod
    async def get_available_providers(cls, api_keys: Optional[Dict] = None, base_urls: Optional[Dict] = None) -> List[str]:
        api_keys = api_keys or {}
        base_urls = base_urls or {}
        available = []
        for provider in cls._client_classes:
            try:
                client = cls.get_client(provider, api_key=api_keys.get(provider), base_url=base_urls.get(provider))
                if await client.is_available():
                    available.append(provider)
            except Exception:
                pass
        return available

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._client_classes.keys())

    @classmethod
    def get_default_models(cls, provider: str) -> List[str]:
        return PROVIDER_DEFAULT_MODELS.get(provider, [])
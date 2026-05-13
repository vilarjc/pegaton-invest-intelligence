"""Provider abstraction layer for multi-model access.
Supports DeepSeek, Gemini, OpenRouter, and any OpenAI-compatible API."""

import os
import json
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))


class ModelProvider:
    """Base class for model providers."""
    
    name: str = "base"
    
    async def chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        """Send a chat completion request. Returns parsed response."""
        raise NotImplementedError
    
    def parse_response(self, raw: dict) -> dict:
        """Extract content, tokens, and cost from raw API response."""
        raise NotImplementedError


class DeepSeekProvider(ModelProvider):
    """Provider for DeepSeek API (V4 Flash, Chat, Reasoner, V4 Pro)."""
    
    name = "deepseek"
    base_url = "https://api.deepseek.com"
    
    # Model configs: config_id -> {name, api_model, input_price_per_M, output_price_per_M}
    MODELS = {
        "deepseek-v4-flash": {
            "name": "V4 Flash",
            "api_model": "deepseek-v4-flash",
            "input_price": 0.14,
            "output_price": 0.28,
            "input_cache_hit_price": 0.0028,
            "description": "Rápido y barato para tareas rutinarias",
        },

        "deepseek-v4-pro": {
            "name": "V4 Pro",
            "api_model": "deepseek-v4-pro",
            "input_price": 0.435,
            "output_price": 0.87,
            "input_cache_hit_price": 0.003625,
            "description": "Alta calidad para decisiones críticas (75% OFF hasta 31-May-2026)",
        },

    }
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            print("WARNING: DEEPSEEK_API_KEY not configured")
    
    async def chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        if not self.api_key:
            return {"error": "DeepSeek API key not configured", "model": model}
        
        # Map model IDs to actual API model names
        cfg = self.MODELS.get(model, {})
        api_model = cfg.get("api_model", model)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": api_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                data = resp.json()
                if resp.status_code != 200:
                    return {"error": f"API error {resp.status_code}: {data}", "model": model}
                return self.parse_response(data, model)
            except Exception as e:
                return {"error": str(e), "model": model}
    
    def parse_response(self, data: dict, model: str) -> dict:
        """Parse DeepSeek response and calculate cost."""
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        total_tokens = tokens_in + tokens_out
        
        cfg = self.MODELS.get(model, {"input_price": 0.14, "output_price": 0.28, "name": model})
        cost = (tokens_in / 1_000_000 * cfg["input_price"]) + \
               (tokens_out / 1_000_000 * cfg["output_price"])
        
        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        
        return {
            "provider": "deepseek",
            "model": model,
            "model_name": cfg.get("name", model),
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "cost": round(cost, 6),
            "temperature": 0.3,
        }


class GeminiProvider(ModelProvider):
    """Provider for Google Gemini API via OpenAI-compatible endpoint."""
    
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    MODELS = {
        "gemini-2.5-flash": {
            "name": "Gemini 2.5 Flash",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "✅ Funciona en tier gratuito — multimodal rápido",
        },
    }
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not configured")
    
    async def chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        retries: int = 3,
    ) -> dict:
        if not self.api_key:
            return {"error": "Gemini API key not configured", "model": model}

        # Gemini uses its own format - convert from OpenAI format
        system_msg = ""
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            elif m["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": m["content"]}]})

        request_body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_msg:
            request_body["systemInstruction"] = {"parts": [{"text": system_msg}]}

        last_error = None
        for attempt in range(retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    resp = await client.post(
                        f"{self.base_url}/models/{model}:generateContent",
                        params={"key": self.api_key},
                        json=request_body,
                    )
                    data = resp.json()
                    if resp.status_code == 429:
                        if attempt < retries - 1:
                            wait = 2 ** attempt * 2  # 2s, 4s, 8s
                            print(f"  Gemini rate limited, retrying in {wait}s (attempt {attempt+1}/{retries})")
                            import asyncio
                            await asyncio.sleep(wait)
                            continue
                        return {"error": "Gemini: Límite de tasa excedido (429). El tier gratuito tiene límites de ~60 req/min. Espera 30s y reintenta.", "model": model}
                    if resp.status_code != 200:
                        return {"error": f"Gemini error {resp.status_code}: {data}", "model": model}
                    return self.parse_response(data, model)
                except Exception as e:
                    last_error = str(e)
                    if attempt < retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return {"error": last_error, "model": model}
        return {"error": last_error or "Max retries exceeded", "model": model}
    
    def parse_response(self, data: dict, model: str) -> dict:
        cfg = self.MODELS.get(model, {"name": model})
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = " ".join(p.get("text", "") for p in parts)
        
        usage = data.get("usageMetadata", {})
        tokens_in = usage.get("promptTokenCount", 0)
        tokens_out = usage.get("candidatesTokenCount", 0)
        
        return {
            "provider": "gemini",
            "model": model,
            "model_name": cfg.get("name", model),
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "cost": 0.0,  # Free tier
            "temperature": 0.3,
        }


class OpenRouterProvider(ModelProvider):
    """Provider for OpenRouter (access to many models including free ones)."""
    
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    
    MODELS = {
        "nvidia/nemotron-3-super-120b-a12b:free": {
            "name": "NanoTron 3 Super",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en OpenRouter",
        },
        "meta-llama/llama-3.3-70b-instruct:free": {
            "name": "Llama 3.3 70B",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en OpenRouter",
        },
        "google/gemma-3-27b-it:free": {
            "name": "Gemma 3 27B",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en OpenRouter",
        },
        "qwen/qwen3-coder:free": {
            "name": "Qwen3 Coder",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en OpenRouter",
        },
    }
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            print("WARNING: OPENROUTER_API_KEY not configured - free models may be limited")
    
    async def chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                data = resp.json()
                if resp.status_code == 401:
                    return {"error": f"OpenRouter requiere autenticación. OPENROUTER_API_KEY no está configurada o es inválida.", "model": model}
                if resp.status_code == 429:
                    msg = data.get("error", {}).get("message", "")
                    if "free-models-per-day" in msg:
                        detail = "Has agotado el límite diario de modelos gratuitos en OpenRouter. Vuelve mañana o añade créditos."
                    else:
                        detail = f"Rate limit: {msg}"
                    return {"error": f"OpenRouter: {detail}", "model": model}
                if resp.status_code != 200:
                    return {"error": f"OpenRouter error {resp.status_code}: {data}", "model": model}
                return self.parse_response(data, model)
            except Exception as e:
                return {"error": str(e), "model": model}
    
    def parse_response(self, data: dict, model: str) -> dict:
        cfg = self.MODELS.get(model, {"name": model, "input_price": 0, "output_price": 0})
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        
        # OpenRouter returns cost in the response
        cost = float(data.get("cost", 0)) if data.get("cost") else 0
        
        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        
        return {
            "provider": "openrouter",
            "model": model,
            "model_name": cfg.get("name", model),
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "cost": round(cost, 6),
            "temperature": 0.3,
        }


class GroqProvider(ModelProvider):
    """Provider for Groq API (fast inference on open models)."""

    name = "groq"
    base_url = "https://api.groq.com/openai/v1"

    MODELS = {
        "groq/llama-3.3-70b-versatile": {
            "name": "Llama 3.3 70B (Groq)",
            "api_model": "llama-3.3-70b-versatile",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en Groq — 30 req/min, 8K contexto",
        },
        "groq/llama-3.1-8b-instant": {
            "name": "Llama 3.1 8B (Groq)",
            "api_model": "llama-3.1-8b-instant",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en Groq — ultrarápido, 8K contexto",
        },
        "groq/mixtral-8x7b-32768": {
            "name": "Mixtral 8x7B (Groq)",
            "api_model": "mixtral-8x7b-32768",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en Groq — 32K contexto, buena calidad",
        },
        "groq/deepseek-r1-distill-llama-70b": {
            "name": "DeepSeek V4 Flash 70B (Groq)",
            "api_model": "deepseek-r1-distill-llama-70b",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en Groq — razonamiento profundo",
        },
        "groq/gemma2-9b-it": {
            "name": "Gemma 2 9B (Groq)",
            "api_model": "gemma2-9b-it",
            "input_price": 0.0,
            "output_price": 0.0,
            "description": "Gratuito en Groq — ligero y rápido",
        },
    }

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            print("WARNING: GROQ_API_KEY not configured")

    async def chat(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        if not self.api_key:
            return {"error": "Groq API key not configured", "model": model}

        cfg = self.MODELS.get(model, {})
        api_model = cfg.get("api_model", model)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": api_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                data = resp.json()
                if resp.status_code == 429:
                    msg = data.get("error", {}).get("message", "")
                    return {"error": f"Groq rate limit: {msg}", "model": model}
                if resp.status_code == 401:
                    return {"error": "Groq: API key inválida o no configurada", "model": model}
                if resp.status_code != 200:
                    return {"error": f"Groq error {resp.status_code}: {data}", "model": model}
                return self.parse_response(data, model)
            except Exception as e:
                return {"error": str(e), "model": model}

    def parse_response(self, data: dict, model: str) -> dict:
        cfg = self.MODELS.get(model, {"name": model, "input_price": 0, "output_price": 0})
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")

        return {
            "provider": "groq",
            "model": model,
            "model_name": cfg.get("name", model),
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "cost": 0.0,  # Free tier
            "temperature": 0.3,
        }


# Singleton instances
_deepseek: Optional[DeepSeekProvider] = None
_gemini: Optional[GeminiProvider] = None
_openrouter: Optional[OpenRouterProvider] = None
_groq: Optional[GroqProvider] = None


def get_provider(name: str) -> ModelProvider:
    """Get or create a provider by name."""
    global _deepseek, _gemini, _openrouter, _groq

    if name == "deepseek":
        if _deepseek is None:
            _deepseek = DeepSeekProvider()
        return _deepseek
    elif name == "gemini":
        if _gemini is None:
            _gemini = GeminiProvider()
        return _gemini
    elif name == "openrouter":
        if _openrouter is None:
            _openrouter = OpenRouterProvider()
        return _openrouter
    elif name == "groq":
        if _groq is None:
            _groq = GroqProvider()
        return _groq
    else:
        raise ValueError(f"Unknown provider: {name}")


def get_available_models() -> list:
    """Get all available models with their configs."""
    models = []
    for provider_name in ["deepseek", "gemini", "openrouter", "groq"]:
        provider = get_provider(provider_name)
        for model_id, cfg in provider.MODELS.items():
            models.append({
                "id": model_id,
                "provider": provider_name,
                "name": cfg["name"],
                "description": cfg["description"],
                "input_price": cfg["input_price"],
                "output_price": cfg["output_price"],
                "available": bool(os.getenv(f"{provider_name.upper()}_API_KEY", "")) or cfg["input_price"] == 0,
            })
    return models


def get_active_models() -> list:
    """Get only models that are currently usable (have API key or are free)."""
    return [m for m in get_available_models() if m["available"]]

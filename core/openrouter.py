"""Thin wrapper around the OpenRouter chat API (OpenAI-compatible)."""
from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from .config import settings


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to your .env file.")
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


def _headers() -> dict:
    h = {}
    if settings.site_url:
        h["HTTP-Referer"] = settings.site_url
    if settings.app_name:
        h["X-Title"] = settings.app_name
    return h


def chat(
    messages: list[dict],
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> str:
    """Send a chat completion request to OpenRouter and return the text."""
    resp = _client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers=_headers(),
    )
    return (resp.choices[0].message.content or "").strip()
